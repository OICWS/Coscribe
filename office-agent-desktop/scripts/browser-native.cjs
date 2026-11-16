// Real WebContents popups must run without Playwright's automatic debugger attachment.
const assert = require('node:assert/strict');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const electron = require('electron');
if (!process.versions.electron) {
  const scratch = mkdtempSync(join(tmpdir(), 'coscribe-native-'));
  try {
    const result = require('node:child_process').spawnSync(electron,
      [...(process.platform === 'linux' ? ['--no-sandbox', '--disable-gpu'] : []), __filename],
      { stdio: 'inherit', timeout: 60000, env: { ...process.env, COSCRIBE_NATIVE_DATA: scratch } });
    if (result.error) console.error(result.error.message);
    process.exitCode = result.status === 0 ? 0 : 1;
  } finally { rmSync(scratch, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }); }
} else {
  const { app, BrowserWindow } = electron;
  app.setPath('userData', process.env.COSCRIBE_NATIVE_DATA);
  const timeout = setTimeout(() => { console.error('Native popup test timed out'); app.exit(1); }, 50000);
  app.whenReady().then(async () => {
    const panel = require('../dist/main/browserPanel');
    const { cdpFor } = require('../dist/main/browserCdp');
    const window = new BrowserWindow({ show: false, webPreferences: { nodeIntegration: true, contextIsolation: false } });
    panel.registerBrowserPanelHandlers(window);
    await window.loadURL('data:text/html,<title>Host</title>');
    const invoke = (channel, ...args) => window.webContents.executeJavaScript(`require('electron').ipcRenderer.invoke(${JSON.stringify(channel)}, ...${JSON.stringify(args)})`);
    const group = 'browser-smoke';
    const source = panel.createTab(undefined, group);
    panel.selectTab(source.id);
    await source.view.webContents.loadURL('data:text/html,<title>Source</title><p>Source page</p>');
    cdpFor(source.view.webContents).driving = true;
    const handle = await source.view.webContents.executeJavaScript(
      "(() => { const p = window.open('about:blank'); if (p) p.document.body.textContent = 'Popup form'; return Boolean(p); })()", true);
    assert.ok(handle, 'window.open must retain its WindowProxy');
    const popup = panel.allTabs(group).find(t => t.id !== source.id);
    assert.ok(popup && !popup.blank && popup.openerId === source.id, 'popup must retain its source');
    const preferences = popup.view.webContents.getLastWebPreferences();
    assert.equal(preferences.nodeIntegration, false);
    assert.equal(preferences.contextIsolation, true);
    assert.equal(preferences.sandbox, true);
    assert.equal(popup.view.webContents.getBackgroundThrottling(), false);
    const zoom = popup.view.webContents.getZoomFactor();
    await popup.view.webContents.executeJavaScript("window.dispatchEvent(new WheelEvent('wheel', { ctrlKey: true, deltaY: -100 }))");
    for (let n = 0; n < 250 && popup.view.webContents.getZoomFactor() === zoom; n++) {
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    assert.ok(popup.view.webContents.getZoomFactor() > zoom, 'popup must retain the panel preload zoom handler');
    assert.equal(await popup.view.webContents.executeJavaScript('document.body.textContent'), 'Popup form');
    assert.equal(panel.activeTab(group).id, source.id, 'popup must not steal the AI page');
    const neighbour = panel.createTab(undefined, group);
    await neighbour.view.webContents.loadURL('about:blank');
    panel.selectTab(popup.id);
    panel.closeTab(popup.id);
    assert.equal(panel.activeTab(group).id, source.id, 'closing must restore the source, not a neighbour');
    panel.closeTab(neighbour.id);
    // Electron has already cleared view.webContents when a page that closed itself reports it.
    const uncaught = [];
    const onUncaught = error => uncaught.push(error);
    process.on('uncaughtException', onUncaught);
    await source.view.webContents.executeJavaScript("void window.open('about:blank')", true);
    const selfClosing = panel.allTabs(group).find(t => t.openerId === source.id);
    assert.ok(selfClosing, 'the second popup must open as a tab');
    void selfClosing.view.webContents.executeJavaScript('window.close()').catch(() => undefined);
    for (let n = 0; n < 250 && !uncaught.length && panel.allTabs(group).includes(selfClosing); n++) {
      await new Promise(resolve => setTimeout(resolve, 20));
    }
    process.off('uncaughtException', onUncaught);
    assert.deepEqual(uncaught.map(String), [], 'a page closing itself must not throw in the main process');
    assert.ok(!panel.allTabs(group).includes(selfClosing), 'a page that closed itself leaves no tab');
    assert.equal(panel.activeTab(group).id, source.id);
    panel.viewGroup(group);
    const rect = { x: 10, y: 50, width: 700, height: 400 };
    await invoke(panel.BROWSER_PANEL_OPEN_CHANNEL, rect);
    let boundsCalls = 0;
    const originalBounds = source.view.setBounds.bind(source.view);
    source.view.setBounds = next => { boundsCalls++; originalBounds(next); };
    await invoke(panel.BROWSER_PANEL_REPOSITION_CHANNEL, rect);
    assert.equal(boundsCalls, 0, 'identical rectangles cannot trigger another native layout');
    await invoke(panel.BROWSER_PANEL_REPOSITION_CHANNEL, { ...rect, width: 710 });
    assert.equal(boundsCalls, 2, 'changed bounds retain the Electron double-set workaround');
    await invoke(panel.BROWSER_PANEL_SET_VIEW_HIDDEN_CHANNEL, true);
    await source.view.webContents.loadURL('data:text/html,<p>Navigation behind settings</p>');
    assert.ok(source.view.getBounds().x < 0, 'navigation must keep the native page behind the foreground overlay');
    await invoke(panel.BROWSER_PANEL_SET_VIEW_HIDDEN_CHANNEL, false);
    assert.equal(source.view.getBounds().x, rect.x);
    const background = panel.createTab(undefined, group);
    await background.view.webContents.loadURL('data:text/html,<input id="field">');
    assert.ok(window.contentView.children.includes(background.view), 'independent pages need an attached native viewport');
    assert.ok(background.view.getBounds().x < 0);
    const cdp = cdpFor(background.view.webContents);
    await cdp.drive(group, undefined, true, { width: 710, height: 400 });
    await background.view.webContents.executeJavaScript('document.querySelector("input").focus()');
    await cdp.input('Input.insertText', { text: 'Background form input' });
    assert.equal(await background.view.webContents.executeJavaScript('document.querySelector("input").value'), 'Background form input');
    let metrics = 0;
    const send = background.view.webContents.debugger.sendCommand.bind(background.view.webContents.debugger);
    background.view.webContents.debugger.sendCommand = (method, ...args) => {
      if (method.startsWith('Emulation.')) metrics++;
      return send(method, ...args);
    };
    await Promise.all([cdp.fit(true, { width: 710, height: 400 }), cdp.fit(true, { width: 710, height: 400 })]);
    assert.equal(metrics, 0, 'unchanged viewport metrics must not be resent');
    assert.equal(panel.activeTab(group).id, source.id);
    let stream;
    const results = new Map();
    global.fetch = async (url, options) => {
      if (url.endsWith('/result')) {
        const reply = JSON.parse(options.body);
        results.get(reply.id)(reply); results.delete(reply.id);
        return { ok: true };
      }
      return { ok: true, body: new ReadableStream({ start(controller) { stream = controller; } }) };
    };
    require('../dist/main/browserAgent').startBrowserAgent(1, 'native-test', () => window);
    await new Promise(resolve => setImmediate(resolve));
    let requestId = 0;
    const command = (action, args) => new Promise(resolve => {
      const id = `native-${++requestId}`;
      results.set(id, resolve);
      stream.enqueue(Buffer.from(`data: ${JSON.stringify({ id, thread_id: group, action, args })}\n\n`));
    });
    await background.view.webContents.loadURL('data:text/html,<label>Company Code<input id="company"></label><label>Posting Date<input id="date"></label><script>window.inputs=0;document.addEventListener("input",()=>window.inputs++)</script>');
    const filled = await command('fill_form', { tab_id: background.id, fields: [{ ref: 'textbox \"Company Code\"', text: '1000' }, { ref: 'textbox \"Posting Date\"', text: '2026-11-16' }] });
    assert.equal(filled.ok, true, filled.error);
    assert.deepEqual(await background.view.webContents.executeJavaScript('[company.value,date.value,window.inputs]'), ['1000','2026-11-16',2]);
    await background.view.webContents.loadURL('data:text/html,' + encodeURIComponent(
      '<label>Plant<select id="plant" aria-label="Plant"><option>Berlin</option><option value="HH">Hamburg</option></select></label>' +
      '<label><input type="checkbox" id="urgent">Urgent</label><label><input type="radio" name="m" id="air">Air</label>' +
      '<label>Due<input type="date" id="due"></label><label>Code<input id="code" oninput="this.value=this.value.toUpperCase()"></label>' +
      '<button onclick="setTimeout(()=>document.body.append(\'Posted\'),300)">Post</button>'));
    const kinds = await command('fill_form', { tab_id: background.id, timeout: 5, fields: [
      { ref: 'combobox "Plant"', text: 'hamburg' }, { ref: 'checkbox "Urgent"', text: 'checked' },
      { ref: 'radio "Air"', text: 'yes' }, { ref: 'textbox "Due"', text: '2026-12-01' }, { ref: 'textbox "Code"', text: 'ab1' }] });
    assert.equal(kinds.ok, true, kinds.error);
    assert.deepEqual(await background.view.webContents.executeJavaScript('[plant.value,urgent.checked,air.checked,due.value,code.value]'),
      ['HH', true, true, '2026-12-01', 'AB1'], 'every field kind fills in one call');
    assert.deepEqual(kinds.result.filled.filter(f => f.changed).map(f => f.value), ['AB1'], 'the read-back names what the page changed');
    const unclear = await command('fill_form', { tab_id: background.id, fields: [{ ref: 'checkbox "Urgent"', text: 'maybe' }] });
    assert.match(unclear.error, /checked" or "unchecked/);
    const ran = await command('steps', { tab_id: background.id, steps: [
      { fill: [{ ref: 'checkbox "Urgent"', text: 'unchecked' }] }, { click: 'button "Post"' }, { wait_for: 'Posted' }] });
    assert.equal(ran.ok, true, ran.error);
    assert.equal(await background.view.webContents.executeJavaScript('urgent.checked'), false);
    const stopped = await command('steps', { tab_id: background.id, timeout: 1, steps: [{ click: 'button "Post"' }, { click: 'button "Missing"' }] });
    assert.match(stopped.error, /Step 2 of 2 \(click\) failed: .* Done before it: click button "Post"/);
    const either = await command('wait_for', { tab_id: background.id, any_of: ['Rejected', 'Posted'], timeout: 2 });
    assert.equal(either.result.found_text, 'Posted');
    await invoke(panel.BROWSER_PANEL_SET_VIEW_HIDDEN_CHANNEL, true);
    const duringOverlay = await command('evaluate', { tab_id: source.id, expression: 'document.title' });
    assert.equal(duringOverlay.ok, true, duringOverlay.error);
    assert.ok(source.view.getBounds().x < 0, 'automation must not unhide the native view over settings');
    await invoke(panel.BROWSER_PANEL_SET_VIEW_HIDDEN_CHANNEL, false);
    assert.equal(panel.activeTab(group).id, source.id);
    await invoke('browser-panel:take-over', background.id, true);
    const denied = await command('evaluate', { tab_id: background.id, expression: 'document.title' });
    assert.equal(denied.ok, false);
    assert.match(denied.error, /taken over/);
    await invoke('browser-panel:take-over', background.id, false);
    assert.equal((await command('evaluate', { tab_id: background.id, expression: 'document.title' })).ok, true);
    const dropped = join(process.env.COSCRIBE_NATIVE_DATA, 'invoice.pdf');
    require('node:fs').writeFileSync(dropped, 'pdf');
    await background.view.webContents.loadURL('data:text/html,' + encodeURIComponent(
      '<button id="item" draggable="true" ondragstart="event.dataTransfer.setData(\'text/plain\',\'row-7\')">Item</button>' +
      '<div role="button" aria-label="Zone" style="width:200px;height:60px" ondragover="event.preventDefault()" ondrop="event.preventDefault();window.dropped=event.dataTransfer.getData(\'text/plain\')">Zone</div>' +
      '<div role="button" aria-label="Files" style="width:200px;height:60px" ondragover="event.preventDefault()" ondrop="event.preventDefault();window.files=[...event.dataTransfer.files].map(f=>f.name)">Files</div>' +
      '<input type="range" aria-label="Level" id="level" min="0" max="100" value="0" style="width:200px">' +
      '<div role="note" aria-label="Note"><b>Bold</b> words</div>' +
      '<div contenteditable="true" role="textbox" aria-label="Editor" id="editor"></div><input aria-label="Plain" id="plain">'));
    const html5 = await command('drag', { tab_id: background.id, ref: 'button "Item"', target: 'button "Zone"' });
    assert.equal(html5.ok, true, html5.error);
    assert.equal(html5.result.how, 'html5');
    assert.equal(await background.view.webContents.executeJavaScript('window.dropped'), 'row-7', 'an HTML5 drag carries its data to the drop target');
    const slid = await command('drag', { tab_id: background.id, ref: 'slider "Level"', by_x: 80 });
    assert.equal(slid.ok, true, slid.error);
    assert.ok(Number(await background.view.webContents.executeJavaScript('level.value')) > 20, 'a mouse drag moves a slider');
    const filesDropped = await command('upload', { tab_id: background.id, ref: 'button "Files"', paths: [dropped], drop: true });
    assert.equal(filesDropped.ok, true, filesDropped.error);
    assert.deepEqual(await background.view.webContents.executeJavaScript('window.files'), ['invoice.pdf']);
    assert.equal((await command('paste', { tab_id: background.id, ref: 'textbox "Plain"' })).ok, false, 'nothing to paste before a copy');
    await background.view.webContents.executeJavaScript('getSelection().selectAllChildren(document.querySelector("[role=note]"))');
    const copied = await command('copy', { tab_id: background.id });
    assert.equal(copied.result.preview, 'Bold words');
    const rich = await command('paste', { tab_id: background.id, ref: 'textbox "Editor"' });
    assert.equal(rich.result.formatted, true, rich.error);
    assert.match(await background.view.webContents.executeJavaScript('editor.innerHTML'), /<b>Bold<\/b>/, 'a rich editor keeps the formatting');
    await command('paste', { tab_id: background.id, ref: 'textbox "Plain"' });
    assert.equal(await background.view.webContents.executeJavaScript('plain.value'), 'Bold words');
    assert.notEqual(require('electron').clipboard.readText(), 'Bold words', "the person's clipboard is left alone");
    panel.closeTab(background.id);
    const permissions = require('../dist/main/browserPermissions');
    permissions.registerBrowserPermissionHandlers(window);
    const prompts = [];
    const originalSend = window.webContents.send.bind(window.webContents);
    window.webContents.send = (channel, data) => {
      if (channel === permissions.BROWSER_PERMISSION_EVENT) prompts.push(data);
      originalSend(channel, data);
    };
    const firstPermission = permissions.requestPermission('https://first.example', group, window);
    const secondPermission = permissions.requestPermission('https://second.example', group, window);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(prompts.length, 1, 'parallel operations cannot overwrite the foreground permission prompt');
    await invoke('browser-panel:permission-answer', prompts[0].requestId, 'once');
    await firstPermission;
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(prompts.length, 2);
    await invoke('browser-panel:permission-answer', prompts[1].requestId, 'once');
    await secondPermission;
    panel.destroyBrowserPanel();
    clearTimeout(timeout);
    console.log('Native browser checks passed: popups, bounds, overlays, background input, form events, every field kind, page steps, waiting for one of several texts, drag and drop, file drop, the AI clipboard, takeover and permission queue.');
    app.exit(0);
  }).catch(error => { console.error(error); app.exit(1); });
}
