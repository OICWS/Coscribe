(function () {
  "use strict";
  var root = document.body.getAttribute("data-root") || "";
  var html = document.documentElement;

  /* Theme: the same stored key as the main site, so a choice made there holds here. */
  document.getElementById("theme").addEventListener("click", function () {
    var cur = html.getAttribute("data-theme");
    var dark = cur ? cur === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark";
    html.setAttribute("data-theme", next);
    try { localStorage.setItem("coscribe-theme", next); } catch (e) {}
  });

  /* Narrow screens: the sidebar is a drawer. */
  var menu = document.getElementById("menu");
  var scrim = document.getElementById("scrim");
  function setNav(open) {
    document.body.classList.toggle("nav-open", open);
    menu.setAttribute("aria-expanded", String(open));
  }
  menu.addEventListener("click", function () { setNav(!document.body.classList.contains("nav-open")); });
  scrim.addEventListener("click", function () { setNav(false); });

  /* A link icon on each heading, so a section can be sent to a colleague. */
  var link = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>';
  document.querySelectorAll(".prose h2[id], .prose h3[id]").forEach(function (h) {
    var a = document.createElement("a");
    a.className = "anchor";
    a.href = "#" + h.id;
    a.setAttribute("aria-label", "链接到这一节");
    a.innerHTML = link;
    h.appendChild(a);
  });

  /* Copy the page's Markdown, for pasting into a chat with an AI or a colleague. */
  var copy = document.getElementById("copy-md");
  if (copy) {
    copy.addEventListener("click", function () {
      var label = copy.querySelector("span");
      fetch(copy.getAttribute("data-src"))
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(function (text) { return navigator.clipboard.writeText(text); })
        .then(function () { label.textContent = "已复制"; copy.classList.add("done"); })
        .catch(function () { label.textContent = "复制失败，请点“查看 Markdown”"; })
        .finally(function () {
          setTimeout(function () { label.textContent = "复制 Markdown"; copy.classList.remove("done"); }, 2000);
        });
    });
  }

  /* "In this article": highlight the section being read. */
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (tocLinks.length && "IntersectionObserver" in window) {
    var heads = tocLinks.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); });
    var visible = new Set();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.isIntersecting ? visible.add(e.target) : visible.delete(e.target); });
      var current = heads.find(function (h) { return visible.has(h); });
      if (!current) {
        current = heads.filter(function (h) { return h.getBoundingClientRect().top < 140; }).pop();
      }
      tocLinks.forEach(function (a, i) { a.classList.toggle("active", heads[i] === current); });
    }, { rootMargin: "-110px 0px -55% 0px" });
    heads.forEach(function (h) { if (h) io.observe(h); });
  }

  /* Search: the whole index is small, so it loads on first focus and is searched in the page. */
  var q = document.getElementById("q");
  var box = document.getElementById("results");
  var index = null;
  var sel = -1;

  function load() {
    if (index) return Promise.resolve(index);
    return fetch(root + "search.json").then(function (r) { return r.json(); }).then(function (d) { index = d; return d; });
  }
  function escape(s) {
    return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
  function mark(s, terms) {
    var out = escape(s);
    terms.forEach(function (t) {
      out = out.split(escape(t)).join("<mark>" + escape(t) + "</mark>");
    });
    return out;
  }
  function snippet(text, terms) {
    var low = text.toLowerCase();
    var at = -1;
    terms.some(function (t) { at = low.indexOf(t); return at >= 0; });
    if (at < 0) return text.slice(0, 120);
    var start = Math.max(0, at - 30);
    return (start ? "…" : "") + text.slice(start, start + 120);
  }
  function score(page, terms) {
    var total = 0;
    var t = page.t.toLowerCase(), h = page.h.join(" ").toLowerCase(), x = page.x.toLowerCase();
    for (var i = 0; i < terms.length; i++) {
      var term = terms[i], s = 0;
      if (t.indexOf(term) >= 0) s += 10;
      if (h.indexOf(term) >= 0) s += 4;
      if (x.indexOf(term) >= 0) s += 1 + Math.min(3, x.split(term).length - 2);
      if (!s) return 0;
      total += s;
    }
    return total;
  }
  function show() {
    var value = q.value.trim().toLowerCase();
    sel = -1;
    if (!value) { box.hidden = true; return; }
    var terms = value.split(/\s+/).filter(Boolean);
    load().then(function (pages) {
      var hits = pages
        .map(function (p) { return { p: p, s: score(p, terms) }; })
        .filter(function (r) { return r.s > 0; })
        .sort(function (a, b) { return b.s - a.s; })
        .slice(0, 8);
      if (!hits.length) {
        box.innerHTML = '<div class="empty">没有找到“' + escape(q.value.trim()) + '”。换个说法试试，比如功能在程序里的名字。</div>';
      } else {
        // The link is set as a property, not spliced into markup; only escaped text goes through innerHTML.
        box.replaceChildren.apply(box, hits.map(function (r) {
          var a = document.createElement("a");
          a.setAttribute("role", "option");
          a.href = root + r.p.u;
          a.innerHTML =
            (r.p.g ? '<div class="r-g">' + escape(r.p.g) + "</div>" : "") +
            '<div class="r-t">' + mark(r.p.t, terms) + "</div>" +
            '<div class="r-x">' + mark(snippet(r.p.x, terms), terms) + "</div>";
          return a;
        }));
      }
      box.hidden = false;
    });
  }
  function move(step) {
    var items = box.querySelectorAll("a");
    if (!items.length) return;
    sel = (sel + step + items.length) % items.length;
    items.forEach(function (a, i) { a.setAttribute("aria-selected", String(i === sel)); });
    items[sel].scrollIntoView({ block: "nearest" });
  }
  q.addEventListener("focus", load);
  q.addEventListener("input", show);
  q.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") {
      var items = box.querySelectorAll("a");
      var target = items[sel >= 0 ? sel : 0];
      if (target) location.href = target.href;
    } else if (e.key === "Escape") { q.value = ""; box.hidden = true; q.blur(); }
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search")) box.hidden = true;
  });
  document.addEventListener("keydown", function (e) {
    var tag = (e.target.tagName || "").toLowerCase();
    if (e.key === "/" && tag !== "input" && tag !== "textarea" && !e.target.isContentEditable) {
      e.preventDefault();
      q.focus();
    }
    if (e.key === "Escape") setNav(false);
  });
})();
