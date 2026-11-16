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
      { stdio: 'inherit', timeout: 30000, env: { ...process.env, COSCRIBE_NATIVE_DATA: scratch } });
    if (result.error) console.error(result.error.message);
    process.exitCode = result.status === 0 ? 0 : 1;
  } finally { rmSync(scratch, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 }); }
} else {
  const { app, BrowserWindow } = electron;
  app.setPath('userData', process.env.COSCRIBE_NATIVE_DATA);
  const timeout = setTimeout(() => { console.error('Native popup test timed out'); app.exit(1); }, 25000);
  app.whenReady().then(async () => {
    const panel = require('../dist/main/browserPanel');
    const { cdpFor } = require('../dist/main/browserCdp');
    const window = new BrowserWindow({ show: false });
    panel.registerBrowserPanelHandlers(window);
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
    panel.destroyBrowserPanel();
    clearTimeout(timeout);
    console.log('Native popup lifecycle passed: handle, content, source focus and close restoration.');
    app.exit(0);
  }).catch(error => { console.error(error); app.exit(1); });
}
