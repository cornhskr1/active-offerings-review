"""App-owned proof for one reviewed held basketball provenance transition.

Private data supplies no validator or allowlist. The exact prior public screening,
prior public catalog and replacement must match reviewed hashes. Both old clocks
are required unchanged; no source hold or age evidence can be refreshed here.
"""
from copy import deepcopy
import hashlib
from scripts.snapshot_semantic_guards import canonical

PATH = 'data/ncaa-basketball-intelligence.json'
CATALOG = 'data/catalog-live.json'
BEFORE = 'fc93c9f0059c7fe4ca5ab3f354b48e996e9da6a35963ca20b918368be8dcb5b3'
AFTER = 'ca86740abcaa8b971ff85a241493071f57077bf146f541210292ebdcd0d935b6'
CATALOG_HASH = '77af391ebfc40d9c108a83a17a09346b9416c0b64de8d4d4c897e7f6519d77bc'
CLOCKS = ('generated_at', 'screening_date')
PROVENANCE = ('catalog_source', 'catalog_version')


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def proven_candidate(previous, candidate, catalog):
    """Prove the exact replacement, never normalize consumer input."""
    if not all(isinstance(value, dict) for value in (previous, candidate, catalog)):
        return None
    if digest(previous) != BEFORE or digest(catalog) != CATALOG_HASH or digest(candidate) != AFTER:
        return None
    if any(not isinstance(previous.get(key), str) or candidate.get(key) != previous[key] for key in CLOCKS):
        return None
    old_rules, new_rules = previous.get('catalog_special_rules'), candidate.get('catalog_special_rules')
    if not isinstance(old_rules, list) or not isinstance(new_rules, list) or len(old_rules) != len(new_rules):
        return None
    lines = [line for section in catalog.get('sections', [])
             if section.get('sport') == 'NCAA Basketball' for line in section.get('lines', [])]
    stripped = deepcopy(candidate)
    for old, new, restore in zip(old_rules, new_rules, stripped['catalog_special_rules']):
        if (new.get('catalog_line') not in lines
                or new.get('catalog_source') != catalog.get('source_label')
                or new.get('catalog_version') != catalog.get('menu_version')):
            return None
        for key in PROVENANCE:
            restore[key] = old[key]
    if canonical(stripped) != canonical(previous):
        return None
    return deepcopy(candidate)


def retention_baselines(previous, current):
    """Independently prove the transition against restored public history."""
    if PATH not in current:
        return previous
    proved = proven_candidate(previous.get(PATH), current[PATH], previous.get(CATALOG))
    if proved is None:
        return previous
    return {**previous, PATH: proved}
