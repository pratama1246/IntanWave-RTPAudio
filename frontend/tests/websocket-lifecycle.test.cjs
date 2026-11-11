const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Execute the actual effect with inert socket/timer adapters, without React or LAN.
const app = fs.readFileSync(path.join(__dirname, '../src/App.jsx'), 'utf8');
const start = app.indexOf('useEffect(() => {', app.indexOf('// WebSocket Live Telemetry'));
const end = app.indexOf('}, []);', start) + '}, []);'.length;
const effect = app.slice(start, end);

function mount() {
  const sockets = [], timers = new Map(), states = [];
  let cleanup, nextTimer = 0;
  class Socket {
    constructor() { sockets.push(this); }
    close() { this.onclose?.({ code: 1000 }); }
  }
  vm.runInNewContext(effect, {
    useEffect: callback => { cleanup = callback(); },
    window: { location: { protocol: 'http:', host: 'localhost:7080' } },
    WebSocket: Socket,
    setTimeout: callback => { const id = ++nextTimer; timers.set(id, callback); return id; },
    clearTimeout: id => timers.delete(id),
    setWsConnected: value => states.push(value),
    fetchData() {},
  });
  return { sockets, timers, states, cleanup };
}

test('cleanup close cannot create an orphan reconnect, including StrictMode remount', () => {
  const first = mount();
  first.cleanup();
  assert.equal(first.timers.size, 0);
  assert.deepEqual(first.states, []);
  const second = mount();
  assert.equal(second.sockets.length, 1);
  first.sockets[0].onopen();
  assert.deepEqual(first.states, []);
  second.cleanup();
});

test('cleanup cancels a reconnect queued by network close', () => {
  const instance = mount();
  instance.sockets[0].onclose({ code: 1006 });
  assert.equal(instance.timers.size, 1);
  const queued = [...instance.timers.values()][0];
  instance.cleanup();
  assert.equal(instance.timers.size, 0);
  queued(); // Even an already-dispatched callback must be inert after disposal.
  assert.equal(instance.sockets.length, 1);
});

test('policy close stops automatic retries until the view remounts', () => {
  const instance = mount();
  instance.sockets[0].onclose({ code: 1008 });
  assert.equal(instance.timers.size, 0);
  assert.deepEqual(instance.states, [false]);
  instance.cleanup();
});
