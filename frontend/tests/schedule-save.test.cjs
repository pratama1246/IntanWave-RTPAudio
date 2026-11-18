const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('frontend/src/App.jsx', 'utf8');
const start = source.indexOf('  const handleSaveSchedule = async');
const end = source.indexOf('\n  };', start) + 5;
const handler = source.slice(start, end);
async function check(ok, editingScheduleId = null) {
  let error = '', closed = false, saving = false, refreshed = false;
  const schedule = { name: 'Test', time_str: '08:00' };
  const requests = [];
  const run = new Function('isSavingSchedule', 'editingScheduleId', 'newSchedule', 'setIsSavingSchedule', 'setScheduleError', 'setShowAddSchedule', 'setEditingScheduleId', 'fetchData', 'fetch', '"use strict";\n' + handler + '; return handleSaveSchedule;')(
    false, editingScheduleId, schedule, value => { saving = value; }, value => { error = value; }, value => { closed = !value; }, () => {}, () => { refreshed = true; }, async (url, options) => {
      requests.push({ url, options });
      return { ok, json: async () => ({ detail: 'Periksa tujuan siaran' }) };
    }
  );
  await run({ preventDefault() {} });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, editingScheduleId ? `/api/schedules/${editingScheduleId}` : '/api/schedules');
  assert.equal(requests[0].options.method, editingScheduleId ? 'PUT' : 'POST');
  assert.deepEqual(JSON.parse(requests[0].options.body), schedule);
  assert.equal(closed, ok);
  assert.equal(refreshed, ok);
  assert.equal(saving, false);
  assert.equal(error, ok ? '' : 'Periksa tujuan siaran');
}
(async () => {
  await check(true);
  await check(false);
  await check(true, 7);
  await check(false, 7);
  console.log('Schedule save: create and unchanged edit succeed; server rejection preserves the form in strict mode.');
})().catch(error => { console.error(error); process.exitCode = 1; });
