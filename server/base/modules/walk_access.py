"""OSM tagged access only; not a live opening or accessibility guarantee."""
DENIED = {'no', 'private', 'customers', 'permit', 'delivery', 'agricultural', 'forestry', 'use_sidepath'}
ALLOWED = {'yes', 'designated', 'permissive'}

def pedestrian_access_allowed(tags, *, node=False):
    if tags.get('construction') not in (None, '', 'no') or tags.get('proposed') not in (None, '', 'no'):
        return False
    foot = tags.get('foot', '')
    if foot in DENIED or (foot not in ALLOWED and tags.get('access') in DENIED):
        return False
    if node and (tags.get('locked') == 'yes' or tags.get('barrier') in {'wall', 'fence', 'hedge'}):
        return False
    return True
