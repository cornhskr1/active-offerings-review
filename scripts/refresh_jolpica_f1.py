"""Daily no-auth F1 schedule refresh; writes only its isolated licensed dataset."""
import argparse
import json
from pathlib import Path
import os
import tempfile
from datetime import datetime, timezone
import urllib.request
import urllib.error
try:
    from jolpica_f1_schedule import collect_schedule, ENDPOINT, MAX_BYTES
except ImportError:
    from scripts.jolpica_f1_schedule import collect_schedule, ENDPOINT, MAX_BYTES


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, 'Redirect rejected', headers, None)


def provider_get(url, timeout=30, allow_redirects=False, max_bytes=MAX_BYTES, opener=None):
    if url != ENDPOINT or allow_redirects is not False or max_bytes != MAX_BYTES:
        raise ValueError('unapproved_provider_request')
    opener = opener or urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': 'ActiveOfferingsReview/1.0 (schedule-only)', 'Accept': 'application/json'})
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
            headers = {'Retry-After': response.headers.get('Retry-After')} if response.headers.get('Retry-After') is not None else {}
            if status != 200:
                return {'status_code': status, 'headers': headers, 'body_bytes': 0}
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return {'status_code': status, 'headers': headers, 'body_bytes': len(raw)}
            return {'status_code': status, 'headers': headers, 'body_bytes': len(raw), 'payload': json.loads(raw)}
    except urllib.error.HTTPError as error:
        result = {'status_code': error.code, 'headers': {}, 'body_bytes': 0}
        if error.headers and error.headers.get('Retry-After') is not None:
            result['headers']['Retry-After'] = error.headers['Retry-After']
        error.close()
        return result


def refresh(previous_path, output_path, now=None, get=provider_get):
    # Missing/corrupt previous state must not erase a persisted access hold.
    previous = json.loads(Path(previous_path).read_text())
    result = collect_schedule(previous, now or datetime.now(timezone.utc), get=get)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.jolpica-', dir=output.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        os.replace(tmp, output)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        result = refresh(args.previous, args.output)
        print('F1 schedule:', result['source_health']['status'], ';', len(result['events']), 'window events')
    except Exception:
        raise SystemExit('F1 refresh failed safely; previous data preserved. Review source state before retrying.') from None
