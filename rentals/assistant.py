import json
import re
import urllib.request
from django.conf import settings
from django.db.models import Q

from accounts.models import Profile
from .models import Area, Building, Unit


NEARBY_AREAS = {
    'roysambu': ['Kasarani', 'Zimmerman', 'Mirema', 'Githurai', 'Kahawa West'],
    'kasarani': ['Roysambu', 'Mwiki', 'Zimmerman', 'Mirema', 'Githurai'],
    'zimmerman': ['Roysambu', 'Kasarani', 'Mirema', 'Githurai'],
    'mirema': ['Roysambu', 'Kasarani', 'Zimmerman'],
    'kahawa': ['Kahawa Sukari', 'Kahawa West', 'Ruiru', 'Githurai', 'Roysambu'],
    'kahawa wendani': ['Kahawa Sukari', 'Kahawa West', 'Ruiru', 'Githurai', 'Roysambu'],
    'ruaka': ['Muchatha', 'Two Rivers', 'Runda', 'Kitisuru'],
    'kilimani': ['Kileleshwa', 'Lavington', 'Yaya', 'Ngong Road'],
    'donholm': ['Umoja', 'Buruburu', 'Tena', 'Embakasi'],
    'south b': ['South C', 'Mombasa Road', 'Industrial Area'],
    'embakasi': ['Pipeline', 'Donholm', 'Fedha', 'Tassia'],
    'pipeline': ['Embakasi', 'Fedha', 'Tassia', 'Donholm'],
    'rongai': ['Kiserian', 'Karen', 'Ngong'],
    'umoja': ['Donholm', 'Buruburu', 'Tena', 'Kayole'],
}


SMALL_TALK = {'hello', 'hi', 'hey', 'hallo', 'jambo', 'sasa', 'niaje'}
VAGUE_TEXT = {'what', 'what?', 'help', 'help me', 'assist', 'start'}

ADVICE_KEYWORDS = [
    'what should i look', 'what to look', 'characteristic', 'characteristics', 'qualities',
    'features', 'consider', 'before paying', 'before i pay', 'deposit', 'safety', 'safe',
    'avoid fake', 'scam', 'landlord', 'caretaker genuine', 'receipt', 'viewing',
    'water', 'electricity', 'tokens', 'security', 'transport', 'commute', 'noise',
    'flood', 'drainage', 'checklist', 'advise', 'advice', 'tips', 'choose', 'choosing',
    'compare', 'better area', 'which area', 'documents', 'agreement', 'contract'
]

SEARCH_INTENT_WORDS = [
    'find', 'show', 'available', 'vacant', 'listing', 'listings', 'option', 'options',
    'near', 'around', 'within', 'under', 'below', 'budget', 'rent for', 'houses in',
    'house in', 'bedsitter', 'bed sitter', 'studio', 'one bedroom', '1 bedroom',
    'two bedroom', '2 bedroom', 'apartment in', 'unit in'
]


def _wants_advice(question):
    t = _normalize(question)
    return any(word in t for word in ADVICE_KEYWORDS)


def _wants_listings(question):
    t = _normalize(question)
    return (
        any(word in t for word in SEARCH_INTENT_WORDS)
        or bool(_unit_type_from_text(question))
        or bool(_money_from_text(question))
        or (bool(_area_from_text(question)) and any(w in t for w in ['house', 'rent', 'rental', 'unit', 'apartment', 'room']))
    )


def _assistant_intent(question):
    """Classify the message before touching listings.

    The assistant should be general enough to answer normal questions, but it must
    return to RentWise listings immediately when the user asks about houses, rent,
    locations, units, availability, deposits, safety, or moving.
    """
    if _is_greeting(question):
        return 'greeting'
    if _is_vague(question):
        return 'vague'
    wants_advice = _wants_advice(question)
    wants_listings = _wants_listings(question)
    normalized = _normalize(question)
    # Phrases such as "apart from the houses in the database" are explicitly
    # asking for guidance, not for available unit results.
    if wants_advice and any(phrase in normalized for phrase in ['apart from', 'besides', 'other than', 'not the listings', 'not houses']):
        return 'advice'
    if wants_advice and not wants_listings:
        return 'advice'
    if wants_advice and wants_listings:
        return 'mixed'
    if wants_listings:
        return 'search'
    return 'general'


def _advice_answer(question, include_listing_hint=False):
    t = _normalize(question)
    lines = []

    if 'deposit' in t or 'pay' in t or 'receipt' in t or 'scam' in t or 'fake' in t:
        lines.append('Before paying anything, physically view the exact unit, confirm the caretaker or landlord is genuine, and ask for a written receipt with the building name, unit number, amount paid, and balance.')
        lines.append('Avoid paying through a personal number unless the person is verified and you have seen the unit; if possible, pay through an official till/paybill or documented landlord account.')
    elif 'safe' in t or 'safety' in t or 'security' in t:
        lines.append('For safety, visit the building during the day and also check the area in the evening if possible.')
        lines.append('Look for working gates, lighting, secure locks, controlled access, nearby transport, and whether current tenants feel safe walking home.')
    elif 'compare' in t or 'which area' in t or 'better area' in t or 'commute' in t:
        lines.append('When comparing areas, judge them by total monthly cost, commute time, safety at night, water reliability, noise, access to shops/transport, and how easy it is to reach work or school.')
        lines.append('A cheaper unit can become expensive if transport is high, water is unreliable, or the route is unsafe late in the evening.')
    else:
        lines.append('Apart from the houses listed in RentWise, judge a house by the full living experience, not rent alone.')
        lines.append('Check water availability and pressure, electricity/token setup, security, lighting, door and window locks, drainage during rain, network strength, noise, ventilation, cleanliness, and distance to transport or work.')
        lines.append('Also confirm the total move-in cost, deposit terms, garbage/water/service charges, house rules, and whether the caretaker or landlord gives receipts.')

    lines.append('Speak to at least one current tenant if you can, and do not pay a deposit before viewing the exact unit you will occupy.')
    if include_listing_hint:
        lines.append('If you also want available RentWise options, tell me the area, unit type, and budget, for example: bedsitter near Roysambu under KSh 10,000.')
    return '\n'.join(lines)


def _general_answer(question):
    """Local fallback for non-rental questions when Gemini is not available.

    It answers briefly where possible and then gives the user an easy path back to
    rental search. Gemini can replace this with a richer general answer when the
    API key is connected.
    """
    t = _normalize(question)
    if 'color' in t or 'colour' in t:
        return (
            'For color, a rental website or marketplace theme can use navy, white, and warm orange because they feel trustworthy, clean, and action-oriented. '
            'For house interiors, light neutrals such as white, cream, beige, or soft gray usually make rooms feel brighter and larger. '
            'When you are ready to search homes again, tell me the area, unit type, and budget.'
        )
    return (
        'I can answer general questions too. For this app, I will keep the answer practical and then help you return to rentals when needed. '
        'If your question is about a house, area, rent, deposit, safety, or moving, tell me the location and budget so I can check verified RentWise listings.'
    )


def _normalize(text):
    return re.sub(r'\s+', ' ', text.lower().strip())


def _money_from_text(text):
    text = text.lower().replace(',', '')
    match = re.search(r'(?:under|below|less than|max|maximum|budget|ksh|kes)\s*(\d{4,6})', text)
    if match:
        return int(match.group(1))
    short = re.search(r'(\d{1,3})\s*k\b', text)
    if short:
        return int(short.group(1)) * 1000
    return None


def _unit_type_from_text(text):
    t = text.lower()
    if 'bedsitter' in t or 'bed sitter' in t:
        return 'bedsitter'
    if 'studio' in t:
        return 'studio'
    if 'one bedroom' in t or '1 bedroom' in t or '1br' in t or '1 br' in t:
        return 'one_bedroom'
    if 'two bedroom' in t or '2 bedroom' in t or '2br' in t or '2 br' in t:
        return 'two_bedroom'
    if 'three bedroom' in t or '3 bedroom' in t or '3br' in t or '3 br' in t:
        return 'three_bedroom'
    if 'shop' in t:
        return 'shop'
    return None


def _area_from_text(text):
    t = _normalize(text)

    # Prefer exact saved RentWise areas first.
    for area in Area.objects.all().only('name'):
        name = _normalize(area.name)
        if name and name in t:
            return name

    # Then check building landmarks/names because users often search malls, stages, roads, or estates.
    for building in Building.objects.filter(is_published=True, caretaker__profile__approval_status=Profile.APPROVED, caretaker__profile__phone_verified=True).select_related('area')[:300]:
        candidates = [building.name, building.landmark, building.area.name]
        for candidate in candidates:
            c = _normalize(candidate or '')
            if c and len(c) > 2 and c in t:
                return _normalize(building.area.name)

    known = [
        'kahawa wendani', 'roysambu', 'kasarani', 'ruaka', 'kilimani', 'donholm',
        'south b', 'embakasi', 'rongai', 'umoja', 'kahawa', 'pipeline',
        'zimmerman', 'mirema', 'githurai', 'ruiru', 'kikuyu', 'westlands', 'ngong',
    ]
    for area in known:
        if area in t:
            return area
    return None


def _is_greeting(question):
    return _normalize(question) in SMALL_TALK


def _is_vague(question):
    return _normalize(question) in VAGUE_TEXT


def _looks_like_rental_search(question):
    return _assistant_intent(question) in {'search', 'mixed'}


def matching_units(question, limit=10):
    """Return database listings likely relevant to the user's question.

    The assistant is allowed to recommend only these records. This keeps answers grounded
    and avoids invented houses.
    """
    max_rent = _money_from_text(question)
    unit_type = _unit_type_from_text(question)
    area = _area_from_text(question)

    qs = Unit.objects.select_related('building', 'building__area', 'building__caretaker__profile').filter(
        status=Unit.AVAILABLE,
        building__is_published=True,
        building__caretaker__profile__approval_status=Profile.APPROVED,
        building__caretaker__profile__phone_verified=True,
    )
    if max_rent:
        qs = qs.filter(rent__lte=max_rent)
    if unit_type:
        qs = qs.filter(unit_type=unit_type)
    if area:
        qs = qs.filter(
            Q(building__area__name__icontains=area)
            | Q(building__landmark__icontains=area)
            | Q(building__name__icontains=area)
        )
    return list(qs.order_by('rent')[:limit])


def _alternative_units(question, limit=5):
    """Useful fallback options when the exact area has no available listing."""
    max_rent = _money_from_text(question)
    unit_type = _unit_type_from_text(question)
    qs = Unit.objects.select_related('building', 'building__area', 'building__caretaker__profile').filter(
        status=Unit.AVAILABLE,
        building__is_published=True,
        building__caretaker__profile__approval_status=Profile.APPROVED,
        building__caretaker__profile__phone_verified=True,
    )
    if max_rent:
        qs = qs.filter(rent__lte=max_rent)
    if unit_type:
        qs = qs.filter(unit_type=unit_type)
    return list(qs.order_by('rent')[:limit])


def _format_listings(units):
    if not units:
        return 'No matching available listings were found in the current RentWise database.'
    lines = []
    for u in units:
        lines.append(
            f"ID {u.id}: {u.get_unit_type_display()} at {u.building.name}, {u.building.area.name}; "
            f"rent KSh {u.rent:,}; move-in about KSh {u.move_in_cost:,}; "
            f"landmark: {u.building.landmark or 'not specified'}; amenities: {u.building.amenities or 'not specified'}; "
            f"notes: {u.notes or 'none'}"
        )
    return "\n".join(lines)


def _system_prompt():
    return (
        'You are RentWise Assistant. You can answer general questions, but you are strongest as a Nairobi rental assistant. '
        'First respect the user intent. If the user asks a general non-rental question, answer it briefly and naturally, then connect back to homes only if helpful. '
        'If the user asks for advice about renting, give practical Kenya-specific advice. '
        'If the app provides listings, use only those listings as real options. '
        'Do not invent rental listings, caretakers, prices, or availability. '
        'If there are no matching listings, clearly say none are currently verified in that area. '
        'Answer in 4 to 8 useful sentences. Do not use markdown tables.'
    )


def _unit_line(u):
    return (
        f"- {u.get_unit_type_display()} at {u.building.name}, {u.building.area.name}: "
        f"KSh {u.rent:,} rent, move-in about KSh {u.move_in_cost:,}. "
        f"Landmark: {u.building.landmark or 'not specified'}."
    )


def _database_answer(question, relevant_units):
    area = _area_from_text(question)
    unit_type = _unit_type_from_text(question)
    max_rent = _money_from_text(question)
    intent = _assistant_intent(question)

    if intent == 'general':
        return _general_answer(question)

    if intent == 'advice':
        return _advice_answer(question, include_listing_hint=True)

    if intent == 'mixed' and not relevant_units:
        advice = _advice_answer(question, include_listing_hint=False)
        search_note = []
        if area:
            search_note.append(f'I also checked {area.title()} in the current RentWise database, but no verified available unit is currently listed there.')
            nearby = NEARBY_AREAS.get(area, NEARBY_AREAS.get(area.split()[0], []))
            if nearby:
                search_note.append('Try nearby areas such as ' + ', '.join(nearby[:5]) + ', or increase the map search radius.')
        return advice + '\n' + '\n'.join(search_note) if search_note else advice

    if _is_greeting(question):
        return (
            'Hello! I am RentWise Assistant. Tell me the area, unit type, and budget you want, '
            'for example: Find a bedsitter in Roysambu under KSh 10,000. I will check verified RentWise listings first and avoid inventing houses.'
        )

    if _is_vague(question):
        return (
            'I can help you search for verified rentals, compare areas, or know what to check before paying deposit. '
            'Please tell me the area and budget, for example: I need a bedsitter near Kahawa Wendani under KSh 12,000.'
        )

    if relevant_units:
        lines = []
        if area:
            lines.append(f'I checked the current RentWise database for {area.title()}.')
        else:
            lines.append('I checked the current RentWise database for your request.')
        lines.append('Here are verified available options:')
        for u in relevant_units[:5]:
            lines.append(_unit_line(u))
        lines.append('Open the building page to view photos, confirm availability, and call the caretaker before visiting. Do not pay deposit before viewing and getting a receipt.')
        return '\n'.join(lines)

    if _looks_like_rental_search(question):
        lines = []
        if area:
            lines.append(f'I checked {area.title()} in the current RentWise database.')
            lines.append('No verified available unit is currently listed there.')
            nearby = NEARBY_AREAS.get(area, NEARBY_AREAS.get(area.split()[0], []))
            if nearby:
                lines.append('Try nearby areas such as ' + ', '.join(nearby[:5]) + ', or increase the map search radius.')
        else:
            lines.append('I checked the current RentWise database, but I could not identify an exact area from your message.')
            lines.append('Tell me the estate, road, mall, or landmark so I can narrow it down.')

        alternatives = _alternative_units(question)
        if alternatives:
            lines.append('Verified options currently available elsewhere in RentWise include:')
            for u in alternatives[:3]:
                lines.append(_unit_line(u))
        lines.append('If you must live in that exact area, also walk around and ask caretakers directly because some vacant units may not yet be listed online.')
        return '\n'.join(lines)

    return (
        'I can help with Nairobi rental search and safety. Ask me with an area, unit type, and budget, '
        'for example: Find a one bedroom near Kasarani under KSh 18,000.'
    )


def _answer_with_gemini(question, listing_context, database_answer):
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}'
    prompt = (
        f'{_system_prompt()}\n\n'
        f'Database answer already prepared by RentWise:\n{database_answer}\n\n'
        f'Current relevant RentWise listings:\n{listing_context}\n\n'
        f'User question: {question}\n\n'
        'Improve the answer if helpful, but keep the same facts and do not begin with a greeting.'
    )
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.25, 'maxOutputTokens': 800},
    }
    data = json.dumps(body).encode('utf-8')
    request = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode('utf-8'))
    candidates = payload.get('candidates') or []
    if not candidates:
        raise RuntimeError('Gemini returned no candidates')
    parts = candidates[0].get('content', {}).get('parts', [])
    text = ''.join(part.get('text', '') for part in parts).strip()
    if not text:
        raise RuntimeError('Gemini returned an empty answer')
    return text


def _is_bad_ai_answer(text, question):
    plain = _normalize(text)
    if len(plain) < 120 and ('hello' in plain or 'rentwise assistant' in plain):
        return True
    intent = _assistant_intent(question)
    if intent in {'search', 'mixed'} and not any(word in plain for word in ['verified', 'available', 'listed', 'database', 'rent', 'ksh', 'area']):
        return True
    if intent == 'advice' and any(word in plain for word in ['sunrise court', 'mirema heights', 'arena view', 'ruaka ridge', 'kilele suites']):
        return True
    if intent == 'general' and any(word in plain for word in ['sunrise court', 'mirema heights', 'arena view', 'ruaka ridge', 'kilele suites']):
        return True
    return False


def answer_question(question):
    """Answer with a database-first response, enhanced by Gemini when configured.

    The database answer is always prepared first so Gemini cannot produce a greeting-only
    or invented-listing answer. If Gemini fails or gives a weak response, the safe
    RentWise database answer is shown instead.
    """
    intent = _assistant_intent(question)
    relevant_units = matching_units(question) if intent in {'search', 'mixed'} else []
    if intent in {'search', 'mixed'}:
        listing_context = _format_listings(relevant_units)
    elif intent == 'advice':
        listing_context = 'No listing search was needed because the user asked for rental advice.'
    else:
        listing_context = 'No listing search was needed because the user asked a general question.'
    database_answer = _database_answer(question, relevant_units)

    if settings.GEMINI_API_KEY and getattr(settings, 'AI_PROVIDER', 'gemini') == 'gemini':
        try:
            ai_answer = _answer_with_gemini(question, listing_context, database_answer)
            if not _is_bad_ai_answer(ai_answer, question):
                return ai_answer
        except Exception:
            pass

    return database_answer
