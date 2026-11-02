// Put into every artboard page the app serves: it answers the canvas panel's questions about the
// page's elements (their tree, the element at a point, and for one element its box, the style
// rules that match it and what it inherits). The frame is sandboxed without same-origin, so the
// panel cannot read the page itself; it asks by message and only its own parent is answered. It
// changes nothing in the page and must hold no closing-tag sequence, since it is put inside a
// script element as it is.
(function () {
  var INHERITED = ["color", "font-family", "font-size", "font-weight", "font-style", "line-height",
    "letter-spacing", "text-align", "text-transform", "white-space"];
  var SHOWN = ["display", "position", "flex-direction", "justify-content", "align-items", "gap",
    "padding", "margin", "font-family", "font-size", "font-weight", "line-height", "color",
    "background-color", "border-radius", "opacity"];
  var MAX_NODES = 400;

  function pathOf(el) {
    var parts = [];
    while (el && el !== document.body && el.parentElement) {
      parts.unshift(Array.prototype.indexOf.call(el.parentElement.children, el));
      el = el.parentElement;
    }
    return el === document.body ? parts.join(".") : null;
  }

  function byPath(path) {
    var el = document.body;
    if (path) {
      var parts = String(path).split(".");
      for (var i = 0; i < parts.length && el; i++) el = el.children[Number(parts[i])];
    }
    return el || null;
  }

  function kindOf(el) {
    var tag = el.tagName.toLowerCase();
    if (/^(img|svg|picture|canvas|video)$/.test(tag)) return "Image";
    var style = getComputedStyle(el);
    if (style.display.indexOf("flex") >= 0) return style.flexDirection.indexOf("column") === 0 ? "Column" : "Row";
    if (style.display.indexOf("grid") >= 0) return "Grid";
    if (!el.children.length && el.textContent.trim()) return "Text";
    return "Frame";
  }

  function textOf(el) {
    // innerText, as drawn: a line break between two words is a space, not nothing.
    return (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60);
  }

  function skipped(el) {
    return /^(script|style|template|noscript|link|meta)$/i.test(el.tagName);
  }

  function tree() {
    var count = 0;
    function node(el) {
      count++;
      var children = [];
      var kind = kindOf(el);
      if (kind !== "Image" && kind !== "Text") {
        for (var i = 0; i < el.children.length && count < MAX_NODES; i++) {
          if (!skipped(el.children[i])) children.push(node(el.children[i]));
        }
      }
      return { path: pathOf(el), tag: el.tagName.toLowerCase(), kind: kind, text: textOf(el), children: children };
    }
    return node(document.body);
  }

  function eachRule(rules, visit) {
    for (var i = 0; i < rules.length; i++) {
      var rule = rules[i];
      if (rule.selectorText !== undefined) visit(rule);
      else if (rule.media && rule.cssRules) {
        if (window.matchMedia(rule.media.mediaText).matches) eachRule(rule.cssRules, visit);
      } else if (rule.cssRules) eachRule(rule.cssRules, visit);
    }
  }

  function matchedRules(el) {
    var found = [];
    for (var s = 0; s < document.styleSheets.length; s++) {
      var rules;
      try {
        rules = document.styleSheets[s].cssRules;
      } catch (e) {
        continue;
      }
      eachRule(rules, function (rule) {
        try {
          if (el.matches(rule.selectorText)) found.push(rule);
        } catch (e) {
          // A selector this browser cannot test (a vendor pseudo-class) matches nothing here.
        }
      });
    }
    return found;
  }

  // From the serialised text, not the indexed properties: those are longhands (row-gap and
  // column-gap for a gap), while the text keeps the shorthands the page was written with.
  function declarations(style) {
    var out = [];
    (style.cssText || "").split(/;(?![^(]*\))/).forEach(function (part) {
      var at = part.indexOf(":");
      if (at > 0) out.push([part.slice(0, at).trim(), part.slice(at + 1).trim()]);
    });
    return out;
  }

  function labelOf(el) {
    var label = el.tagName.toLowerCase();
    if (el.id) label += "#" + el.id;
    else if (el.classList.length) label += "." + el.classList[0];
    return label;
  }

  function inherited(el) {
    var taken = {};
    matchedRules(el).forEach(function (rule) {
      declarations(rule.style).forEach(function (d) { taken[d[0]] = true; });
    });
    if (el.style) declarations(el.style).forEach(function (d) { taken[d[0]] = true; });
    var groups = [];
    for (var up = el.parentElement; up; up = up.parentElement) {
      var props = [];
      matchedRules(up).concat(up.style ? [{ style: up.style }] : []).forEach(function (rule) {
        declarations(rule.style).forEach(function (d) {
          if (INHERITED.indexOf(d[0]) >= 0 && !taken[d[0]]) {
            taken[d[0]] = true;
            props.push(d);
          }
        });
      });
      if (props.length) groups.push({ from: labelOf(up), props: props });
    }
    return groups;
  }

  function describe(el) {
    if (!el) return null;
    var box = el.getBoundingClientRect();
    var style = getComputedStyle(el);
    var computed = {};
    SHOWN.forEach(function (name) { computed[name] = style.getPropertyValue(name); });
    var rules = matchedRules(el).map(function (rule) {
      return { selector: rule.selectorText, declarations: declarations(rule.style) };
    });
    if (el.getAttribute("style")) rules.push({ selector: "style attribute", declarations: declarations(el.style) });
    return {
      path: pathOf(el),
      tag: el.tagName.toLowerCase(),
      label: labelOf(el),
      kind: kindOf(el),
      text: textOf(el),
      // For an element that holds text alone: its whole text as the source has it (textContent, not
      // the drawn innerText, which follows text-transform), so an edit can be checked against it.
      content: el.children.length ? null : (el.textContent || "").replace(/\s+/g, " ").trim(),
      box: { x: box.left + scrollX, y: box.top + scrollY, width: box.width, height: box.height },
      computed: computed,
      rules: rules,
      inherited: inherited(el),
    };
  }

  window.addEventListener("message", function (e) {
    var data = e.data;
    if (e.source !== parent || !data || typeof data.coscribe !== "string") return;
    if (data.coscribe === "inspect-tree") parent.postMessage({ coscribe: "inspect-tree", tree: tree() }, "*");
    else if (data.coscribe === "inspect-pick" || data.coscribe === "inspect-select") {
      var el = data.coscribe === "inspect-pick" ? document.elementFromPoint(Number(data.x), Number(data.y)) : byPath(data.path);
      while (el && el.closest && el.closest("svg") && el.tagName.toLowerCase() !== "svg") el = el.parentElement;
      parent.postMessage({ coscribe: "inspect-element", element: describe(el) }, "*");
    }
  });
})();
