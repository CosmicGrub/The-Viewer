/* THE VIEWER -- shared.js: the ONE copy of the tiny helpers duplicated across ~14 pages
   (backlog A2, v0.96.0). Served at /shared.js. STRICTLY ES5 (legacy/RPS gate -- rps_lint
   enforces this file): no arrows, no const/let, no template literals.
   Pages adopt it with <script src="/shared.js"></script>; inline copies keep working
   during the transition (identical behavior), then get stripped page-by-page. */
(function (g) {
  "use strict";

  /* HTML-escape (superset of every per-page copy: handles & < > " ' and null/undefined). */
  function esc(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* Tiny query helpers. */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  /* Review finding (UX priority-5 review pass): is kiosk/glove mode on right now? Reads the same
     'viewer_kiosk' localStorage key palette.js itself owns (sets/toggles) -- this is the READ-ONLY
     half, safe to call from any page/script regardless of load order, since shared.js is the one file
     loaded FIRST on every page (before palette.js, before cadview.js/deepzoom.js/threed.html's own
     inline scripts). Was previously reimplemented independently (and inconsistently -- one copy used a
     different default) in cadview.js, deepzoom.js, and inline in threed.html; those now call this. */
  function kioskOn() {
    try { return window.localStorage.getItem("viewer_kiosk") === "1"; } catch (e) { return false; }
  }

  /* Recommendations annex #10 (ocr-badge-tooltips): a shared, plain-language confidence-tier
     bucketer for a raw 0..1 float, so a page doesn't have to reimplement its own thresholds/labels
     (which had already silently drifted once: index.html's part-match card used "<60" while
     rpstl_feature.py's own review() queue -- the backend's real, load-bearing "needs review"
     threshold -- used "<=0.6"). 0.6 here is not a new number: it matches rpstl_feature.py's
     review(max_conf=0.6) exactly, so a mechanic who taps a low-confidence part number sees the SAME
     boundary the review queue itself already treats as "needs a second look". Not master.html's own
     4-tier vocabulary (high/medium/review/low) -- that one is about masterfile.py's provenance-based
     corroboration (authoritative vs external), a different judgment than a raw RPSTL field-match
     score, and forcing a fake extra tier onto a score that only ever lands on 0/0.2/0.4/0.6/0.8/1.0
     would be a distinction without a difference. */
  function confTier(conf) {
    var c = (typeof conf === "number" && !isNaN(conf)) ? conf : 0;
    if (c >= 0.8) return { key: "high", label: "High confidence", note: "" };
    if (c > 0.6) return { key: "verify", label: "Verify before use",
      note: "One field didn't match cleanly — confirm nomenclature/CAGEC on the cited page." };
    return { key: "low", label: "Low confidence — verify on page",
      note: "This may be an OCR misread. Open the cited page to confirm before ordering." };
  }

  /* GET a JSON endpoint (XHR -- works on every tier; fetch needs a polyfill on legacy). */
  function getJSON(url, cb, errcb) {
    var x = new XMLHttpRequest();
    x.open("GET", url, true);
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      var data = null;
      try { data = JSON.parse(x.responseText || "null"); } catch (e) { /* non-JSON */ }
      if (x.status >= 200 && x.status < 300) cb(data, x);
      else if (errcb) errcb(x.status, data, x);
      else cb(null, x);
    };
    x.send();
    return x;
  }

  /* POST JSON, parse JSON back. */
  function postJSON(url, body, cb, errcb) {
    var x = new XMLHttpRequest();
    x.open("POST", url, true);
    x.setRequestHeader("Content-Type", "application/json");
    x.onreadystatechange = function () {
      if (x.readyState !== 4) return;
      var data = null;
      try { data = JSON.parse(x.responseText || "null"); } catch (e) { /* non-JSON */ }
      if (x.status >= 200 && x.status < 300) cb(data, x);
      else if (errcb) errcb(x.status, data, x);
      else cb(null, x);
    };
    x.send(JSON.stringify(body || {}));
    return x;
  }

  /* Non-blocking notification (replaces per-page toast copies + stray alert()s).
     Styles ship in base.css (#vw-toast); a minimal inline fallback keeps it working
     on pages that haven't adopted base.css yet. */
  var _toastTimer = null;
  function toast(msg, ms) {
    var el = document.getElementById("vw-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "vw-toast";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      if (!document.querySelector('link[href="/base.css"]')) {
        el.style.cssText = "position:fixed;left:50%;bottom:26px;transform:translateX(-50%);" +
          "background:#171d26;color:#e6e9ee;border:1px solid #2b333f;border-radius:8px;" +
          "padding:9px 16px;font-size:13px;z-index:9999;opacity:0;transition:opacity .2s";
      }
      document.body.appendChild(el);
    }
    el.textContent = msg == null ? "" : String(msg);
    el.className = "show";
    if (el.style.cssText) el.style.opacity = "1";
    if (_toastTimer) clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function () {
      el.className = "";
      if (el.style.cssText) el.style.opacity = "0";
    }, ms || 2600);
  }

  /* Debounce (backlog D29: type-ahead etc.). */
  function debounce(fn, wait) {
    var t = null;
    return function () {
      var args = arguments, self = this;
      if (t) clearTimeout(t);
      t = setTimeout(function () { t = null; fn.apply(self, args); }, wait || 120);
    };
  }

  /* Thousands separator for counts. */
  function fmtInt(n) {
    n = Math.round(Number(n) || 0);
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  /* v1.13.0 UI coherence: universal footer nav — every non-home page gets a small fixed
     "Back · Home · Ctrl+K" pill (bottom-right, ABOVE palette.js's own bottom:12px pills so
     nothing overlaps; toasts sit bottom-center). Styles in base.css (#vw-footer); inline
     fallback keeps it working on pages without base.css. Never injected twice (id guard). */
  function _footerNav() {
    try {
      if (document.getElementById("vw-footer")) return;
      var path = (window.location && window.location.pathname) || "/";
      if (path === "/" || path === "/index.html" || path === "") return;
      if (!document.body) return;
      var f = document.createElement("div");
      f.id = "vw-footer";
      if (!document.querySelector('link[href="/base.css"]')) {
        f.style.cssText = "position:fixed;right:12px;bottom:52px;z-index:9998;" +
          "background:#171d26;color:#9aa6b6;border:1px solid #2b333f;border-radius:20px;" +
          "padding:6px 12px;font:11px/1.4 -apple-system,Segoe UI,Arial,sans-serif;" +
          "opacity:.8;box-shadow:0 4px 14px rgba(0,0,0,.35)";
        /* base.css normally carries the print-hide; replicate it for no-base.css pages
           (e.g. /packet's paper preview must never print the nav pill). */
        var pstyle = document.createElement("style");
        pstyle.textContent = "@media print{#vw-footer{display:none !important}}";
        (document.head || document.documentElement).appendChild(pstyle);
      }
      var back = document.createElement("a");
      back.href = "/"; back.textContent = "← Back";
      back.title = "Go back to the previous page";
      back.onclick = function (ev) {
        if (ev && ev.preventDefault) ev.preventDefault();
        if (window.history && window.history.length > 1) window.history.back();
        else window.location.href = "/";
        return false;
      };
      var home = document.createElement("a");
      home.href = "/"; home.textContent = "⌂ Home";
      home.title = "Back to search (home)";
      var keys = document.createElement("span");
      keys.textContent = "Ctrl+K commands";
      keys.title = "Open the command palette (Ctrl+K)";
      keys.style.cursor = "pointer";
      keys.onclick = function () {
        if (typeof window.cmdkOpen === "function") window.cmdkOpen();
      };
      var d1 = document.createElement("span"); d1.textContent = " · ";
      var d2 = document.createElement("span"); d2.textContent = " · ";
      f.appendChild(back); f.appendChild(d1); f.appendChild(home);
      f.appendChild(d2); f.appendChild(keys);
      document.body.appendChild(f);
    } catch (e) { /* never break the host page over a nav pill */ }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _footerNav);
  } else {
    _footerNav();
  }

  /* v1.42.0: version-staleness banner. /healthz now reports started_with_version/code_changed_since_start
     (see engine/viewer_app.py's STARTUP_VERSION + current_disk_version()) -- a *running* process whose
     code on disk has since been changed (e.g. a git pull'd over a server nobody restarted) otherwise looks
     completely healthy: it answers requests fine, it just isn't running the fix anyone thinks it is. Shown
     on EVERY page (unlike _footerNav, which skips home) since this is a team-wide correctness signal, not
     per-page chrome. Deliberately NOT dismissible / no localStorage suppression -- a banner a mechanic can
     click away and never see again defeats the point; it persists every load until the process is actually
     restarted, at which point started_with_version naturally matches version again and this stops firing. */
  function _staleBanner() {
    try {
      function paint(data) {
        if (!data || !data.code_changed_since_start) return;
        if (document.getElementById("vw-stalebanner")) return;
        if (!document.body) return;
        var b = document.createElement("div");
        b.id = "vw-stalebanner";
        b.setAttribute("role", "alert");
        var msg = "⚠ Running code is stale — server started on v" +
          (data.started_with_version || "?") + ", disk now has v" + (data.version || "?") +
          ". Restart the server to pick up the fix.";
        if (!document.querySelector('link[href="/base.css"]')) {
          b.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;" +
            "background:#2a1210;color:#f5b8b3;border-bottom:1px solid #e0564f;" +
            "padding:8px 14px;font:12px/1.4 -apple-system,Segoe UI,Arial,sans-serif;" +
            "text-align:center";
        } else {
          b.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:9999;" +
            "background:var(--red);color:#2a0d0b;border-bottom:1px solid var(--red);" +
            "padding:8px 14px;font-size:12px;text-align:center;font-weight:600";
        }
        b.textContent = msg;
        document.body.appendChild(b);
      }
      function check() {
        getJSON("/healthz", paint, function () { /* transient failure -- never break the host page */ });
      }
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", check);
      } else {
        check();
      }
      setInterval(check, 5 * 60 * 1000);   // v1.42.0: re-poll every 5 min, same cadence as this codebase's other background polls
    } catch (e) { /* never break the host page over a staleness banner */ }
  }
  _staleBanner();

  /* Roadmap Now-tier item 3 (a11y): a shared focus trap for modal dialogs, modeled on palette.js's
     own inline Tab-trap/focus-restore/Escape handling (cmdk, the only correct implementation of
     this in the codebase before now) but generalized so index.html's other modals (#sidegate,
     #pnreview, #overlay, #setgate, #tsgate) don't each need to reimplement it. Those modals are
     opened/closed from many scattered call sites throughout index.html (button handlers, not one
     owned open()/close() pair) via a consistent style.display="flex"/"none" toggle -- confirmed by
     grep before writing this -- so rather than requiring every call site to be touched, this
     watches the container's own style attribute with a MutationObserver and reacts to the
     none<->flex transition itself. Call once per modal container after the page defines it
     (idempotent per element -- each call attaches its own observer+listener scoped to that one
     element, so wiring multiple modals never cross-interferes). No-op (never throws) on a browser
     without MutationObserver, or if the id/element isn't found. */
  /* v1.45 (a11y extension): generalized to also cover modals toggled by classList rather than inline
     style.display -- schematics.html and threed.html's own gate modals use the CSS rule
     .gate.on { display:flex } (classList.add/remove('on')), never touching the inline style property
     at all. The original isVisible()/attributeFilter only watched the inline style property, so
     attaching trapFocus to either page as-is would silently never fire onShow()/onHide() -- no error,
     no visible breakage, just a modal that never traps focus. getComputedStyle().display is toggle-
     mechanism-agnostic (works for both inline-style and classList-driven display), and watching both
     the "style" and "class" HTML attributes via the MutationObserver's attributeFilter covers every
     real pattern in this codebase without requiring index.html's 5 existing call sites (or any future
     modal) to change how they open/close. */
  function trapFocus(idOrEl) {
    var el = typeof idOrEl === "string" ? document.getElementById(idOrEl) : idOrEl;
    if (!el || typeof window.MutationObserver !== "function") return;
    var prevFocus = null;
    function isVisible() { try { return window.getComputedStyle(el).display !== "none"; } catch (e) { return el.style.display !== "none" && el.style.display !== ""; } }
    var wasVisible = isVisible();

    function focusables() {
      var cand = el.querySelectorAll('a[href],button,input,select,textarea,[tabindex]');
      var out = [];
      for (var i = 0; i < cand.length; i++) {
        if (!cand[i].disabled && cand[i].getAttribute("tabindex") !== "-1" && cand[i].offsetParent !== null) {
          out.push(cand[i]);
        }
      }
      return out;
    }

    function onShow() {
      prevFocus = document.activeElement;
      var f = focusables();
      if (f.length) { try { f[0].focus(); } catch (e) { /* ignore */ } }
    }
    function onHide() {
      if (prevFocus && prevFocus.focus) { try { prevFocus.focus(); } catch (e) { /* ignore */ } }
      prevFocus = null;
    }

    try {
      new MutationObserver(function () {
        var v = isVisible();
        if (v && !wasVisible) onShow();
        else if (!v && wasVisible) onHide();
        wasVisible = v;
      }).observe(el, { attributes: true, attributeFilter: ["style", "class"] });
    } catch (e) { /* never break the host page over a11y wiring */ }

    el.addEventListener("keydown", function (e) {
      if (!isVisible()) return;
      if (e.key === "Escape") {
        /* Two real close conventions exist in this codebase: index.html's 5 modals set inline
           style.display="none" directly at every close call site; schematics.html/threed.html's gate
           toggles its "on" classList entry instead (via the .gate.on { display:flex } rule) and never
           touches inline style. Detect which one this element uses and close the same way, so
           re-opening afterward isn't broken by a stale inline style fighting that CSS rule. Harmless
           no-op if the page's own Escape handler (both gate pages already have one) races this and
           closes it first. */
        e.preventDefault();
        if (el.style.display && el.style.display !== "") { el.style.display = "none"; }
        else if (el.classList.contains("on")) { el.classList.remove("on"); }
        return;
      }
      if (e.key !== "Tab") return;
      var f = focusables();
      if (!f.length) { e.preventDefault(); return; }
      var first = f[0], last = f[f.length - 1], act = document.activeElement;
      if (e.shiftKey) { if (act === first || !el.contains(act)) { e.preventDefault(); last.focus(); } }
      else { if (act === last || !el.contains(act)) { e.preventDefault(); first.focus(); } }
    });
  }

  var VW = { esc: esc, $: $, $all: $all, getJSON: getJSON, postJSON: postJSON,
             toast: toast, debounce: debounce, fmtInt: fmtInt, kioskOn: kioskOn, confTier: confTier,
             trapFocus: trapFocus };
  g.VW = VW;
  /* Back-compat: expose the classic names only when the page doesn't define its own. */
  if (g.esc === undefined) g.esc = esc;
  if (g.toast === undefined) g.toast = toast;
  if (g.viewerKioskOn === undefined) g.viewerKioskOn = kioskOn;
}(typeof window !== "undefined" ? window : this));
