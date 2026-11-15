"""Read spatial PDF words, never guess a competition or approval identity.

The independent content-stream extraction must account for the same characters
as the coordinate extraction. Missing text is a review hold, not a dictionary
repair. Existing exact identity/scope checks remain in force.
"""
from collections import Counter
from textwrap import dedent


def characters(text):
    for ligature, replacement in [('ﬁ', 'fi'), ('ﬂ', 'fl'), ('ﬀ', 'ff'), ('ﬃ', 'ffi'), ('ﬄ', 'ffl')]:
        text = text.replace(ligature, replacement)
    return Counter(character for character in text if not character.isspace())


def extract_verified_page(page, spatial_page, *, page_number):
    plain = page.extract_text() or ""
    layout = spatial_page.extract_text(layout=True) or ""
    if not plain.strip() or not layout.strip():
        raise ValueError(f"Catalog PDF page {page_number} has no extractable text; review required")
    if characters(plain) != characters(layout):
        raise ValueError(f"Catalog PDF page {page_number} extraction disagrees; review required")
    return dedent(layout)


def validate_split_parents(catalog, season_map):
    """A changed legal scope needs mapping review, never approximate approval."""
    legal = {section['sport']: section['lines'] for section in catalog['sections']}
    for sport in season_map.get('sports', []):
        for group in sport.get('groups', []):
            for event in group.get('events', []):
                if not event.get('coverage_children'):
                    continue
                parent = event.get('catalog_event', '')
                if not parent or not any(line == parent or line.startswith(parent + ' - ') or
                                         line.startswith(parent + ' | ')
                                         for line in legal.get(sport['sport'], [])):
                    raise ValueError(f"Catalog legal parent missing; review required: {sport['sport']} / {parent}")
