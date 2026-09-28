"""Read-only production inspection. Never print environment or secret values."""
import hashlib
import pathlib
import re
import subprocess

result = subprocess.run(['sudo', '-n', 'nginx', '-T'], capture_output=True, text=True)
print('nginx configuration test exit:', result.returncode)
print(result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
for part in result.stdout.split('# configuration file ')[1:]:
    name, _, content = part.partition(':\n')
    for header in re.findall(r'^\s*add_header\s+(\S+)', content, re.M):
        print('HEADER_DIRECTIVE:', name, header)
    if 'ccpleads.safelifehomehealth.com' not in content:
        continue
    print('CONFIG:', name)
    print('SHA256:', hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest())
    for line in content.splitlines():
        if re.match(r'^\s*(server\s*\{|\}|listen\s|server_name\s|location\s|proxy_pass\s|root\s|try_files\s|include\s|return\s|proxy_hide_header\s)', line) or re.match(r'^\s*add_header\s+X-Robots-Tag\b', line):
            print(line)
        elif re.match(r'^\s*add_header\s', line):
            print('  OTHER add_header directive:', line.strip().split()[1])
print('PRODUCTION_COMMIT:', subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip())
print('TRACKED_CHANGES:')
print(subprocess.check_output(['git','diff','--name-only','HEAD'], text=True))
print('DIST_EXISTS:', pathlib.Path('rebuild frontend/dist/index.html').is_file())
