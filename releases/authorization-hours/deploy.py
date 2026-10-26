import os, pathlib, shutil, subprocess, sys, time
app = pathlib.Path(sys.argv[1]).resolve()
release = pathlib.Path(__file__).resolve().parent
frontend = app / 'rebuild frontend'
stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
backup = pathlib.Path.home() / 'authorization-deploy-backups' / stamp
backup.mkdir(parents=True, mode=0o700)
os.chmod(backup, 0o700)
def run(args, cwd=app):
    subprocess.run(args, cwd=cwd, check=True)
if shutil.disk_usage(app).free < 250 * 1024 * 1024:
    raise RuntimeError('At least 250 MB free space required')
run(['git', 'apply', '--check', str(release / 'authorization.patch')])
files = ['server/index.js', 'src/components/LeadCard.jsx', 'migrations/aws/postgres-schema.sql', 'src/utils/authorization.js', 'server/authorization.test.js']
for name in files:
    source = frontend / name
    if source.exists():
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
# Back up lead data before the additive schema change. Credentials stay on the server.
backup_js = '''import fs from 'node:fs';
import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({path:'../.env'}); dotenv.config({path:'.env'});
if (process.env.DATABASE_URL?.startsWith('postgres')) {
 const pool = new pg.Pool({connectionString:process.env.DATABASE_URL,ssl:process.env.PGSSL==='false'?false:{rejectUnauthorized:false}});
 try { const result=await pool.query('select * from leads'); fs.writeFileSync(process.env.AUTH_BACKUP+'/leads.json',JSON.stringify(result.rows),{mode:0o600}); console.log('Lead backup rows:',result.rowCount); } finally { await pool.end(); }
} else { fs.copyFileSync(process.env.LEAD_DB || '../backend/leads.db',process.env.AUTH_BACKUP+'/leads.db'); }
'''
subprocess.run(['node', '--input-type=module', '-e', backup_js], cwd=frontend, env={**os.environ,'AUTH_BACKUP':str(backup)}, check=True)
changed = False
old_dist = backup / 'dist'
try:
    run(['git', 'apply', str(release / 'authorization.patch')]); changed = True
    shutil.copy2(release/'authorization.js', frontend/'src/utils/authorization.js')
    shutil.copy2(release/'authorization.test.js', frontend/'server/authorization.test.js')
    run(['node', '--check', 'server/index.js'], frontend)
    run(['node', '--test', 'server/authorization.test.js'], frontend)
    if (frontend/'dist').exists(): shutil.move(str(frontend/'dist'), str(old_dist))
    run(['npm', 'run', 'build'], frontend)
    run(['pm2', 'restart', 'lead-manager-react'], frontend)
    time.sleep(4)
    run(['curl', '--fail', '--silent', '--output', '/dev/null', 'http://127.0.0.1:3001/'])
    run(['pm2', 'save'], frontend)
except Exception:
    if changed:
        for name in files:
            saved = backup / name
            target = frontend / name
            if saved.exists(): shutil.copy2(saved, target)
            elif target.exists(): target.unlink()
        if old_dist.exists():
            if (frontend/'dist').exists(): shutil.rmtree(frontend/'dist')
            shutil.move(str(old_dist), str(frontend/'dist'))
        subprocess.run(['pm2','restart','lead-manager-react'],cwd=frontend)
    raise
print('Authorization release deployed; backup:', backup)
