/* Plays back a real Coscribe conversation in the app's own markup.
 *
 * Each scenes/<lang>-<n>/scene.json was taken from the real UI rendering a conversation that ran
 * on Windows (tools/capture.cjs): the window, the prompt, every reply, every tool call's opened
 * view and the panel the made file opens in. This file only decides when each piece appears, and
 * names the calls with the app's own wording (labels.js, bundled from transcriptGrouping.ts). */
(function () {
  "use strict";

  var L = window.CoscribeLabels;
  var stage = document.getElementById("stage");

  /* What the capture can't know: the title the app gave the conversation on Windows and how
   * long the run took there (run.json; the two without a time are counted from the screenshots
   * taken every 12 seconds), which the turn timer counts through in fast forward. */
  var SCENES = {
    "en-1": { title: "Build Q3 sales business review", seconds: 341 },
    "en-2": { title: "Review supply agreement against standard terms", seconds: 112 },
    "en-3": { title: "Reconcile September bank vs ledger", seconds: 160 },
    "en-4": { title: "Export Q4 CRM renewals", seconds: 247 },
    "en-5": { title: "Q3 sales review chart next steps", seconds: 76 },
    "zh-1": { title: "Q3销售数据经营分析PPT", seconds: 353 },
    "zh-2": { title: "对照标准审供货合同", seconds: 176 },
    "zh-3": { title: "银行流水与账簿对账", seconds: 138 },
    "zh-4": { title: "CRM导出Q4续约客户", seconds: 96 },
    "zh-5": { title: "Q3销售经营分析", seconds: 84 },
  };
  var GREETING = "Good work starts with a good question";

  var params = new URLSearchParams(location.search);
  var lang = params.get("lang") === "zh" || location.hash === "#zh" ? "zh" : "en";
  var sceneNo = Math.max(1, Number(params.get("scene")) || 1);
  var standalone = window.parent === window;
  // Embedded, the page waits for the homepage to say it is on screen.
  var paused = params.get("autoplay") === "0";
  var token = 0;
  var cache = {};

  /* Wide, the window is drawn at the size the conversations were captured at (1280 by 861) and
   * scaled to fit. On a phone that would make the text unreadable, so the window is drawn 680
   * wide and as tall as the frame, with the chat filling it and a panel over it, as the app lays
   * itself out in a narrow window. */
  var narrow = false;
  function fit() {
    narrow = window.innerWidth < 900 && window.innerHeight / window.innerWidth > 0.9;
    var w = narrow ? 680 : 1280;
    var s = narrow ? window.innerWidth / w : Math.min(window.innerWidth / 1280, window.innerHeight / 861);
    stage.style.width = w + "px";
    stage.style.height = (narrow ? window.innerHeight / s : 861) + "px";
    stage.style.transform = "scale(" + s + ")";
    stage.style.left = Math.max(0, (window.innerWidth - w * s) / 2) + "px";
    stage.classList.toggle("demo-narrow", narrow);
  }
  window.addEventListener("resize", fit);
  fit();

  function sleep(ms, t) {
    return new Promise(function (resolve, reject) {
      var left = ms;
      (function tick() {
        if (t !== token) return reject(new Error("stopped"));
        if (paused) return setTimeout(tick, 100);
        if (left <= 0) return resolve();
        var step = Math.min(50, left);
        left -= step;
        setTimeout(tick, step);
      })();
    });
  }

  function el(html) {
    var box = document.createElement("div");
    box.innerHTML = html.trim();
    return box.firstElementChild;
  }

  function esc(text) {
    return String(text).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* The capture ran against a local server with a test model; the window on Windows showed the
   * workspace "Demo", deepseek-flash at Low, and the file made just now. */
  function fix(html, meta) {
    return html
      .replace(/>\s*[Ww]orkspace\s*</g, ">Demo<")
      .replace(/>fake</g, ">deepseek-flash<")
      .replace(/<span class="">Medium<\/span>/g, '<span class="">Low</span>')
      .replace(/text-\[var\(--muted\)\] opacity-60/g, "text-[var(--muted)] hover:text-[var(--fg)]")
      .replace(/\b\d+ (?:hours?|minutes?|days?) ago\b|\b\d+[hmd] ago\b/g, "just now")
      .replace(/title="New session">New session</g, 'title="' + esc(meta.title) + '">' + esc(meta.title) + "<");
  }

  function elapsed(seconds) {
    var s = Math.max(0, Math.floor(seconds));
    return s >= 60 ? Math.floor(s / 60) + "m " + (s % 60) + "s" : s + "s";
  }

  /* ---------- tool calls, as ToolRuns.tsx draws them ---------- */

  function label(parts) {
    var glue = parts.glue == null ? " " : parts.glue;
    var failed = parts.failedCount !== undefined
      ? '<span class="ml-1 text-[var(--danger)]">(' + parts.failedCount + " failed)</span>" : "";
    if (parts.shimmer) {
      return '<span class="shimmer-text">' + esc(parts.verb) + (parts.object ? esc(glue + parts.object) : "") + "</span>" + failed;
    }
    var html = esc(parts.verb) + (parts.object
      ? esc(glue) + '<span class="font-medium text-[var(--fg)]">' + esc(parts.object) + "</span>" : "") + failed;
    return parts.failed ? '<span class="text-[var(--danger)]">' + html + "</span>" : html;
  }

  /* Tools the app still names by their raw name ("build_pptx_from_pages"); the demo words them
   * the way the app words its other calls. */
  function base(p) { return String(p || "").split(/[\\/]/).pop(); }
  var WORDS = {
    build_pptx_from_pages: function (a) { return ["Built", "Building", base(a.path)]; },
    render_pptx_preview: function (a) { return ["Previewed", "Previewing", base(a.path)]; },
    replace_docx_text: function (a) { return ["Edited", "Editing", base(a.path)]; },
    insert_docx_text: function (a) { return ["Edited", "Editing", base(a.path)]; },
    edit_docx_review: function (a) { return ["Reviewed", "Reviewing", base(a.path)]; },
    copy_file: function (a) { return ["Copied", "Copying", base(a.source)]; },
    move_file: function (a) { return ["Moved", "Moving", base(a.source)]; },
    browser_navigate: function (a) { return ["Opened", "Opening", a.url]; },
    browser_snapshot: function () { return ["Read the page", "Reading the page", null]; },
    browser_click: function () { return ["Clicked on the page", "Clicking on the page", null]; },
    browser_select_option: function (a) { return ["Chose", "Choosing", (a.values || []).join(", ") || null]; },
    browser_evaluate: function () { return ["Read the page's data", "Reading the page's data", null]; },
    browser_save_table: function (a) { return ["Saved the table", "Saving the table", a.table || null]; },
  };
  function polish(parts, items) {
    if (parts.object != null) return parts;
    var item = items.filter(function (it) { return it.toolName === parts.verb; })[0];
    if (!item || !WORDS[item.toolName]) return parts;
    var w = WORDS[item.toolName](item.arguments || {});
    return Object.assign({}, parts, { verb: parts.running ? w[1] : w[0], object: w[2], glue: " " });
  }

  var CHEVRON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="h-3.5 w-3.5 shrink-0 transition-transform motion-reduce:transition-none ROT"><path d="M9 6l6 6-6 6"></path></svg>';
  function chevron(open) { return CHEVRON.replace("ROT", open ? "rotate-90" : ""); }

  function Group(details) {
    this.items = [];
    this.first = 0;
    this.open = false;
    this.rows = {};
    this.live = true;
    this.details = details;
    this.node = el('<div class="w-full text-sm demo-in"></div>');
  }
  Group.prototype.render = function () {
    var self = this;
    var items = this.items;
    var header = L.summarizeGroupParts(items, this.live);
    var head = header.shown.map(function (p, i) { return (i > 0 ? ", " : "") + label(L.inSentence(polish(p, items), i)); }).join("");
    if (header.more > 0) head += (header.shown.length > 0 ? ", and " : "And ") + header.more + " more action" + (header.more === 1 ? "" : "s");
    if (header.active) head += (header.shown.length > 0 ? ", " : "") + label(L.inSentence(polish(header.active, items), header.shown.length));
    var html = '<button type="button" data-demo-group aria-expanded="' + this.open + '" class="inline-flex max-w-full items-center gap-1 text-left text-[var(--muted)] [overflow-wrap:anywhere] hover:text-[var(--fg)]"><span class="min-w-0">' + head + "</span>" + chevron(this.open) + "</button>";
    if (this.open) {
      html += '<div class="mt-2 overflow-hidden rounded-xl border border-[var(--border)]">';
      if (items.length === 1) {
        html += items[0].result === undefined ? '<div class="flex flex-col"><p class="px-3 py-2 text-[var(--muted)]">No result yet.</p></div>' : this.details[this.first] || "";
      } else {
        items.forEach(function (item, i) {
          var open = !!self.rows[i];
          var running = L.isRunning(item, self.live);
          html += '<div class="' + (i === 0 ? "" : "border-t border-[var(--border)]") + '">' +
            '<button type="button" data-demo-row="' + i + '" aria-expanded="' + open + '" class="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-[var(--card-bg)]">' +
            '<span class="min-w-0 flex-1 truncate">' + label(polish(L.summarizeItemParts(item, running), [item])) + "</span>" +
            '<span class="text-[var(--muted)]">' + chevron(open) + "</span></button>" +
            (open ? '<div class="border-t border-[var(--border)]">' + (item.result === undefined
              ? '<div class="flex flex-col"><p class="px-3 py-2 text-[var(--muted)]">No result yet.</p></div>'
              : self.details[self.first + i] || "") + "</div>" : "") +
            "</div>";
        });
      }
      html += "</div>";
    }
    this.node.innerHTML = html;
  };

  /* ---------- one scene ---------- */

  var view = null; // what is on screen now, for clicks

  function load(key) {
    if (!cache[key]) {
      cache[key] = fetch("scenes/" + key + "/scene.json").then(function (r) {
        if (!r.ok) throw new Error(key + ": " + r.status);
        return r.json();
      });
    }
    return cache[key];
  }

  /* Puts a captured window on the stage and moves the conversation into it. A window captured at
   * rest gets the running composer back while the turn is still going. */
  function mount(v, html, name) {
    stage.innerHTML = fix(html, v.meta);
    v.log = stage.querySelector('[data-testid="chat-log"] > div');
    v.notices = stage.querySelector('[data-testid="notice-stack"]');
    v.scroller = stage.querySelector('[data-testid="chat-log"]');
    v.stage = name;
    if (v.turn) v.log.appendChild(v.turn);
    if (v.noticeBox) v.notices.appendChild(v.noticeBox);
    if (v.running) stage.querySelector('[data-testid="composer"]').outerHTML = fix(v.data.working.composer, v.meta);
    v.timer = stage.querySelector('[data-testid="run-status"]');
    if (v.timer) v.timer.textContent = v.clock || "0s";
    v.scroller.addEventListener("scroll", function () {
      v.stickToBottom = v.scroller.scrollHeight - v.scroller.scrollTop - v.scroller.clientHeight < 40;
    });
    var area = stage.querySelector('[data-testid="browser-page-area"]');
    if (area && v.crm && v.crm.open) area.appendChild(crmFrame(v));
    v.scroller.scrollTop = v.scroller.scrollHeight;
  }

  /* The sample CRM the run used, live in the Browser panel, set to where the run had taken it. */
  function crmFrame(v) {
    var frame = document.createElement("iframe");
    frame.title = "Northwind CRM";
    frame.src = "crm/index.html";
    frame.style.cssText = "position:absolute;inset:0;width:100%;height:100%;border:0;background:#fff";
    frame.addEventListener("load", function () {
      var tries = 0;
      (function apply() {
        var doc = frame.contentDocument;
        if (!doc || !doc.getElementById("rows") || !doc.getElementById("rows").children.length) {
          if (tries++ < 40) setTimeout(apply, 50);
          return;
        }
        var q = doc.getElementById("q");
        if (v.crm.quarter && q.value !== v.crm.quarter) { q.value = v.crm.quarter; q.dispatchEvent(new Event("change")); }
        for (var i = 0; i < v.crm.page; i++) doc.getElementById("next").click();
      })();
    });
    v.crm.frame = frame;
    return frame;
  }

  function crmStep(v, call) {
    var doc = v.crm.frame && v.crm.frame.contentDocument;
    var a = call.arguments || {};
    if (call.toolName === "browser_select_option") {
      v.crm.quarter = "Q4";
      v.crm.page = 0;
      if (doc && doc.getElementById("q")) { doc.getElementById("q").value = "Q4"; doc.getElementById("q").dispatchEvent(new Event("change")); }
    } else if ((call.toolName === "browser_save_table" && a.next_page) || call.toolName === "browser_click") {
      if (v.crm.page < 1) {
        v.crm.page += 1;
        if (doc && doc.getElementById("next")) doc.getElementById("next").click();
      }
    }
  }

  function toBottom(v) {
    if (v.stickToBottom) v.scroller.scrollTop = v.scroller.scrollHeight;
  }

  function typeInto(textarea, text, t) {
    var i = 0;
    var send = stage.querySelector('button[title="Send"]');
    return new Promise(function (resolve, reject) {
      (function next() {
        if (t !== token) return reject(new Error("stopped"));
        if (paused) return setTimeout(next, 100);
        i = Math.min(text.length, i + 1);
        textarea.value = text.slice(0, i);
        textarea.style.height = "auto";
        textarea.style.height = textarea.scrollHeight + "px";
        if (send) send.removeAttribute("disabled");
        if (i >= text.length) return resolve();
        setTimeout(next, 18);
      })();
    });
  }

  async function play(n, t) {
    var key = lang + "-" + n;
    var meta = SCENES[key];
    if (!meta) return;
    var data = await load(key);
    if (t !== token) return;

    // The start page, with the prompt typed in.
    stage.innerHTML = fix(data.home, meta);
    var h1 = stage.querySelector("h1");
    if (h1) h1.textContent = GREETING;
    view = { data: data, meta: meta, stage: "home" };
    progress(0);
    await sleep(500, t);
    await typeInto(stage.querySelector("textarea"), data.prompt, t);
    await sleep(700, t);

    // Sent: the conversation, with the composer showing the turn is running.
    var v = { data: data, meta: meta, groups: [], stickToBottom: true, running: true, crm: { open: false, quarter: "", page: 0 } };
    v.turn = el('<div class="group/turn relative flex flex-col gap-3"></div>');
    v.turn.appendChild(el(fix(data.user, meta)));
    mount(v, data.shell, "chat");
    view = v;

    var order = data.order;
    var steps = order.length;
    var tool = 0;
    var agent = 0;
    var group = null;
    var pace = Math.max(160, Math.min(600, 16000 / Math.max(1, data.tools.length)));
    for (var i = 0; i < steps; i++) {
      progress(0.1 + 0.8 * (i / steps));
      v.clock = elapsed((i / steps) * meta.seconds);
      if (v.timer) v.timer.textContent = v.clock;
      var call = order[i] === "t" ? data.tools[tool] : null;
      var browsing = call && /^browser_/.test(call.toolName);
      if (browsing && data.browser && !/^browser/.test(v.stage)) {
        // The first visit to a site waits for the person's yes, as the app asks on Windows.
        if (!v.crm.allowed) {
          mount(v, data.browser.ask, "browser-ask");
          await sleep(2200, t);
          v.crm.allowed = true;
        }
        v.crm.open = true;
        mount(v, data.browser.busy, "browser-busy");
      } else if (!browsing && v.stage === "browser-busy") {
        mount(v, data.browser.idle, "browser-idle");
      }
      if (call) {
        if (!group) {
          group = new Group(data.details);
          group.first = tool;
          v.groups.push(group);
          v.turn.appendChild(group.node);
        }
        tool++;
        var item = { kind: "tool", id: "t" + tool, toolName: call.toolName, arguments: call.arguments };
        group.items.push(item);
        // Opened as if clicked once a run has a second call; a lone call stays one line.
        if (group.items.length === 2 && !group.touched) group.open = true;
        group.render();
        toBottom(v);
        if (browsing) crmStep(v, call);
        await sleep(browsing ? Math.max(pace, 1100) * 0.6 : pace * 0.6, t);
        item.result = call.isError ? "error" : "ok";
        item.isError = call.isError;
        group.render();
        await sleep(browsing ? Math.max(pace, 1100) * 0.4 : pace * 0.4, t);
      } else {
        if (group) { group.live = false; group.render(); }
        group = null;
        var last = agent === data.agents.length - 1;
        var reply = el(data.agents[agent++]);
        reply.classList.add("demo-in");
        v.turn.appendChild(reply);
        if (last) await reveal(reply, v, t);
        else { toBottom(v); await sleep(900, t); }
      }
    }
    if (group) { group.live = false; group.render(); }
    v.clock = elapsed(meta.seconds);
    if (v.timer) v.timer.textContent = v.clock;
    await sleep(300, t);

    // Done: the composer at rest and the notice for the file the run made.
    v.running = false;
    var composer = stage.querySelector('[data-testid="composer"]');
    var rest = el(fix(data.shell, meta)).querySelector('[data-testid="composer"]');
    if (composer && rest) composer.replaceWith(rest);
    if (v.stage === "browser-busy") mount(v, data.browser.idle, "browser-idle");
    if (data.cards) {
      var cards = el(data.cards);
      cards.classList.add("demo-in");
      v.turn.appendChild(cards);
    }
    if (data.replyActions) v.turn.appendChild(el(data.replyActions));
    if (data.notices) {
      v.noticeBox = el(fix(data.notices, meta));
      v.noticeBox.classList.add("demo-in");
      v.notices.appendChild(v.noticeBox);
    }
    toBottom(v);
    await sleep(2200, t);
    if (data.open) {
      var notice = stage.querySelector('[data-testid="notice"]');
      if (notice) notice.classList.add("bg-[var(--notice-hover-bg)]");
      await sleep(600, t);
      openPanel();
    }
    progress(1);
    await sleep(standalone ? 9000 : 7000, t);
    finished(n);
  }

  async function reveal(reply, v, t) {
    var prose = reply.querySelector(".prose") || reply;
    var blocks = Array.prototype.slice.call(prose.children);
    blocks.forEach(function (b) { b.style.display = "none"; });
    for (var i = 0; i < blocks.length; i++) {
      blocks[i].style.display = "";
      blocks[i].classList.add("demo-in");
      toBottom(v);
      await sleep(Math.min(900, 160 + blocks[i].textContent.length * 3), t);
    }
  }

  function openPanel() {
    var v = view;
    if (!v || !v.data || !v.data.open || v.stage === "open" || v.running) return;
    mount(v, v.data.open.shell, "open");
    var panel = stage.querySelector("section[data-panel]");
    if (panel) panel.classList.add("demo-in");
  }

  function closePanel() {
    var v = view;
    if (!v || !v.data || v.stage === "chat" || v.stage === "home" || v.running) return;
    mount(v, v.data.shell, "chat");
  }

  function showSlide(button) {
    var strip = button.parentElement;
    Array.prototype.forEach.call(strip.children, function (b) {
      var on = b === button;
      b.setAttribute("aria-current", String(on));
      b.classList.toggle("border-[var(--accent)]", on);
      b.classList.toggle("border-transparent", !on);
      b.classList.toggle("hover:border-[var(--border-hover)]", !on);
    });
    var main = stage.querySelector("[data-slide] img");
    var src = button.querySelector("img");
    if (main && src) main.src = src.getAttribute("src");
  }

  // An entrance plays once; moving the conversation into another window must not replay it.
  stage.addEventListener("animationend", function (event) { event.target.classList.remove("demo-in"); });

  /* ---------- clicks ---------- */

  stage.addEventListener("click", function (event) {
    var target = event.target.closest("button");
    if (!target || !view) return;
    if (target.hasAttribute("data-demo-group")) {
      var g = (view.groups || []).filter(function (x) { return x.node.contains(target); })[0];
      if (g) { g.open = !g.open; g.touched = true; g.render(); }
    } else if (target.hasAttribute("data-demo-row")) {
      var gr = (view.groups || []).filter(function (x) { return x.node.contains(target); })[0];
      var i = Number(target.getAttribute("data-demo-row"));
      if (gr) { gr.rows[i] = !gr.rows[i]; gr.render(); }
    } else if (target.closest('[data-testid="notice"]')) {
      if (target.title === "Close") { target.closest('[data-testid="notice"]').remove(); return; }
      openPanel();
    } else if ((target.closest(".prose") && target.querySelector("span.truncate")) || /^Open /.test(target.title)) {
      openPanel();
    } else if (/^Close /.test(target.getAttribute("aria-label") || "")) {
      closePanel();
    } else if (/^Slide \d+$/.test(target.getAttribute("aria-label") || "")) {
      showSlide(target);
    }
    held();
  });

  /* A click on the window holds the scene where it is for a while before the tour moves on. */
  var holdUntil = 0;
  function held() { holdUntil = Date.now() + 15000; }

  function progress(value) {
    if (!standalone) window.parent.postMessage({ type: "coscribe-demo", event: "progress", value: value }, "*");
  }

  function finished(n) {
    if (Date.now() < holdUntil) {
      var t = token;
      setTimeout(function () { if (t === token) finished(n); }, 1000);
      return;
    }
    if (standalone) start(SCENES[lang + "-" + (n % 5 + 1)] ? n % 5 + 1 : 1);
    else window.parent.postMessage({ type: "coscribe-demo", event: "done", scene: n }, "*");
  }

  function start(n) {
    sceneNo = n;
    token += 1;
    holdUntil = 0;
    var t = token;
    play(n, t).catch(function (e) {
      if (e && e.message !== "stopped") console.error(e);
    });
  }

  window.addEventListener("message", function (event) {
    var m = event.data;
    if (!m || m.type !== "coscribe-demo") return;
    if (m.lang && m.lang !== lang) { lang = m.lang === "zh" ? "zh" : "en"; if (m.scene == null) start(sceneNo); }
    if (typeof m.paused === "boolean") paused = m.paused;
    if (m.scene != null) start(Number(m.scene));
  });

  start(sceneNo);
})();
