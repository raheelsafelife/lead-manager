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
run(['git', 'apply', '--check', str(release / 'active-default.patch')])
files = ['server/index.js', 'src/pages/LeadsPage.jsx', 'server/leadListSummary.js', 'server/leadListSummary.test.js']
for name in files:
    source = frontend / name
    if source.exists():
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
# Back up lead data before release. Credentials stay on the server.
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
    run(['git', 'apply', str(release / 'active-default.patch')]); changed = True
    shutil.copy2(release/'leadListSummary.js', frontend/'server/leadListSummary.js')
    shutil.copy2(release/'leadListSummary.test.js', frontend/'server/leadListSummary.test.js')
    run(['node', '--check', 'server/index.js'], frontend)
    run(['node', '--test', 'server/leadListSummary.test.js', 'server/authorization.test.js'], frontend)
    if not (frontend/'node_modules/leaflet/package.json').exists():
        run(['npm', 'install', '--no-save', '--package-lock=false', '--ignore-scripts', 'leaflet@1.9.4'], frontend)
    if (frontend/'dist').exists(): shutil.move(str(frontend/'dist'), str(old_dist))
    run(['npm', 'run', 'build'], frontend)
    # Preserve existing static resources that were deployed outside the source tree.
    if old_dist.exists():
        for source in old_dist.rglob('*'):
            target = frontend/'dist'/source.relative_to(old_dist)
            if source.is_file() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    run(['pm2', 'restart', 'lead-manager-react'], frontend)
    time.sleep(4)
    run(['curl', '--fail', '--silent', '--output', '/dev/null', 'http://127.0.0.1:3001/'])
    verify_js = """import dotenv from 'dotenv'; import pg from 'pg';
import assert from 'node:assert/strict'; import { defaultAuthorizationScope, getLeadListSummary } from './server/leadListSummary.js';
assert.equal(defaultAuthorizationScope({type:'authorization'}).active,'Active');
assert.equal(defaultAuthorizationScope({type:'authorization',active:'All'}).active,'All');
dotenv.config({path:'../.env'}); dotenv.config({path:'.env'});
if (process.env.DATABASE_URL?.startsWith('postgres')) {
 const pool=new pg.Pool({connectionString:process.env.DATABASE_URL,ssl:process.env.PGSSL==='false'?false:{rejectUnauthorized:false}});
 try {
  const db={get:async(sql)=> (await pool.query(sql)).rows[0]};
  const where="where leads.active_client = 1 and leads.authorization_received = 1 and leads.deleted_at is null and coalesce(leads.care_status,'') not in ('Hold','Terminated','Deceased')";
  const summary=await getLeadListSummary(db,where,{},true);
  const expected=(await pool.query('select count(*) as count, coalesce(sum(hours),0) as weekly, coalesce(sum(monthly_hours),0) as monthly from leads '+where)).rows[0];
  assert.equal(summary.total,Number(expected.count));
  assert.equal(summary.authorizationHours.weekly,Number(expected.weekly));
  assert.equal(summary.authorizationHours.monthly,Number(expected.monthly));
  console.log('Production active authorization totals verified against PostgreSQL');
 } finally { await pool.end(); }
}
"""
    subprocess.run(['node','--input-type=module','-e',verify_js],cwd=frontend,check=True)
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
print('Active authorization default deployed; backup:', backup)
