"""Apply the reviewed indexing-only change without restarting the application."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

DOMAIN = 'ccpleads.safelifehomehealth.com'
BASE_HASH = '05d366ad4146c6a083507746339e6718a44509348b54c197cb8a0538cec7de9d'
CONFIG = Path('/etc/nginx/sites-enabled/ccpleads').resolve()
SNIPPET = Path('/etc/nginx/snippets/lead-manager-search-privacy.conf')
INCLUDE = f'    include {SNIPPET};\n'
META = '<meta name="robots" content="noindex,nofollow,noarchive" />'
ROOT = Path.cwd()
DIST = ROOT / 'rebuild frontend/dist'


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def nginx_test():
    result = run('sudo', '-n', 'nginx', '-t')
    if 'conflicting server name' in result.stderr.lower():
        raise RuntimeError('Conflicting Nginx server names; refusing deployment')
    print(result.stderr.strip())


def write_atomic(path, content):
    descriptor, temporary = tempfile.mkstemp(prefix='.search-privacy-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as file:
            file.write(content)
        os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


nginx_test()
dump = run('sudo', '-n', 'nginx', '-T')
if 'conflicting server name' in dump.stderr.lower():
    raise RuntimeError('Conflicting server names')
# Require the exact two reviewed server_name directives across all loaded files.
matching = [line for line in dump.stdout.splitlines()
            if re.match(r'^\s*server_name\s', line) and DOMAIN in line]
if len(matching) != 2 or any(line.strip() != f'server_name {DOMAIN};' for line in matching):
    raise RuntimeError('Unexpected or shared domain configuration')
original = CONFIG.read_text()
base = original.replace(INCLUDE, '')
if hashlib.sha256(base.encode()).hexdigest() != BASE_HASH:
    raise RuntimeError('Nginx configuration changed since inspection; review required')
needle = f'    server_name {DOMAIN};\n'
if base.count(needle) != 2:
    raise RuntimeError('Expected two dedicated server blocks')
updated = base.replace(needle, needle + INCLUDE)
snippet = (ROOT / 'rebuild frontend/deploy/nginx/search-privacy.conf').read_text()
if SNIPPET.exists() and SNIPPET.read_text() != snippet:
    raise RuntimeError('Existing snippet differs; review required')
html_path = DIST / 'index.html'
html = html_path.read_text()
existing_meta = re.findall(r'<meta\b[^>]*\bname=["\'](?:robots|googlebot|bingbot)["\'][^>]*>', html, re.I)
if existing_meta and existing_meta != [META]:
    raise RuntimeError('Existing robots metadata requires review')
if '</head>' not in html:
    raise RuntimeError('Unexpected frontend HTML')
updated_html = html if existing_meta else html.replace('</head>', f'    {META}\n  </head>', 1)
robots_path = DIST / 'robots.txt'
robots = (ROOT / 'rebuild frontend/public/robots.txt').read_text()
assert robots == 'User-agent: *\nDisallow: /\n'
if robots_path.exists() and robots_path.read_text() != robots:
    raise RuntimeError('Existing robots.txt differs; review required')

# Back up only affected files, outside the publicly served dist directory.
backup = ROOT / '.search-privacy-backups' / str(time.time_ns())
backup.mkdir(parents=True, mode=0o700)
shutil.copy2(html_path, backup / 'index.html')
if robots_path.exists():
    shutil.copy2(robots_path, backup / 'robots.txt')
run('sudo', '-n', 'cp', '-p', str(CONFIG), str(backup / 'nginx.conf'))
had_snippet = SNIPPET.exists()
if had_snippet:
    run('sudo', '-n', 'cp', '-p', str(SNIPPET), str(backup / 'snippet.conf'))

try:
    with tempfile.TemporaryDirectory() as staging:
        staged = Path(staging)
        (staged / 'snippet').write_text(snippet)
        run('sudo', '-n', 'install', '-m', '644', str(staged / 'snippet'), str(SNIPPET))
        # Preserve the existing site's owner, permissions, symlink and all other directives.
        subprocess.run(['sudo', '-n', 'tee', str(CONFIG)], input=updated, text=True,
                       stdout=subprocess.DEVNULL, check=True)
    nginx_test()
    write_atomic(html_path, updated_html)
    write_atomic(robots_path, robots)
    # No reload is attempted unless the immediately preceding configuration test passes.
    nginx_test()
    run('sudo', '-n', 'systemctl', 'reload', 'nginx')
except Exception:
    run('sudo', '-n', 'cp', '-p', str(backup / 'nginx.conf'), str(CONFIG))
    if had_snippet:
        run('sudo', '-n', 'cp', '-p', str(backup / 'snippet.conf'), str(SNIPPET))
    else:
        run('sudo', '-n', 'rm', '-f', str(SNIPPET))
    write_atomic(html_path, (backup / 'index.html').read_text())
    if (backup / 'robots.txt').exists():
        write_atomic(robots_path, (backup / 'robots.txt').read_text())
    elif robots_path.exists():
        robots_path.unlink()
    nginx_test()
    run('sudo', '-n', 'systemctl', 'reload', 'nginx')
    raise
print('Search privacy deployed; application process and database untouched.')
print('Backups:', backup.name)
