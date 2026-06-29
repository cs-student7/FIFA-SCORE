"""
Template filter that converts a country/team name (e.g. "Portugal", "Uzbekistan")
into a flag image URL, using flagcdn.com + pycountry for name -> ISO code lookup.

Usage in templates:
    {% load flags %}
    <img src="{{ m.home_team_name_en|country_flag }}" ...>
"""
from django import template

register = template.Library()

try:
    import pycountry
except ImportError:
    pycountry = None

_FLAG_CACHE = {}

MANUAL_ALIASES = {
    'usa': 'US',
    'united states': 'US',
    'south korea': 'KR',
    'north korea': 'KP',
    'ivory coast': 'CI',
    'czech republic': 'CZ',
    'czechia': 'CZ',
    'england': 'GB',
    'wales': 'GB',
    'scotland': 'GB',
    'congo dr': 'CD',
    'democratic republic of the congo': 'CD',
    'cape verde': 'CV',
    'iran': 'IR',
    'russia': 'RU',
    'uae': 'AE',
    'bosnia': 'BA',
    'bosnia and herzegovina': 'BA',
}


@register.filter
def country_flag(name):
    """Return a flagcdn.com URL for the given country/team name, or empty string."""
    if not name:
        return ''

    key = name.strip().lower()
    if key in _FLAG_CACHE:
        return _FLAG_CACHE[key]

    alpha2 = MANUAL_ALIASES.get(key)

    if not alpha2 and pycountry:
        try:
            matches = pycountry.countries.search_fuzzy(name)
            if matches:
                alpha2 = matches[0].alpha_2
        except LookupError:
            alpha2 = None

    url = f"https://flagcdn.com/w40/{alpha2.lower()}.png" if alpha2 else ''
    _FLAG_CACHE[key] = url
    return url