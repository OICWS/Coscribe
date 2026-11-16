// Exercises the actual panel and command queue with an in-process Electron transport double.
// The Windows desktop smoke additionally checks native WebContents popup behavior.
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const Module = require('node:module');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const scratch = mkdtempSync(join(tmpdir(), 'coscribe-browser-'));
const session = new EventEmitter();
Object.assign(session, { setPermissionRequestHandler() {}, setPermissionCheckHandler() {} });
let onEvaluate = () => ({});
const contents = [];
class Contents extends EventEmitter {
  constructor() { super(); contents.push(this); }
  navigationHistory = { canGoBack: () => false, canGoForward: () => false };
  url = 'about:blank';
  destroyed = false;
  getURL() { return this.url; }
  getTitle() { return this.url; }
  isLoading() { return false; }
  isDestroyed() { return this.destroyed; }
  async loadURL(url) {
    this.url = url;
    this.emit('did-start-navigation', { isMainFrame: true, isSameDocument: false, url });
    this.emit('did-navigate');
  }
  setWindowOpenHandler(fn) {
    this.open = ({ url }) => {
      const response = fn({ url });
      if (response.createWindow) {
        const guest = new Contents();
        const adopted = response.createWindow({ webContents: guest, webPreferences: {} });
        assert.equal(adopted, guest, "native popup must adopt Electron's guest WebContents");
        void adopted.loadURL(url);
      }
      return response;
    };
  }
  send() {}
  setBackgroundThrottling() {}
  async executeJavaScriptInIsolatedWorld() { return {}; }
  async executeJavaScript() { return this.empty !== false; }
  close() { this.destroyed = true; this.emit('destroyed'); }
}
const cdps = new WeakMap();
const cdpMock = {
  existingCdp: wc => cdps.get(wc),
  cdpFor(wc) {
    if (!cdps.has(wc)) cdps.set(wc, {
      threadId: '', main: {}, dialog: null, driving: false, downloads: [],
      async drive(threadId, dir) { this.threadId = threadId; this.downloadDir = dir; this.driving = true; },
      async fit() {}, async idle() {},
      async evaluateInPage(expression) { return { value: onEvaluate(wc, expression) }; },
    });
    return cdps.get(wc);
  },
};
const load = Module._load;
Module._load = function(name, ...rest) {
  if (name === 'electron') return {
    BrowserWindow: { getAllWindows: () => [] },
    webContents: { getAllWebContents: () => contents },
    app: { getPath: () => scratch }, session: { fromPartition: () => session },
    WebContentsView: class { constructor(options) { this.webContents = options.webContents ?? new Contents(); } setBorderRadius() {} },
  };
  if (name === './browserCdp') return cdpMock;
  if (name === './browserPermissions') return {
    checkNetworkLanding() {}, checkNetworkSites() {}, isAllowed: () => true,
    browserSettings: () => ({}), normalizeSite: x => x,
  };
  return load.call(this, name, ...rest);
};
const panel = require('../dist/main/browserPanel');
const { startBrowserAgent } = require('../dist/main/browserAgent');
const steps = require('../dist/main/browserAgentSteps');
Module._load = load;
let stream;
const replies = new Map();
global.fetch = async (url, options) => {
  if (url.endsWith('/result')) {
    const reply = JSON.parse(options.body);
    replies.get(reply.id)?.(reply);
    replies.delete(reply.id);
    return { ok: true };
  }
  return { ok: true, body: new ReadableStream({ start(c) { stream = c; } }) };
};
let nextId = 0;
function emit(command) { stream.enqueue(Buffer.from(`data: ${JSON.stringify(command)}\n\n`)); }
function request(action, args = {}, thread_id = 'a') {
  const id = String(++nextId);
  const result = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`No reply to ${action}`)), 5000);
    replies.set(id, reply => { clearTimeout(timer); resolve(reply); });
  });
  emit({ id, thread_id, action, args: { ...args, download_dir: scratch } });
  return { id, result };
}
async function call(action, args, thread) {
  const reply = await request(action, args, thread).result;
  assert.equal(reply.ok, true, reply.error);
  return reply.result;
}
function download(wc, name, state = 'completed') {
  const item = new EventEmitter();
  Object.assign(item, { getFilename: () => name, setSavePath(path) { this.path = path; } });
  session.emit('will-download', {}, item, wc);
  item.emit('done', {}, state);
  assert.ok(item.path, 'download must bypass the system save dialog');
}
(async () => {
  startBrowserAgent(1, 'test', () => undefined);
  await new Promise(resolve => setImmediate(resolve));
  emit({ action: 'activity', thread_id: 'a', args: { active: true } });
  await call('navigate', { url: 'https://first.example/' });
  const source = panel.activeTab('a');
  await call('navigate', { url: 'https://second.example/' });
  assert.equal(panel.allTabs('a').length, 1, 'navigation reuses the current page');
  assert.equal(panel.activeTab('a').id, source.id);

  onEvaluate = wc => { wc.open({ url: 'https://login.example/' }); return 'opened'; };
  const opened = await call('evaluate', { expression: 'open' });
  const popup = panel.allTabs('a').find(t => t.id !== source.id);
  assert.equal(panel.activeTab('a').id, source.id, 'AI popup must not steal its source');
  assert.equal(opened.tabs.find(t => t.id === popup.id).opener_id, source.id);
  await call('tabs', { op: 'select', tab_id: popup.id });
  assert.equal(panel.activeTab('a').id, popup.id);

  // The wait is on the popup, but the download belongs to the source tab.
  download(source.view.webContents, 'report.xlsx');
  cdpMock.cdpFor(popup.view.webContents).drive = () => { throw new Error('renderer unavailable'); };
  const finished = await call('wait_for', { download: true, timeout: 1 });
  assert.equal(finished.downloads[0].name, 'report.xlsx');
  assert.equal((await call('tabs', { op: 'list' })).tabs.length, 2, 'content popups are retained');
  await call('tabs', { op: 'close', tab_id: popup.id });
  assert.equal(panel.activeTab('a').id, source.id, 'closing a popup restores its source');

  source.view.webContents.open({ url: 'about:blank' });
  const blank = panel.allTabs('a').find(t => t.openerId === source.id);
  panel.selectTab(blank.id);
  download(blank.view.webContents, 'empty-popup.xlsx');
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(panel.allTabs('a').length, 1, 'completed untouched empty popup is closed');
  const retained = await call('wait_for', { download: true, timeout: 1 });
  assert.equal(retained.downloads[0].name, 'empty-popup.xlsx', 'closing popup cannot lose its download');

  source.view.webContents.open({ url: 'about:blank' });
  const written = panel.allTabs('a').find(t => t.openerId === source.id);
  assert.equal(written.blank, false, 'native about:blank popups can contain actionable content');
  written.view.webContents.empty = false;
  download(written.view.webContents, 'form-report.xlsx');
  await new Promise(resolve => setImmediate(resolve));
  assert.ok(panel.allTabs('a').includes(written), 'never close a nonempty about:blank form');
  await call('wait_for', { download: true, timeout: 1 });
  panel.closeTab(written.id);

  const emptyOther = await request('wait_for', { download: true, timeout: 0.01 }, 'empty').result;
  assert.match(emptyOther.error, /No download started/);
  assert.equal(panel.allTabs('empty').length, 0);

  await call('navigate', { url: 'https://other.example/' }, 'b');
  const other = await request('wait_for', { download: true, timeout: 0.01 }, 'b').result;
  assert.equal(other.ok, false, 'downloads must not leak across conversations');

  source.view.webContents.open({ url: 'https://late.example/' });
  onEvaluate = () => 'unchanged';
  const late = await call('evaluate', { expression: 'read' });
  assert.ok(late.tabs.some(t => t.url === 'https://late.example/'), 'report popups opened between commands');
  const latePopup = panel.allTabs('a').find(t => t.openerId === source.id);
  latePopup.view.webContents.close();
  assert.ok(!panel.allTabs('a').includes(latePopup), 'site-closed pages leave no stale tabs');
  while (panel.allTabs('a').length < panel.MAX_TABS) panel.createTab(undefined, 'a');
  const url = source.view.webContents.getURL();
  assert.equal(source.view.webContents.open({ url: 'https://overflow.example/' }).action, 'deny');
  assert.equal(source.view.webContents.getURL(), url, 'popup overflow cannot overwrite its source');
  assert.match((await call('evaluate', { expression: 'read' })).note, /all tabs/);

  download(source.view.webContents, 'broken.xlsx', 'interrupted');
  const interrupted = await request('wait_for', { download: true, timeout: 1 }).result;
  assert.equal(interrupted.ok, false);
  assert.match(interrupted.error, /broken.xlsx: interrupted/);

  const pending = request('wait_for', { download: true, timeout: 60 });
  await new Promise(resolve => setImmediate(resolve));
  emit({ action: 'cancel_request', thread_id: 'a', args: { request_id: pending.id } });
  assert.equal((await pending.result).ok, false);
  await call('tabs', { op: 'list' });
  await assert.rejects(steps.browserOperation(new Promise(() => {}), 1), /stopped responding/);
  const step = { threadId: 'a', requestId: 'cancel', stop: false };
  const cancelled = steps.stepContext.run(step, () => steps.browserOperation(new Promise(() => {})));
  step.stop = true;
  await assert.rejects(cancelled, /Stopped/);
  for (const thread of ['a', 'b']) steps.cancelFrameOff(thread);
  console.log('Browser regressions passed: reuse, popup feedback/select/close, download ownership/cleanup/isolation, cancellation and protocol timeout.');
})().then(() => { rmSync(scratch, { recursive: true, force: true }); process.exit(0); }, error => {
  console.error(error); rmSync(scratch, { recursive: true, force: true }); process.exit(1);
});
