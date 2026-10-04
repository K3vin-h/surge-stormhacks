const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');

const source = readFileSync(require.resolve('../common.js'), 'utf8');

function context(storage) {
  const sandbox = { localStorage: storage, crypto: webcrypto, URL,
    document: { currentScript: { src: 'http://localhost/common.js' }, querySelector() { return {}; } },
    location: { href: 'http://localhost/victim.html' } };
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  return sandbox;
}

test('device identity stays stable when reading storage is blocked', () => {
  const sandbox = context({ getItem() { throw new Error('Storage blocked'); } });
  const first = sandbox.deviceId();
  assert.ok(first);
  assert.equal(sandbox.deviceId(), first);
});

test('device identity stays stable when writing storage fails', () => {
  const sandbox = context({ getItem() { return null; }, setItem() { throw new Error('Quota exceeded'); } });
  const first = sandbox.deviceId();
  assert.ok(first);
  assert.equal(sandbox.deviceId(), first);
});

test('persisted device identity is reused across page loads', () => {
  const values = new Map();
  const storage = { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) };
  const first = context(storage).deviceId();
  assert.equal(context(storage).deviceId(), first);
});
