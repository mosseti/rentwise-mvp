import json
import math
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Min, Count, Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from accounts.models import Profile
from .assistant import answer_question
from .forms import AdminBuildingForm, BuildingForm, CaretakerCreateForm, CaretakerProfileForm, ListingReportForm, UnitForm, ViewingRequestForm
from .models import Area, AssistantMessage, Building, CachedPlace, ContactLead, ListingReport, SearchEvent, SavedProperty, Unit, ViewingRequest

User = get_user_model()

def _public_units_queryset():
    return Unit.objects.select_related('building', 'building__area', 'building__caretaker__profile').filter(
        status=Unit.AVAILABLE,
        building__is_published=True,
        building__caretaker__profile__approval_status=Profile.APPROVED,
        building__caretaker__profile__phone_verified=True,
    )


def _public_buildings_queryset():
    return Building.objects.select_related('area', 'caretaker__profile').filter(
        is_published=True,
        caretaker__profile__approval_status=Profile.APPROVED,
        caretaker__profile__phone_verified=True,
    )


def home(request):
    areas = Area.objects.annotate(building_count=Count('buildings', filter=Q(buildings__is_published=True, buildings__caretaker__profile__approval_status=Profile.APPROVED, buildings__caretaker__profile__phone_verified=True))).order_by('name')[:8]
    latest_units = _public_units_queryset().order_by('rent')[:6]
    saved_unit_ids = set()
    if request.user.is_authenticated and getattr(request.user, 'profile', None) and request.user.profile.role == Profile.SEEKER:
        saved_unit_ids = set(SavedProperty.objects.filter(user=request.user, unit__isnull=False).values_list('unit_id', flat=True))
    return render(request, 'rentals/home.html', {'areas': areas, 'latest_units': latest_units, 'saved_unit_ids': saved_unit_ids})


def area_list(request):
    areas = Area.objects.annotate(building_count=Count('buildings', filter=Q(buildings__is_published=True, buildings__caretaker__profile__approval_status=Profile.APPROVED, buildings__caretaker__profile__phone_verified=True))).order_by('name')
    return render(request, 'rentals/area_list.html', {'areas': areas})


def area_detail(request, slug):
    area = get_object_or_404(Area, slug=slug)
    buildings = _public_buildings_queryset().filter(area=area).annotate(min_rent=Min('units__rent'))
    return render(request, 'rentals/area_detail.html', {'area': area, 'buildings': buildings})


def map_search(request):
    areas = Area.objects.all()
    unit_types = Unit.TYPE_CHOICES
    return render(request, 'rentals/map_search.html', {'areas': areas, 'unit_types': unit_types})


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_km(lat1, lng1, lat2, lng2):
    # Haversine distance. It is fast enough for this prototype and avoids adding heavy GIS dependencies.
    radius = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lng / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))




def _normalise_place_query(value):
    return ' '.join((value or '').lower().strip().split())


def _local_place_matches(query, limit=5):
    """Return known RentWise places first so common searches do not hit a public API."""
    q = query.strip()
    if not q:
        return []
    results = []
    seen = set()
    areas = Area.objects.filter(Q(name__icontains=q) | Q(description__icontains=q)).order_by('name')[:limit]
    for area in areas:
        key = ('area', area.id)
        seen.add(key)
        results.append({
            'label': f'{area.name}, Nairobi',
            'lat': float(area.latitude),
            'lng': float(area.longitude),
            'source': 'rentwise_area',
        })
    remaining = max(limit - len(results), 0)
    if remaining:
        buildings = _public_buildings_queryset().filter(
            Q(name__icontains=q) | Q(landmark__icontains=q) | Q(area__name__icontains=q)
        ).order_by('area__name', 'name')[:remaining]
        for building in buildings:
            key = ('building', building.id)
            if key in seen:
                continue
            results.append({
                'label': f'{building.name}, {building.area.name} - {building.landmark or "Nairobi"}',
                'lat': float(building.latitude),
                'lng': float(building.longitude),
                'source': 'rentwise_building',
            })
    return results[:limit]


def _nominatim_search(query, limit=5):
    """Small Nominatim client used for free testing. Results are bounded and cached."""
    if settings.GEOCODER_PROVIDER != 'nominatim':
        return []
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
        'format': 'jsonv2',
        'limit': limit,
        'countrycodes': 'ke',
        'addressdetails': 0,
        'q': f'{query}, Nairobi, Kenya',
    })
    request = urllib.request.Request(url, headers={
        'User-Agent': 'RentWiseNairobiPrototype/1.0 (local testing)',
        'Accept': 'application/json',
    })
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            raw = response.read().decode('utf-8')
        payload = json.loads(raw)
    except Exception:
        return []

    results = []
    for item in payload[:limit]:
        lat = _parse_float(item.get('lat'))
        lng = _parse_float(item.get('lon'))
        label = item.get('display_name') or query
        if lat is None or lng is None:
            continue
        results.append({'label': label, 'lat': lat, 'lng': lng, 'source': 'nominatim'})
    return results


def place_suggestions_api(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    results = _local_place_matches(query, limit=5)
    normalised = _normalise_place_query(query)
    cached = CachedPlace.objects.filter(query=normalised).first()
    if cached and len(results) < 5:
        results.append({
            'label': cached.label,
            'lat': float(cached.latitude),
            'lng': float(cached.longitude),
            'source': cached.source,
        })

    # Nominatim is a free public geocoder, not a heavy autocomplete service. Use it only
    # after local matches and cache the first result to keep testing smooth and respectful.
    if len(results) < 5 and len(query) >= 3 and not cached:
        external = _nominatim_search(query, limit=5 - len(results))
        if external:
            first = external[0]
            CachedPlace.objects.update_or_create(
                query=normalised,
                defaults={
                    'label': first['label'],
                    'latitude': first['lat'],
                    'longitude': first['lng'],
                    'source': first['source'],
                },
            )
            results.extend(external)
    return JsonResponse({'results': results[:5]})


def geocode_place_api(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'error': 'Enter a place to search.'}, status=400)

    local = _local_place_matches(query, limit=1)
    if local:
        return JsonResponse({'result': local[0]})

    normalised = _normalise_place_query(query)
    cached = CachedPlace.objects.filter(query=normalised).first()
    if cached:
        return JsonResponse({'result': {
            'label': cached.label,
            'lat': float(cached.latitude),
            'lng': float(cached.longitude),
            'source': cached.source,
        }})

    external = _nominatim_search(query, limit=1)
    if external:
        first = external[0]
        CachedPlace.objects.update_or_create(
            query=normalised,
            defaults={
                'label': first['label'],
                'latitude': first['lat'],
                'longitude': first['lng'],
                'source': first['source'],
            },
        )
        return JsonResponse({'result': first})

    return JsonResponse({'error': 'Place not found. Try a clearer Nairobi estate, road, mall, school, or landmark.'}, status=404)


def building_markers_api(request):
    area = request.GET.get('area', '').strip()
    unit_type = request.GET.get('unit_type', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    q = request.GET.get('q', '').strip()
    search_lat = _parse_float(request.GET.get('lat'))
    search_lng = _parse_float(request.GET.get('lng'))
    radius_km = _parse_float(request.GET.get('radius_km')) or 5
    radius_km = min(max(radius_km, 1), 20)

    units = _public_units_queryset()
    if area:
        units = units.filter(building__area__slug=area)
    if unit_type:
        units = units.filter(unit_type=unit_type)
    if max_rent.isdigit():
        units = units.filter(rent__lte=int(max_rent))
    if q:
        units = units.filter(
            Q(building__name__icontains=q) |
            Q(building__landmark__icontains=q) |
            Q(building__area__name__icontains=q)
        )

    # Keep the database query simple and bounded before calculating exact distance in Python.
    if search_lat is not None and search_lng is not None:
        lat_delta = radius_km / 111
        lng_delta = radius_km / (111 * max(math.cos(math.radians(search_lat)), 0.2))
        units = units.filter(
            building__latitude__gte=search_lat - lat_delta,
            building__latitude__lte=search_lat + lat_delta,
            building__longitude__gte=search_lng - lng_delta,
            building__longitude__lte=search_lng + lng_delta,
        )

    buildings = {}
    for unit in units.order_by('rent'):
        b = unit.building
        distance = None
        if search_lat is not None and search_lng is not None:
            distance = _distance_km(search_lat, search_lng, float(b.latitude), float(b.longitude))
            if distance > radius_km:
                continue
        data = buildings.setdefault(b.id, {
            'id': b.id,
            'name': b.name,
            'area': b.area.name,
            'landmark': b.landmark,
            'lat': float(b.latitude),
            'lng': float(b.longitude),
            'url': b.get_absolute_url(),
            'image_url': b.display_image_url,
            'available_count': 0,
            'price_from': unit.rent,
            'distance_km': round(distance, 2) if distance is not None else None,
            'match_group': 'nearby' if distance is not None and distance > 2 else 'exact',
            'units': [],
        })
        data['available_count'] += 1
        data['price_from'] = min(data['price_from'], unit.rent)
        data['units'].append({
            'type': unit.get_unit_type_display(),
            'rent': unit.rent,
            'move_in_cost': unit.move_in_cost,
            'image_url': unit.cover_image_url,
        })

    results = list(buildings.values())
    if search_lat is not None and search_lng is not None:
        results.sort(key=lambda item: (item['distance_km'] if item['distance_km'] is not None else 999, item['price_from']))
    else:
        results.sort(key=lambda item: (item['price_from'], item['name']))

    message = ''
    exact_count = sum(1 for item in results if item['match_group'] == 'exact')
    nearby_count = len(results) - exact_count
    if search_lat is not None and search_lng is not None:
        if results and exact_count:
            message = f'Found {exact_count} verified building(s) close to the searched location.'
            if nearby_count:
                message += f' Also showing {nearby_count} surrounding option(s).'
        elif results:
            message = 'No verified units were found in the exact spot. Here are the closest surrounding options in the current radius.'
        else:
            message = 'No verified available units were found in this exact area. Try increasing the radius, searching a nearby estate, or walk around the area and ask caretakers directly.'

    if search_lat is not None or q:
        if not request.session.session_key:
            request.session.create()
        SearchEvent.objects.create(
            query=q[:180],
            latitude=search_lat,
            longitude=search_lng,
            radius_km=int(radius_km),
            result_count=len(results),
            session_key=request.session.session_key or '',
            user=request.user if request.user.is_authenticated else None,
        )

    return JsonResponse({
        'buildings': results,
        'message': message,
        'exact_count': exact_count,
        'nearby_count': nearby_count,
        'radius_km': radius_km,
    }, encoder=DjangoJSONEncoder)


def building_detail(request, slug):
    building = get_object_or_404(_public_buildings_queryset().select_related('caretaker', 'caretaker__profile', 'area'), slug=slug)
    available_units = building.units.filter(status=Unit.AVAILABLE).prefetch_related('images')
    saved_unit_ids = set()
    if request.user.is_authenticated:
        saved_unit_ids = set(SavedProperty.objects.filter(user=request.user, unit__building=building).values_list('unit_id', flat=True))
    return render(request, 'rentals/building_detail.html', {
        'building': building,
        'available_units': available_units,
        'saved_unit_ids': saved_unit_ids,
    })



def _safe_phone_for_whatsapp(value):
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if digits.startswith('0') and len(digits) == 10:
        return '254' + digits[1:]
    if digits.startswith('254'):
        return digits
    return digits


def _record_contact_lead(request, unit, method):
    if not request.session.session_key:
        request.session.create()
    ContactLead.objects.create(
        unit=unit,
        user=request.user if request.user.is_authenticated else None,
        method=method,
        session_key=request.session.session_key or '',
    )


def request_viewing(request, unit_id):
    unit = get_object_or_404(_public_units_queryset(), id=unit_id)
    initial = {}
    if request.user.is_authenticated:
        initial['name'] = request.user.get_full_name() or request.user.username
        initial['phone'] = getattr(request.user.profile, 'phone', '')
    if request.method == 'POST':
        form = ViewingRequestForm(request.POST)
        if form.is_valid():
            viewing = form.save(commit=False)
            viewing.unit = unit
            if request.user.is_authenticated:
                viewing.requester = request.user
            viewing.save()
            _record_contact_lead(request, unit, ContactLead.VIEWING)
            messages.success(request, 'Viewing request sent. The caretaker can follow up with you.')
            return redirect(unit.building.get_absolute_url())
    else:
        form = ViewingRequestForm(initial=initial)
    return render(request, 'rentals/request_viewing.html', {'form': form, 'unit': unit})



def contact_caretaker(request, unit_id, method):
    unit = get_object_or_404(_public_units_queryset().select_related('building', 'building__caretaker__profile'), id=unit_id)
    phone = unit.building.caretaker.profile.phone
    if not phone:
        messages.error(request, 'Caretaker phone number is not available yet.')
        return redirect(unit.building.get_absolute_url())
    if method not in [ContactLead.CALL, ContactLead.WHATSAPP]:
        return HttpResponseForbidden('Unknown contact method.')
    _record_contact_lead(request, unit, method)
    if method == ContactLead.WHATSAPP:
        text = urllib.parse.quote(f'Hello, I saw the {unit.get_unit_type_display()} at {unit.building.name} on RentWise. Is it still available for viewing?')
        return HttpResponseRedirect(f'https://wa.me/{_safe_phone_for_whatsapp(phone)}?text={text}')
    return render(request, 'rentals/contact_caretaker.html', {'unit': unit, 'phone': phone})


def report_listing(request, unit_id=None, building_id=None):
    unit = None
    if unit_id:
        unit = get_object_or_404(_public_units_queryset().select_related('building'), id=unit_id)
        building = unit.building
    else:
        building = get_object_or_404(_public_buildings_queryset(), id=building_id)

    initial = {}
    if request.user.is_authenticated:
        initial['name'] = request.user.get_full_name() or request.user.username
        initial['phone'] = getattr(request.user.profile, 'phone', '')
    if request.method == 'POST':
        form = ListingReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.unit = unit
            report.building = building
            report.reporter = request.user if request.user.is_authenticated else None
            report.save()
            messages.success(request, 'Thank you. The RentWise team will review this listing.')
            return redirect(building.get_absolute_url())
    else:
        form = ListingReportForm(initial=initial)
    return render(request, 'rentals/report_listing.html', {'form': form, 'building': building, 'unit': unit})


def seeker_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        profile = getattr(request.user, 'profile', None)
        if not (profile and profile.role == Profile.SEEKER):
            return HttpResponseForbidden('House seeker access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


@seeker_required
def seeker_dashboard(request):
    saved = (SavedProperty.objects
        .filter(user=request.user)
        .select_related('unit', 'unit__building', 'unit__building__area', 'unit__building__caretaker__profile', 'building', 'building__area')
        .prefetch_related('unit__images'))
    latest_units = _public_units_queryset().exclude(saved_by__user=request.user).order_by('rent')[:6]
    return render(request, 'rentals/seeker_dashboard.html', {
        'saved_properties': saved,
        'latest_units': latest_units,
    })


@require_POST
@login_required
def save_unit(request, pk):
    unit = get_object_or_404(_public_units_queryset().select_related('building'), pk=pk)
    profile = getattr(request.user, 'profile', None)
    if not (profile and profile.role == Profile.SEEKER):
        messages.error(request, 'Create a house seeker account to bookmark units.')
        return redirect(unit.building.get_absolute_url())
    SavedProperty.objects.get_or_create(user=request.user, unit=unit)
    messages.success(request, f'{unit.get_unit_type_display()} at {unit.building.name} added to your bookmarks.')
    return redirect(request.POST.get('next') or unit.building.get_absolute_url())


@require_POST
@login_required
def unsave_unit(request, pk):
    SavedProperty.objects.filter(user=request.user, unit_id=pk).delete()
    messages.info(request, 'Bookmarked unit removed.')
    return redirect(request.POST.get('next') or 'seeker_dashboard')


def assistant_chat(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None

    if request.method == 'POST':
        question = request.POST.get('message', '').strip()
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if question:
            AssistantMessage.objects.create(user=user, session_key=session_key, role=AssistantMessage.USER, content=question)
            reply = answer_question(question)
            AssistantMessage.objects.create(user=user, session_key=session_key, role=AssistantMessage.ASSISTANT, content=reply)
            if is_ajax:
                return JsonResponse({'ok': True, 'reply': reply})
        if is_ajax:
            return JsonResponse({'ok': False, 'error': 'Please enter a question.'}, status=400)
        return redirect('assistant')

    if user:
        messages_qs = AssistantMessage.objects.filter(user=user)
    else:
        messages_qs = AssistantMessage.objects.filter(session_key=session_key, user__isnull=True)
    return render(request, 'rentals/assistant.html', {'chat_messages': messages_qs.order_by('created_at')})


def caretaker_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        role = getattr(getattr(request.user, 'profile', None), 'role', Profile.SEEKER)
        if not (role in [Profile.CARETAKER, Profile.ADMIN] or request.user.is_staff):
            return HttpResponseForbidden('Caretaker access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


@caretaker_required
def caretaker_dashboard(request):
    buildings = Building.objects.filter(caretaker=request.user).prefetch_related('units')
    if is_platform_admin(request.user):
        buildings = Building.objects.select_related('caretaker', 'area').all().prefetch_related('units')
    return render(request, 'rentals/caretaker_dashboard.html', {'buildings': buildings, 'profile': getattr(request.user, 'profile', None)})


def is_platform_admin(user):
    profile = getattr(user, 'profile', None)
    return user.is_staff or (profile and profile.role == Profile.ADMIN)


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_platform_admin(request.user):
            return HttpResponseForbidden('Admin access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


@caretaker_required
def building_create(request):
    is_admin = is_platform_admin(request.user)
    FormClass = AdminBuildingForm if is_admin else BuildingForm
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            building = form.save(commit=False)
            if not is_admin:
                building.caretaker = request.user
            if not building.slug:
                base_slug = slugify(building.name)
                slug = base_slug
                counter = 2
                while Building.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1
                building.slug = slug
            building.save()
            if not is_platform_admin(request.user) and not request.user.profile.can_publish_listings:
                building.is_published = False
                building.save(update_fields=['is_published'])
                messages.info(request, 'Building saved as a draft. It will go public after admin approval and phone verification.')
            else:
                messages.success(request, 'Building saved.')
            return redirect('caretaker_dashboard')
    else:
        form = FormClass(initial={'latitude': -1.286389, 'longitude': 36.817223})
    return render(request, 'rentals/building_form.html', {'form': form, 'title': 'Add building'})


@caretaker_required
def building_edit(request, pk):
    building = get_object_or_404(Building, pk=pk)
    is_admin = is_platform_admin(request.user)
    if not (is_admin or building.caretaker == request.user):
        return HttpResponseForbidden('You can only edit your own buildings.')
    FormClass = AdminBuildingForm if is_admin else BuildingForm
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=building)
        if form.is_valid():
            building = form.save(commit=False)
            if not building.slug:
                base_slug = slugify(building.name)
                slug = base_slug
                counter = 2
                while Building.objects.filter(slug=slug).exclude(pk=building.pk).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1
                building.slug = slug
            building.save()
            if not is_platform_admin(request.user) and not request.user.profile.can_publish_listings:
                building.is_published = False
                building.save(update_fields=['is_published'])
                messages.info(request, 'Building updated. It remains hidden until admin approval and phone verification.')
            else:
                messages.success(request, 'Building updated.')
            return redirect('caretaker_dashboard')
    else:
        form = FormClass(instance=building)
    return render(request, 'rentals/building_form.html', {'form': form, 'title': 'Edit building'})


@caretaker_required
def unit_create(request):
    caretaker_filter = None if is_platform_admin(request.user) else request.user
    if request.method == 'POST':
        form = UnitForm(request.POST, request.FILES, caretaker=caretaker_filter)
        if form.is_valid():
            unit = form.save(commit=False)
            if not (is_platform_admin(request.user) or unit.building.caretaker == request.user):
                return HttpResponseForbidden('You can only add units to your own buildings.')
            unit.save()
            form.save_uploaded_images(unit)
            messages.success(request, 'Unit saved.')
            return redirect('caretaker_dashboard')
    else:
        form = UnitForm(caretaker=caretaker_filter)
    return render(request, 'rentals/unit_form.html', {'form': form, 'title': 'Add unit', 'unit': None})


@caretaker_required
def unit_edit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    caretaker_filter = None if is_platform_admin(request.user) else request.user
    if not (is_platform_admin(request.user) or unit.building.caretaker == request.user):
        return HttpResponseForbidden('You can only edit your own units.')
    if request.method == 'POST':
        form = UnitForm(request.POST, request.FILES, instance=unit, caretaker=caretaker_filter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Unit updated.')
            return redirect('caretaker_dashboard')
    else:
        form = UnitForm(instance=unit, caretaker=caretaker_filter)
    return render(request, 'rentals/unit_form.html', {'form': form, 'title': 'Edit unit', 'unit': unit})


@admin_required
def admin_caretaker_list(request):
    caretakers = (
        User.objects.filter(profile__role=Profile.CARETAKER)
        .select_related('profile')
        .annotate(building_count=Count('buildings'), unit_count=Count('buildings__units'))
        .order_by('username')
    )
    context = {
        'caretakers': caretakers,
        'total_caretakers': caretakers.count(),
        'total_buildings': Building.objects.count(),
        'total_units': Unit.objects.count(),
        'available_units': _public_units_queryset().count(),
        'pending_caretakers': caretakers.filter(profile__approval_status=Profile.PENDING).count(),
        'recent_searches': SearchEvent.objects.count(),
        'viewing_requests': ViewingRequest.objects.count(),
    }
    return render(request, 'rentals/admin_caretaker_list.html', context)


@admin_required
def admin_caretaker_create(request):
    if request.method == 'POST':
        form = CaretakerCreateForm(request.POST)
        if form.is_valid():
            caretaker = form.save()
            messages.success(request, 'Caretaker account created.')
            return redirect('admin_caretaker_detail', caretaker.id)
    else:
        form = CaretakerCreateForm()
    return render(request, 'rentals/admin_caretaker_form.html', {'form': form, 'title': 'Create caretaker'})


@admin_required
def admin_caretaker_detail(request, pk):
    caretaker = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    buildings = Building.objects.filter(caretaker=caretaker).select_related('area').prefetch_related('units', 'units__images')
    total_available = Unit.objects.filter(building__caretaker=caretaker, status=Unit.AVAILABLE).count()
    return render(request, 'rentals/admin_caretaker_detail.html', {
        'caretaker': caretaker,
        'buildings': buildings,
        'total_available': total_available,
    })


@admin_required
def admin_caretaker_edit(request, pk):
    caretaker = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    if request.method == 'POST':
        form = CaretakerProfileForm(request.POST, instance=caretaker.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caretaker profile updated.')
            return redirect('admin_caretaker_detail', caretaker.id)
    else:
        form = CaretakerProfileForm(instance=caretaker.profile)
    return render(request, 'rentals/admin_caretaker_form.html', {'form': form, 'title': f'Edit {caretaker.username}'})



@admin_required
def admin_analytics(request):
    top_searches = SearchEvent.objects.exclude(query='').values('query').annotate(count=Count('id')).order_by('-count')[:10]
    latest_searches = SearchEvent.objects.order_by('-created_at')[:20]
    latest_requests = ViewingRequest.objects.select_related('unit', 'unit__building').order_by('-created_at')[:20]
    latest_leads = ContactLead.objects.select_related('unit', 'unit__building').order_by('-created_at')[:20]
    open_reports = ListingReport.objects.select_related('unit', 'building').filter(status=ListingReport.OPEN).order_by('-created_at')[:20]
    return render(request, 'rentals/admin_analytics.html', {
        'top_searches': top_searches,
        'latest_searches': latest_searches,
        'latest_requests': latest_requests,
        'total_searches': SearchEvent.objects.count(),
        'total_requests': ViewingRequest.objects.count(),
        'total_leads': ContactLead.objects.count(),
        'open_report_count': ListingReport.objects.filter(status=ListingReport.OPEN).count(),
        'latest_leads': latest_leads,
        'open_reports': open_reports,
        'assistant_messages': AssistantMessage.objects.count(),
    })


@require_POST
@admin_required
def admin_caretaker_action(request, pk):
    caretaker = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    action = request.POST.get('action')
    profile = caretaker.profile
    if action == 'approve':
        profile.approval_status = Profile.APPROVED
        profile.approved_at = timezone.now()
        messages.success(request, 'Caretaker approved.')
    elif action == 'reject':
        profile.approval_status = Profile.REJECTED
        messages.info(request, 'Caretaker rejected.')
    elif action == 'suspend':
        profile.approval_status = Profile.SUSPENDED
        Building.objects.filter(caretaker=caretaker).update(is_published=False)
        messages.warning(request, 'Caretaker suspended and their buildings were hidden.')
    elif action == 'verify_phone':
        profile.phone_verified = True
        messages.success(request, 'Caretaker phone marked as verified.')
    elif action == 'unverify_phone':
        profile.phone_verified = False
        Building.objects.filter(caretaker=caretaker).update(is_published=False)
        messages.warning(request, 'Phone verification removed and buildings were hidden.')
    else:
        messages.error(request, 'Unknown admin action.')
        return redirect('admin_caretaker_detail', caretaker.id)
    profile.save(update_fields=['approval_status', 'approved_at', 'phone_verified'])
    return redirect('admin_caretaker_detail', caretaker.id)


def terms(request):
    return render(request, 'rentals/terms.html')


def privacy(request):
    return render(request, 'rentals/privacy.html')


def contact(request):
    return render(request, 'rentals/contact.html')


@require_POST
@caretaker_required
def unit_toggle_available(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    if not (is_platform_admin(request.user) or unit.building.caretaker == request.user):
        return HttpResponseForbidden('You can only update your own units.')
    unit.status = Unit.OCCUPIED if unit.status == Unit.AVAILABLE else Unit.AVAILABLE
    unit.save(update_fields=['status'])
    return redirect('caretaker_dashboard')
