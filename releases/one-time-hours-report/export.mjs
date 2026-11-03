import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({path:'../../.env',quiet:true});
dotenv.config({path:'../.env',quiet:true});
dotenv.config({path:'.env',quiet:true});
if (!process.env.DATABASE_URL?.startsWith('postgres')) throw new Error('Expected production PostgreSQL');
const pool=new pg.Pool({connectionString:process.env.DATABASE_URL,ssl:process.env.PGSSL==='false'?false:{rejectUnauthorized:false}});
const client=await pool.connect();
try {
 await client.query('BEGIN TRANSACTION READ ONLY');
 const result=await client.query(`select l.id as "Client ID", l.first_name as "First Name", l.last_name as "Last Name",
 l.phone as "Phone", l.email as "Email", l.street as "Street", l.city as "City", l.state as "State", l.zip_code as "ZIP",
 a.name as "Payor", l.payer_id as "Payer ID", c.name as "CCU", l.staff_name as "Assigned Staff",
 coalesce(nullif(l.care_status,''),'Active') as "Care Status", l.source as "Source",
 l.authorization_received_at as "Authorization Received", l.hours as "Weekly Hours", l.monthly_hours as "Monthly Hours"
 from leads l left join agencies a on a.id=l.agency_id left join ccus c on c.id=l.ccu_id
 where l.authorization_received=1 and l.deleted_at is null
 order by lower(l.last_name),lower(l.first_name),l.id`);
 await client.query('COMMIT');
 const escape=(v)=>'"'+String(v??'').replaceAll('"','""')+'"';
 const headers=result.fields.map(f=>f.name);
 process.stdout.write('\ufeff'+[headers,...result.rows.map(row=>headers.map(h=>row[h]))].map(row=>row.map(escape).join(',')).join('\r\n')+'\r\n');
} finally { client.release(); await pool.end(); }
