// Put at the end of every dashboard the app serves: hovering a figure, chart or table bound with
// data-figure or data-source shows a small "i"; clicking it says which dataset the element shows,
// where that came from, when it was made and, for a figure, its formula. It is the page's own,
// so it works the same in the panel and in an exported file. It must hold no closing-tag sequence,
// since it is put inside a script element as it is.
(function () {
  var c = window.coscribe || { datasets: {}, figures: {} };
  var css = document.createElement("style");
  css.textContent =
    ".cs-why{position:fixed;z-index:2147483646;width:22px;height:22px;padding:0;border-radius:11px;" +
    "border:1px solid rgba(0,0,0,.15);background:#fff;color:#4f6ef7;font:600 13px/20px system-ui," +
    "sans-serif;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.15);display:none}" +
    ".cs-pop{position:fixed;z-index:2147483647;max-width:320px;background:#fff;color:#1f2328;" +
    "border:1px solid rgba(0,0,0,.12);border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,.18);" +
    "padding:12px 14px;font:13px/1.45 system-ui,'Segoe UI','Microsoft YaHei',sans-serif;display:none}" +
    ".cs-pop b{font-weight:600}.cs-pop .cs-k{color:#6b7280;font-size:12px}" +
    ".cs-pop div+div{margin-top:4px}.cs-pop b+div{margin-top:2px}";
  document.head.appendChild(css);
  var why = document.createElement("button");
  why.className = "cs-why";
  why.textContent = "i";
  why.title = "Where this comes from";
  var pop = document.createElement("div");
  pop.className = "cs-pop";
  pop.setAttribute("role", "dialog");
  document.body.appendChild(why);
  document.body.appendChild(pop);
  var target = null;

  function add(tag, text, cls) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    el.textContent = text;
    pop.appendChild(el);
    return el;
  }
  function line(key, value) {
    var row = document.createElement("div");
    var label = document.createElement("span");
    label.className = "cs-k";
    label.textContent = key + " ";
    row.appendChild(label);
    row.appendChild(document.createTextNode(value));
    pop.appendChild(row);
  }
  function describe(el) {
    pop.textContent = "";
    var ids = [];
    var figure = el.getAttribute("data-figure");
    if (figure) {
      var f = c.figures[figure] || {};
      add("b", f.label || figure);
      if (f.formula) line("Formula", f.formula);
      ids = f.from || [];
    }
    var source = el.getAttribute("data-source");
    if (source) ids = [source];
    ids.forEach(function (id) {
      var d = c.datasets[id] || {};
      add("div", "").appendChild(document.createElement("b")).textContent = d.title || id;
      if (d.source) line("Source", d.source);
      if (d.updated) line("Updated", d.updated);
      line("Rows", String((d.rows || []).length));
    });
    if (!pop.childNodes.length) add("div", "No dataset is named for this.", "cs-k");
  }
  document.addEventListener("mouseover", function (e) {
    var t = e.target;
    if (!t.closest || t === why || t.closest(".cs-pop")) return;
    var el = t.closest("[data-figure],[data-source]");
    if (!el) return;
    target = el;
    var r = el.getBoundingClientRect();
    why.style.left = Math.max(4, Math.min(innerWidth - 26, r.right - 26)) + "px";
    why.style.top = Math.max(4, r.top + 4) + "px";
    why.style.display = "block";
  });
  why.addEventListener("click", function (e) {
    e.stopPropagation();
    if (!target) return;
    describe(target);
    pop.style.display = "block";
    var r = why.getBoundingClientRect();
    pop.style.left = Math.max(8, Math.min(innerWidth - pop.offsetWidth - 8, r.right - pop.offsetWidth)) + "px";
    pop.style.top = Math.max(8, Math.min(innerHeight - pop.offsetHeight - 8, r.bottom + 6)) + "px";
  });
  document.addEventListener("click", function (e) {
    if (!pop.contains(e.target) && e.target !== why) pop.style.display = "none";
  });
  addEventListener(
    "scroll",
    function () {
      why.style.display = "none";
      pop.style.display = "none";
    },
    true,
  );
})();
