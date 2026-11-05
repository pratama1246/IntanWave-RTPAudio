const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('frontend/src/App.jsx', 'utf8');
const handler = source.split('  const handleToggleSchedule = async (id) => {')[1].split('\n  // Add Schedule')[0];
async function check(failure) {
  let schedules = [{ id: 1, enabled: true }];
  const pending = { current: new Map() };
  let ids = [], requests = 0, alerts = 0, resolve;
  const response = new Promise(done => { resolve = done; });
  const toggle = new Function('schedules', 'pendingScheduleToggles', 'setTogglingScheduleIds', 'setSchedules', 'fetch', 'alert',
    'return async (id) => {' + handler)(schedules, pending, f => { ids = f(ids); }, f => { schedules = f(schedules); }, () => { requests++; return response; }, () => { alerts++; });
  const saving = toggle(1);
  assert.equal(schedules[0].enabled, false, 'toggle should update before server response');
  await toggle(1);
  assert.equal(requests, 1, 'rapid duplicate click should not send a second toggle');
  resolve({ ok: !failure, json: async () => ({ enabled: false }) });
  await saving;
  assert.equal(schedules[0].enabled, failure ? true : false);
  assert.equal(alerts, failure ? 1 : 0);
  assert.equal(ids.length, 0);
  assert.equal(pending.current.size, 0);
}
(async () => { await check(false); await check(true); console.log('Schedule toggle: immediate response, duplicate guard, save and rollback passed'); })().catch(err => { console.error(err); process.exitCode = 1; });
