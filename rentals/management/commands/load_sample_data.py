from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify

from accounts.models import Profile
from rentals.models import Area, Building, SavedProperty, Unit, UnitImage


class Command(BaseCommand):
    help = 'Load sample Nairobi rental data for local testing.'

    def _user(self, username, password, role=Profile.SEEKER, email='', phone='', first_name='', last_name='', staff=False, superuser=False):
        user, _ = User.objects.get_or_create(username=username, defaults={'email': email})
        user.set_password(password)
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_staff = staff
        user.is_superuser = superuser
        user.save()
        user.profile.role = role
        user.profile.phone = phone
        if role in [Profile.ADMIN, Profile.CARETAKER]:
            user.profile.approval_status = Profile.APPROVED
            user.profile.phone_verified = bool(phone)
        user.profile.save()
        return user

    def handle(self, *args, **options):
        demo = self._user('demo', 'demo12345', Profile.SEEKER, 'demo@example.com', '0700000000', 'Demo', 'Seeker')
        self._user('platformadmin', 'admin12345', Profile.ADMIN, 'admin@rentwise.local', '0700111222', 'Platform', 'Admin', staff=True, superuser=True)

        caretaker_one = self._user('caretaker', 'caretaker12345', Profile.CARETAKER, 'caretaker@example.com', '0712345678', 'Mary', 'Wanjiku')
        caretaker_two = self._user('caretaker2', 'caretaker12345', Profile.CARETAKER, 'caretaker2@example.com', '0722333444', 'Brian', 'Otieno')
        caretaker_three = self._user('caretaker3', 'caretaker12345', Profile.CARETAKER, 'caretaker3@example.com', '0733555666', 'Amina', 'Mohamed')

        caretakers = {
            'caretaker': caretaker_one,
            'caretaker2': caretaker_two,
            'caretaker3': caretaker_three,
        }

        areas = [
            ('Roysambu', -1.217900, 36.887200, 'Popular for students and young workers near Thika Road and TRM.'),
            ('Kasarani', -1.226700, 36.902800, 'Residential area with access to Thika Road and sports facilities.'),
            ('Ruaka', -1.204400, 36.776200, 'Fast-growing area near Two Rivers and Limuru Road.'),
            ('Kilimani', -1.292100, 36.783700, 'Central Nairobi apartment area near offices and social amenities.'),
            ('South B', -1.313400, 36.838100, 'Estate close to Mombasa Road, CBD, and Industrial Area.'),
            ('Donholm', -1.296700, 36.895900, 'Eastlands residential area with access to Outer Ring Road.'),
        ]
        area_objs = {}
        for name, lat, lng, desc in areas:
            area_objs[name], _ = Area.objects.update_or_create(
                slug=slugify(name),
                defaults={'name': name, 'latitude': lat, 'longitude': lng, 'description': desc},
            )

        building_data = [
            ('caretaker', 'Sunrise Court', 'Roysambu', 'Near TRM Mall', -1.218650, 36.886180, 'Clean building near shops and matatu stops.', 'Bedsitter from 8,500'),
            ('caretaker', 'Mirema Heights', 'Roysambu', 'Mirema Drive', -1.210300, 36.889450, 'Quiet building with good access to Thika Road.', 'One bedroom from 16,000'),
            ('caretaker2', 'Arena View Apartments', 'Kasarani', 'Near Kasarani Stadium', -1.225900, 36.902200, 'Suitable for workers and students around Kasarani.', 'Bedsitter from 9,000'),
            ('caretaker2', 'Ruaka Ridge', 'Ruaka', 'Near Quickmart Ruaka', -1.203600, 36.776900, 'Modern apartments with easy access to Limuru Road.', 'Studio from 14,000'),
            ('caretaker3', 'Kilele Suites', 'Kilimani', 'Near Yaya Centre', -1.292800, 36.786100, 'Premium apartments in a central location.', 'One bedroom from 38,000'),
            ('caretaker3', 'Hazina Court', 'South B', 'Near South B shopping centre', -1.312700, 36.838600, 'Good access to town and Industrial Area.', 'One bedroom from 22,000'),
        ]
        sample_saved_units = []
        for caretaker_key, name, area, landmark, lat, lng, desc, amenity in building_data:
            b, _ = Building.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    'caretaker': caretakers[caretaker_key],
                    'area': area_objs[area],
                    'name': name,
                    'landmark': landmark,
                    'latitude': lat,
                    'longitude': lng,
                    'description': desc,
                    'amenities': amenity + ', water, security, prepaid electricity',
                    'image_url': 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1200&q=80',
                    'is_published': True,
                },
            )
            bedsitter_rent = 8500 if area == 'Roysambu' else 9500
            one_bedroom_rent = 16000 if area in ['Roysambu', 'Kasarani'] else 22000
            bedsitter, _ = Unit.objects.get_or_create(
                building=b,
                unit_type='bedsitter',
                label='A1',
                defaults={
                    'rent': bedsitter_rent,
                    'deposit': bedsitter_rent,
                    'service_charge': 500,
                    'status': Unit.AVAILABLE,
                    'notes': 'Clean unit with tiled floor and good natural light.',
                },
            )
            if len(sample_saved_units) < 2:
                sample_saved_units.append(bedsitter)
            one_bedroom, _ = Unit.objects.get_or_create(
                building=b,
                unit_type='one_bedroom',
                label='B2',
                defaults={
                    'rent': one_bedroom_rent,
                    'deposit': one_bedroom_rent,
                    'service_charge': 1000,
                    'status': Unit.AVAILABLE,
                    'notes': 'One bedroom unit with separate living area and kitchen space.',
                },
            )
            for unit, urls in {
                bedsitter: [
                    'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80',
                ],
                one_bedroom: [
                    'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1556911220-bff31c812dba?auto=format&fit=crop&w=900&q=80',
                ],
            }.items():
                for index, url in enumerate(urls):
                    UnitImage.objects.get_or_create(unit=unit, image_url=url, defaults={'sort_order': index})

        for unit in sample_saved_units:
            SavedProperty.objects.get_or_create(user=demo, unit=unit)

        self.stdout.write(self.style.SUCCESS(
            'Sample data loaded. Accounts: demo/demo12345, platformadmin/admin12345, '
            'caretaker/caretaker12345, caretaker2/caretaker12345, caretaker3/caretaker12345'
        ))
