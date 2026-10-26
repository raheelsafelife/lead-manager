import test from 'node:test';
import assert from 'node:assert/strict';
import { validateAuthorizationHours as validate, normalizeHours } from '../src/utils/authorization.js';
test('weekly and monthly hours accept independent non-negative values', () => {
  for (const data of [{}, { hours: 0, monthly_hours: 0 }, { hours: '12.5', monthly_hours: '20' }, { hours: 40 }, { monthly_hours: 160 }, { hours: 50, monthly_hours: 20 }]) assert.equal(validate(data), '');
  for (const data of [{ hours: -1 }, { monthly_hours: -1 }, { hours: 'abc' }, { monthly_hours: Infinity }, { hours: true }]) assert.ok(validate(data));
  assert.equal(normalizeHours(''), null);
  assert.equal(normalizeHours('0'), 0);
  assert.equal(normalizeHours('12.5'), 12.5);
});
