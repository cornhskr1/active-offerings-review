"""Permission boundaries for tennis browsing and retained public evidence."""
from copy import deepcopy
try:
    from publisher_access_policy import permission_hold_reason
except ModuleNotFoundError:
    from scripts.publisher_access_policy import permission_hold_reason


def paused_snapshot(url, previous=None):
    reason = permission_hold_reason(url)
    if reason:
        if previous and previous.get('collection_paused') is True and previous.get('permission_required') is True:
            return deepcopy(previous)
        return {'ok': False, 'url': url, 'text': '', 'links': [], 'rows': [],
                'html': '', 'payloads': [], 'permission_required': True,
                'collection_paused': True, 'error': reason}
    return None


def route_publisher_request(route):
    """Inspect every HTTP hop before dispatch, including browser redirects.

    Playwright routing alone does not guarantee interception of redirect hops.
    Fetch with automatic redirects disabled; follow only checked GET/HEAD hops.
    Non-idempotent redirects and excessive chains fail closed.
    """
    from urllib.parse import urljoin, urlsplit
    url = route.request.url
    method = route.request.method.upper()
    response = None
    try:
        for _ in range(11):
            if permission_hold_reason(url):
                route.abort('blockedbyclient')
                return
            if urlsplit(url).scheme not in ('http', 'https'):
                route.abort('blockedbyclient')
                return
            response = route.fetch(url=url, max_redirects=0)
            if 300 <= response.status < 400 and response.headers.get('location'):
                if method not in ('GET', 'HEAD'):
                    route.abort('blockedbyclient')
                    return
                next_url = urljoin(url, response.headers['location'])
                response.dispose()
                response = None
                url = next_url
                continue
            route.fulfill(response=response)
            return
        route.abort('blockedbyclient')
    except Exception:
        # A failed guard/fetch must never fall back to unguarded continue_().
        route.abort('failed')
    finally:
        if response is not None:
            response.dispose()


def install_browser_hold(page):
    page.context.route('**/*', route_publisher_request)


def retain_paused_tournaments(saved):
    rows = []
    for original in saved.get('tournaments') or []:
        reason = permission_hold_reason(original.get('source_url') or '')
        if not reason and str(original.get('tour_id') or '').startswith('itf-'):
            reason = permission_hold_reason('https://www.itftennis.com/')
        if not reason:
            continue
        row = deepcopy(original)
        row.update({'collection_paused': True, 'source_stale': True,
                    'permission_required': True, 'permission_hold_reason': reason,
                    'source_generated_at': original.get('source_generated_at') or saved.get('generated_at')})
        rows.append(row)
    return rows


def mark_permission_metadata(document, checked_at, previous=None):
    # A new run is not a new permission review. Preserve the original hold
    # records (including their dates) across every derived tennis output.
    holds = deepcopy((previous or {}).get('publisher_permission_holds') or [])
    for row in document.get('publisher_permission_holds') or []:
        if row not in holds:
            holds.append(deepcopy(row))
    reason = permission_hold_reason('https://www.itftennis.com/')
    if reason and not any(row.get('publisher') == 'ITF'
                          and row.get('collection_paused') is True
                          and row.get('permission_required') is True
                          and set(row.get('tour_ids') or []) >= {'itf-men', 'itf-women'}
                          for row in holds):
        holds.append({
            'publisher': 'ITF', 'tour_ids': ['itf-men', 'itf-women'],
            'permission_required': True, 'collection_paused': True,
            'source_stale': True, 'reason': reason, 'hold_checked_at': checked_at,
            'note': 'Saved evidence retained; no new ITF collection or permission verification.'})
    if holds:
        document['publisher_permission_holds'] = holds
    return document
