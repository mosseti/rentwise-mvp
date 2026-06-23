from django.conf import settings


def public_settings(request):
    return {
        'MAP_PROVIDER': settings.MAP_PROVIDER,
        'GEOCODER_PROVIDER': settings.GEOCODER_PROVIDER,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'AI_PROVIDER_READY': bool(settings.GEMINI_API_KEY),
        'AI_PROVIDER_NAME': 'Gemini API' if settings.GEMINI_API_KEY else 'Local Fallback',
    }
