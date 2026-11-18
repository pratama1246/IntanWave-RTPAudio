const assert = require('node:assert/strict');
const fs = require('node:fs');
const source = fs.readFileSync('frontend/src/App.jsx', 'utf8');
const start = source.indexOf('  const handleSaveSchedule = async');
const end = source.indexOf('\n  };', start) + 5;
const handler = source.slice(start, end);
async function check(ok) {
  let error = '', closed = false, saving = false, refreshed = false;
  const run = new Function('isSavingSchedule', 'editingScheduleId', 'newSchedule', 'setIsSavingSchedule', 'setScheduleError', 'setShowAddSchedule', 'setEditingScheduleId', 'fetchData', 'fetch', handler + '; return handleSaveSchedule;')(
    false, null, { name: 'Test' }, value => { saving = value; }, value => { error = value; }, value => { closed = !value; }, () => {}, () => { refreshed = true; }, async () => ({ ok, json: async () => ({ detail: 'Periksa tujuan siaran' }) })
  );
  await run({ preventDefault() {} });
  assert.equal(closed, ok);
  assert.equal(refreshed, ok);
  assert.equal(saving, false);
  assert.equal(error, ok ? '' : 'Periksa tujuan siaran');
}
(async () => { await check(true); await check(false); console.log('Schedule save: success closes form; server rejection preserves form and shows error.'); })().catch(error => { console.error(error); process.exitCode = 1; });
