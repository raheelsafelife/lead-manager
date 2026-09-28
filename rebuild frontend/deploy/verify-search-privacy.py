"""Read-only checks; never print response bodies or customer data."""
from html.parser import HTMLParser
import re
import subprocess

BASE = 'https://ccpleads.safelifehomehealth.com'
EXPECTED = 'noindex, nofollow, noarchive'


class RobotsMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.directives = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == 'meta' and attrs.get('name', '').lower() in ('robots', 'googlebot', 'bingbot'):
            self.directives.append(attrs.get('content', ''))


def check(path, status, method='GET', html=False, base=BASE):
    args = ['curl', '--silent', '--show-error', '--max-time', '25', '--dump-header', '-']
    if method == 'HEAD':
        args += ['--head']
    elif method == 'OPTIONS':
        args += ['--request', 'OPTIONS', '--header', f'Origin: {BASE}',
                 '--header', 'Access-Control-Request-Method: GET',
                 '--header', 'Access-Control-Request-Headers: authorization']
    response = subprocess.run(args + [base + path], capture_output=True, text=True, check=True).stdout
    headers, _, body = response.partition('\n\n')
    assert int(headers.splitlines()[0].split()[1]) == status, f'{method} {path}: unexpected status'
    tags = re.findall(r'^x-robots-tag:\s*(.+)$', headers, re.I | re.M)
    assert tags == [EXPECTED], f'{method} {path}: missing, duplicate or conflicting header'
    if html:
        meta = RobotsMeta()
        meta.feed(body)
        assert meta.directives == ['noindex,nofollow,noarchive'], f'{path}: incorrect HTML robots metadata'
    if path == '/robots.txt':
        assert body == 'User-agent: *\nDisallow: /\n', 'Incorrect robots rules'
        assert re.search(r'^content-type:\s*text/plain\b', headers, re.I | re.M), 'Incorrect robots MIME type'
    if method == 'OPTIONS':
        assert f'access-control-allow-origin: {BASE}' in headers.lower(), 'CORS origin changed'
        assert 'access-control-allow-credentials: true' in headers.lower(), 'CORS credentials changed'
    print(f'PASS {method} {base}{path}: {status}, X-Robots-Tag' + (', HTML noindex' if html else ''))
    return body


check('/', 200, method='HEAD')
root = ''
for route in ['/', '/login', '/dashboard', '/view-leads', '/reports']:
    body = check(route, 200, html=True)
    if route == '/':
        root = body
check('/robots.txt', 200)
for route in ['/api/auth/me', '/api/leads', '/api/dashboard', '/api/lookups',
              '/api/reports/export', '/api/attachments/0/download',
              '/uploads/nonexistent-privacy-check', '/api/external-lead/staff']:
    check(route, 401)
check('/api/nonexistent-privacy-check', 404)
check('/api/leads', 204, method='OPTIONS')
asset = re.search(r'["\'](/assets/[^"\']+)', root)
assert asset, 'No frontend asset found'
check(asset.group(1), 200)
check('/', 301, base='http://ccpleads.safelifehomehealth.com')
