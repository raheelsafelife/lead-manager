import test from 'node:test';
import assert from 'node:assert/strict';
import initSqlJs from 'sql.js';
import { getLeadListSummary } from './leadListSummary.js';

test('authorization totals include all filtered pages and respect client scope', async () => {
  const SQL = await initSqlJs();
  const raw = new SQL.Database();
  const db = { get(sql, params) {
    const stmt = raw.prepare(sql);
    try { stmt.bind(params); stmt.step(); return stmt.getAsObject(); }
    finally { stmt.free(); }
  } };
  try {
    raw.run(`create table agencies (id integer primary key, name text);
      create table ccus (id integer primary key);
      create table leads (id integer primary key, agency_id integer, ccu_id integer,
        authorization_received integer, hours real, monthly_hours real, owner_id integer, deleted_at text);
      insert into agencies values (1, 'Payor A'), (2, 'Payor B');`);
    for (let id = 1; id <= 12; id++) raw.run('insert into leads values (?,1,null,1,1.25,5.5,1,null)', [id]);
    raw.run(`insert into leads values
      (13,2,null,1,20,80,2,null),
      (14,1,null,1,null,null,1,null),
      (15,1,null,1,100,400,1,'deleted'),
      (16,1,null,0,999,999,1,null);`);
    const where = 'where leads.authorization_received = 1 and leads.deleted_at is null and leads.owner_id = $owner';
    assert.deepEqual(await getLeadListSummary(db, where, { $owner: 1 }, true), {
      total: 13, authorizationHours: { weekly: 15, monthly: 66 }
    });
    assert.deepEqual(await getLeadListSummary(db, where, { $owner: 2 }, true), {
      total: 1, authorizationHours: { weekly: 20, monthly: 80 }
    });
    assert.deepEqual(await getLeadListSummary(db, where + ' and agencies.name = $payor', { $owner: 1, $payor: 'Payor B' }, true), {
      total: 0, authorizationHours: { weekly: 0, monthly: 0 }
    });
    assert.deepEqual(await getLeadListSummary(db, 'where leads.id = 14', {}, true), {
      total: 1, authorizationHours: { weekly: 0, monthly: 0 }
    });
    assert.deepEqual(await getLeadListSummary(db, 'where leads.id = 16', {}, true), {
      total: 1, authorizationHours: { weekly: 0, monthly: 0 }
    });
    assert.deepEqual(await getLeadListSummary(db, where, { $owner: 1 }), { total: 13 });
  } finally { raw.close(); }
});
