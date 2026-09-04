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

  /* v1.51.0: VW.channel -- cross-window/cross-tab publish/subscribe (multi-window support, stage 1
     of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md). BroadcastChannel is the primary
     transport (near-instant, no practical payload limit, delivered in order per channel by the
     browser itself, and never echoes back to the tab that sent it); the native storage event is
     the automatic fallback for the older/RPS-mode browsers this codebase still supports, where
     BroadcastChannel is undefined (also never echoes to the writing tab, per spec). A subscriber
     never needs to know or care which transport is active -- both paths deliver the identical
     envelope shape.

     Every message is wrapped in an envelope carrying:
       v     -- a schema version (bumped only if this envelope SHAPE itself ever changes), so a tab
                running older/newer code can detect a mismatch and ignore the message cleanly instead
                of crashing on an unexpected shape.
       tabId -- a random id generated once per tab/window load.
       seq   -- a counter, PER (channel name, tabId), incremented on every publish() this tab makes
                to that channel. This is deliberately NOT a global cross-tab sequence -- no single
                source of truth exists for that without real coordination overkill for what this
                needs -- it lets a subscriber detect it may have missed a message from THIS SPECIFIC
                OTHER TAB (seq jumps by more than 1). That matters most on the storage-event fallback
                path: two rapid writes to the same localStorage key from one tab can coalesce into a
                single storage event in another tab, since the event only ever reflects the CURRENT
                value at dispatch time, not a queue of every value that was ever written.

     The storage-event fallback path writes every channel's envelope to ONE shared localStorage key
     (multiple logical channels multiplex over it; subscribe() filters by name), and guards against
     oversized payloads explicitly: BroadcastChannel has no meaningful size limit, but localStorage
     shares a single ~5-10MB origin-wide quota with everything else already stored there -- publish()
     throws a clear, immediate error on an oversized payload on this path rather than letting a raw
     QuotaExceededError (or a partially-written shared key) surface somewhere downstream instead. */
  var _CHANNEL_V = 1;
  var _CHANNEL_KEY = "viewer_channel_msg";
  var _CHANNEL_MAX_BYTES = 200000;    // a safety margin, not the real browser quota -- this fires
                                       // with a clear message long before an actual QuotaExceededError would.
  var _channelTabId = Math.random().toString(36).slice(2) + Date.now().toString(36);
  var _channelSeq = {};        // "<name>" -> last seq THIS tab has sent on that channel
  var _channelLastSeen = {};   // "<name>:<tabId>" -> last seq seen FROM that tab on that channel
  var _channelSubs = {};       // "<name>" -> list of subscriber functions
  var _bcChannels = {};        // "<name>" -> BroadcastChannel instance (or null if unavailable/failed)

  function _channelEnvelope(name, data) {
    _channelSeq[name] = (_channelSeq[name] || 0) + 1;
    return { v: _CHANNEL_V, name: name, tabId: _channelTabId, seq: _channelSeq[name], data: data };
  }

  function _channelDeliver(env) {
    if (!env || env.v !== _CHANNEL_V) return;               // unknown/mismatched schema -- ignore, never throw
    var subs = _channelSubs[env.name];
    if (!subs || !subs.length) return;
    var key = env.name + ":" + env.tabId;
    var last = _channelLastSeen[key];
    var gap = (last !== undefined && env.seq > last + 1);    // true -> this tab may have missed one or more messages
    _channelLastSeen[key] = env.seq;
    var meta = { seq: env.seq, v: env.v, gap: gap };
    for (var i = 0; i < subs.length; i++) {
      try { subs[i](env.data, meta); } catch (e) { /* one bad subscriber must never break the rest */ }
    }
  }

  /* One listener, registered once, covers every channel multiplexed over the single fallback key. */
  try {
    if (typeof window !== "undefined" && window.addEventListener) {
      window.addEventListener("storage", function (ev) {
        if (!ev || ev.key !== _CHANNEL_KEY || !ev.newValue) return;
        var env = null;
        try { env = JSON.parse(ev.newValue); } catch (e) { return; }
        _channelDeliver(env);
      });
    }
  } catch (e) { /* never break the host page over channel wiring */ }

  /* Lazily creates (and wires up) the BroadcastChannel for a channel name, idempotently -- called from both
     publish() and subscribe(), whichever happens first for a given channel name. */
  function _channelEnsureBC(name) {
    if (typeof BroadcastChannel !== "function") return null;
    if (_bcChannels[name] === undefined) {
      try {
        var bc = new BroadcastChannel("viewer:" + name);
        bc.onmessage = function (ev) { _channelDeliver(ev.data); };
        _bcChannels[name] = bc;
      } catch (e) { _bcChannels[name] = null; }
    }
    return _bcChannels[name];
  }

  function channelPublish(name, data) {
    var env = _channelEnvelope(name, data);
    var bc = _channelEnsureBC(name);
    if (bc) { bc.postMessage(env); return; }
    var json = JSON.stringify(env);
    if (json.length > _CHANNEL_MAX_BYTES) {
      throw new Error("VW.channel.publish('" + name + "'): payload too large for the storage-event " +
        "fallback (" + json.length + " bytes, limit " + _CHANNEL_MAX_BYTES + "). BroadcastChannel " +
        "isn't available in this browser, and localStorage shares one small origin-wide quota with " +
        "everything else already stored there.");
    }
    try { window.localStorage.setItem(_CHANNEL_KEY, json); }
    catch (e) { /* quota exceeded or private-mode storage disabled -- best effort, never throw from here */ }
  }

  function channelSubscribe(name, fn) {
    if (!_channelSubs[name]) _channelSubs[name] = [];
    _channelSubs[name].push(fn);
    _channelEnsureBC(name);    // make sure this channel has a live BroadcastChannel listener too
  }

  /* v1.52.0: VW.workspace -- saved, named sets of pages (stage 2 of
     docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, PR 2 of 18). A workspace is the
     data behind "reopen everything I had open for this job": a name plus an ordered list of
     {page, params} entries. This PR is CRUD only -- export/import (PR 3) and the built-in
     templates (PR 4) build on exactly this record shape and this storage key, and are deliberately
     not here.

     Record shape, straight from the design spec:
       { id, name, items: [{page, params}], created, lastOpened, source: "manual" or "template" }

     STORAGE SHAPE (a real decision, documented rather than left implicit): the whole set is one
     JSON ARRAY under the single localStorage key "viewer_workspaces", not an id-keyed object.
     Reasons, in order of weight:
       1. list() is by far the dominant read -- the saved-workspaces UI this exists to feed
          repaints the entire set whenever anything changes -- and an array preserves a real,
          stable creation order for free. An id-keyed object would need a sort on every list() to
          get the same guarantee, since object key iteration order is not worth depending on.
       2. get(id) becomes a linear scan, which is the right trade here: this set is a handful of
          entries a person typed names for, not thousands of machine-generated rows.
       3. An array is already the exact shape PR 3 will serialize for export/import, so nothing
          has to be reshaped at that boundary.

     WHY EVERY MUTATION PUBLISHES ON VW.channel, and why the payload is deliberately thin:
     localStorage is already shared across every tab on this origin, for free -- a second tab does
     not need the workspace data pushed to it, it needs to be TOLD that something changed so it can
     re-read and repaint. That is the same philosophy the design spec describes for D (Bench sync):
     the channel is a notification layer over storage that is already shared, never a second copy
     of the truth. So the payload carries only {action, id, name, at} -- enough for a receiving UI
     to repaint from its own list() or to highlight the one row that moved, small enough that the
     channel's storage-event fallback size guard can never fire on it, and incapable of going stale
     against the real stored value. The write happens FIRST and the notification second, so a tab
     reacting to a notification always reads an already-committed value.

     Read-only calls (list/get) touch localStorage directly and publish nothing -- there is nothing
     for another tab to react to, and a read that broadcasts would be a live-lock waiting to happen
     the moment a subscriber repaints by calling list(). */
  var _WS_KEY = "viewer_workspaces";
  var _WS_CHANNEL = "workspace";

  /* Reads the whole saved set, defensively. Always returns an array -- never null, never throws:
     plain localStorage access itself throws in private-browsing modes, and the stored value could
     be anything at all if it was hand-edited in devtools or written by a future/older build.
     Entries that do not look like a workspace record (a non-null object carrying a string id) are
     dropped from the RETURNED VIEW only. A read deliberately never rewrites storage, so a corrupt
     value stays inspectable instead of being silently destroyed by the act of looking at it; the
     next successful write does drop those entries for good, which is the correct outcome since
     they were unusable either way. */
  function _wsRead() {
    var raw = null;
    try { raw = window.localStorage.getItem(_WS_KEY); } catch (e) { return []; }
    if (!raw) return [];
    var parsed = null;
    try { parsed = JSON.parse(raw); } catch (e) { return []; }
    if (!parsed || Object.prototype.toString.call(parsed) !== "[object Array]") return [];
    var out = [];
    for (var i = 0; i < parsed.length; i++) {
      var w = parsed[i];
      if (w && typeof w === "object" && typeof w.id === "string") out.push(w);
    }
    return out;
  }

  /* Writes the whole set back. Returns true on success, false when storage refused the write (a
     private-browsing profile, or a full origin quota). A caller must never treat false as
     "probably fine": create() reports it upward as a null id rather than handing back an id for a
     workspace that was never actually stored, which is the difference between a UI that can say
     "couldn't save that" and one that lies. */
  function _wsWrite(all) {
    try { window.localStorage.setItem(_WS_KEY, JSON.stringify(all)); return true; }
    catch (e) { return false; }
  }

  /* Ids only ever need to be unique within ONE browser profile's own storage: they are never sent
     anywhere and never merged with another machine's set (PR 3's import will mint a fresh id
     rather than trusting an incoming one). A base-36 timestamp plus 6 random base-36 characters is
     therefore plenty -- the timestamp separates any two creations more than a millisecond apart,
     the suffix covers two within the same millisecond. Rather than leave that as a probability
     argument, _wsNewId checks the ids actually stored and regenerates on a hit, so a duplicate is
     impossible rather than merely unlikely, with a bounded loop and a deterministic final fallback
     so a pathological environment (a stubbed Math.random, say) can neither spin forever nor return
     an id that is already taken. */
  function _wsRandomId() {
    var r = Math.random().toString(36).slice(2, 8);
    while (r.length < 6) { r = r + "0"; }
    return "ws" + Date.now().toString(36) + r;
  }
  function _wsNewId(all) {
    for (var attempt = 0; attempt < 50; attempt++) {
      var id = _wsRandomId();
      var taken = false;
      for (var i = 0; i < all.length; i++) {
        if (all[i].id === id) { taken = true; break; }
      }
      if (!taken) return id;
    }
    return _wsRandomId() + "-" + all.length;
  }

  /* Normalizes an incoming items array into exactly the {page, params} shape the design spec
     names, so a stored workspace can never carry a surprise -- a function, a DOM node, an
     undefined -- that would either vanish through JSON.stringify or come back as garbage on the
     next read. An entry with no usable page string is dropped rather than stored broken. Param
     values are coerced to strings because every real consumer of them builds a URL query string
     (PR 3's exportUrl, and VW.windows.open's URL assembly later), so doing it once here makes the
     stored value match what actually gets used, and makes the JSON round-trip lossless. */
  function _wsItems(items) {
    var out = [];
    if (!items || typeof items.length !== "number") return out;
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (!it || typeof it !== "object") continue;
      var page = (it.page === null || it.page === undefined) ? "" : String(it.page);
      if (!page) continue;
      var params = {};
      var src = (it.params && typeof it.params === "object") ? it.params : {};
      for (var k in src) {
        if (!Object.prototype.hasOwnProperty.call(src, k)) continue;
        var v = src[k];
        if (v === null || v === undefined || typeof v === "function") continue;
        params[k] = String(v);
      }
      out.push({ page: page, params: params });
    }
    return out;
  }

  /* The notification half of every mutation. Wrapped because the write it follows has ALREADY
     committed: a failure here (channelPublish throws by design on an oversized storage-fallback
     payload, and any transport can be missing in a hostile environment) must never turn a saved
     workspace into a reported failure. */
  function _wsNotify(action, ws) {
    try {
      channelPublish(_WS_CHANNEL, { action: action, id: ws.id, name: ws.name, at: ws.lastOpened });
    } catch (e) { /* the data is safely stored; a missed repaint hint is not worth failing over */ }
  }

  /* create(name, items) -> id, or null if storage refused the write.
     The third argument is the record's "source" field, defaulting to "manual" and accepting only
     "template" as the alternative. It exists now, rather than being bolted on in PR 4, because the
     design spec's record shape carries "source" from the start -- without it this function could
     only ever write "manual" and the field would be a constant with a misleading name. */
  function workspaceCreate(name, items, source) {
    var all = _wsRead();
    var now = Date.now();
    var nm = (name === null || name === undefined) ? "" : String(name);
    var ws = {
      id: _wsNewId(all),
      name: nm === "" ? "Untitled workspace" : nm,
      items: _wsItems(items),
      created: now,
      /* Equal to created on purpose: a never-reopened workspace then sorts sanely against its
         siblings by lastOpened alone, with no null handling in every consumer, and "never reopened
         since it was made" stays detectable as lastOpened === created. */
      lastOpened: now,
      source: source === "template" ? "template" : "manual"
    };
    all.push(ws);
    if (!_wsWrite(all)) return null;
    _wsNotify("create", ws);
    return ws.id;
  }

  /* list() -> array of workspace records in creation order (oldest first), newest appended last.
     Every call re-parses storage, so the returned records are fresh copies -- a caller mutating
     what it gets back cannot corrupt what is stored, and cannot hold a stale view across another
     tab's write either. A UI wanting most-recently-opened order sorts by lastOpened itself. */
  function workspaceList() { return _wsRead(); }

  /* get(id) -> the workspace record, or null when no such id is stored. */
  function workspaceGet(id) {
    if (id === null || id === undefined) return null;
    var want = String(id);
    var all = _wsRead();
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === want) return all[i];
    }
    return null;
  }

  /* touch(id) -> true when it updated lastOpened, false when the id is not stored (so a caller can
     tell a stale id from a real one) or when storage refused the write. Only lastOpened moves --
     created, name, items and source are left exactly as they were. */
  function workspaceTouch(id) {
    if (id === null || id === undefined) return false;
    var want = String(id);
    var all = _wsRead();
    var hit = null;
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === want) { hit = all[i]; break; }
    }
    if (!hit) return false;
    hit.lastOpened = Date.now();
    if (!_wsWrite(all)) return false;
    _wsNotify("touch", hit);
    return true;
  }

  /* v1.53.0: VW.windows -- the one shared window-opening path for this app (multi-window support,
     PR 5 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 2, riding VW.channel
     above).

     WHY this exists when window.open() is already one line: passing the same SECOND argument (the
     window name) twice is how a browser natively reuses a window instead of stacking up a fresh one
     per click. That behavior is free, and it is also the thing every call site forgets, because
     nothing about writing window.open(url) suggests you were supposed to name anything. A technician
     who taps the same "pop out the torque table" affordance four times across one job ends up with
     four identical windows fighting over the second monitor. Making the named form the ERGONOMIC
     DEFAULT -- a caller passes opts.name once and never thinks about reuse again -- is the point, and
     three things are layered on top that a bare window.open() call site could not sensibly do for
     itself:

       1. A registry. This tab remembers what it opened, keyed by name, so registry() can report it,
          and so a later PR can record and restore each window's real screen position (PR 6, which is
          deliberately NOT part of this one).
       2. A broadcast. Every successful open publishes an event on the "windows" channel, so a future
          feature can show a live "N windows open" across every tab with no tab polling anything.
          This PR builds that plumbing only; nothing renders it yet.
       3. A toast, fired the instant a window opens or is refocused. Design priority 2 of the spec is
          a snappy UI, and the worst case for a pop-out control is precisely the reuse case: on some
          window managers the reused window comes forward behind the current one, so the click looks
          like it did nothing at all. An immediate toast makes every click visibly register, whether
          a new window appeared or an existing one was reused.

     Honest limits of the registry, stated here rather than discovered later:
       - It is per tab, in memory. It lists what THIS tab opened during THIS page load -- not every
         VIEWER window on the machine. Another tab's opens, and this tab's own opens from before a
         reload, are simply not in it. That is exactly why each open is broadcast: a cross-tab view
         has to be assembled from the messages, never read off one tab's registry.
       - It is a best-effort mirror of the browser's own named-window table, not the truth. The
         browser reuses a named window whether or not this registry knows about it (the window this
         tab opened before its own reload is still out there under that name, and will still be
         reused), so after a reload a reuse can be reported as a fresh open. Entries whose handle
         reports closed === true are pruned on every registry() call and before every reuse decision,
         which covers the common case -- the user closed the pop-out -- exactly.

     Without opts.name there is no reuse and no tracking, and that is a property of the platform, not
     a shortcut taken here: an unnamed window.open() returns a fresh anonymous window on every single
     call, no key exists to store it under, and nothing can ever look it up again. Such a call still
     opens the window and still toasts (a click must always visibly register), it just never appears
     in registry(). Pass a name whenever a repeat click should land on the window already open.

     No window-features argument is passed on this path, on purpose: supplying one turns what the
     browser would have opened as an ordinary tab into a stripped chrome-less popup, overriding the
     user's own new-window preference. PR 6's restoreLayout() is the one place that will legitimately
     pass explicit bounds, because there the user asked for exactly that.

     Popup blockers: every intended call site is a real click handler and browsers permit
     user-gesture-initiated opens, so a block should never happen in practice. It is still handled,
     because window.open() returns null when it does happen and can throw outright in a locked-down
     configuration: open() returns null, and the toast, the registry write and the broadcast are all
     skipped, since none of them may claim a window opened when none did. */
  var _WINDOWS_CHANNEL = "windows";
  var _winReg = {};    // name -> {name: name, url: url, win: window handle}

  /* Drops every entry whose window has since been closed. window.closed is readable across
     same-origin windows and stays readable after the close, so this is a real check rather than a
     guess. A handle that throws on property access (a rare torn-down state) counts as closed instead
     of being allowed to break the caller. */
  function _winPrune() {
    var name, w, dead;
    for (name in _winReg) {
      if (!Object.prototype.hasOwnProperty.call(_winReg, name)) continue;
      w = _winReg[name].win;
      try { dead = !w || w.closed === true; } catch (e) { dead = true; }
      if (dead) delete _winReg[name];
    }
  }

  /* Currently-tracked open windows THIS tab opened, newly-built plain objects each call, so a caller
     can never reach in and corrupt the registry by mutating what it was handed. */
  function windowsRegistry() {
    _winPrune();
    var out = [], name;
    for (name in _winReg) {
      if (!Object.prototype.hasOwnProperty.call(_winReg, name)) continue;
      out.push({ name: _winReg[name].name, url: _winReg[name].url });
    }
    return out;
  }

  function windowsOpen(url, opts) {
    var o = opts || {};
    var name = (typeof o.name === "string" && o.name) ? o.name : null;
    _winPrune();                       // a window the user closed must not be reported as reused
    var reused = !!(name && _winReg[name]);
    var win = null;
    /* Always really call window.open, reuse or not: the reuse, the navigation to a possibly-new url,
       and the raise-to-front are all things the BROWSER does in response to this call. Skipping it
       because the registry already knows the name would leave the existing window untouched and
       still sitting behind whatever is in front of it. */
    try { win = name ? window.open(url, name) : window.open(url); }
    catch (e) { win = null; }
    if (!win) return null;             // blocked or refused -- claim nothing, break nothing
    try { if (win.focus) win.focus(); } catch (e) { /* some window managers refuse this; harmless */ }
    if (name) _winReg[name] = { name: name, url: url, win: win };
    /* Feedback and bookkeeping must never take down a window that already opened successfully. */
    try {
      toast(reused ? "Already open — switched to that window" : "Opened in a new window");
    } catch (e) { /* a page with no body yet, etc. */ }
    try {
      channelPublish(_WINDOWS_CHANNEL, { event: reused ? "reuse" : "open", name: name, url: url,
        count: windowsRegistry().length });   // count is named/tracked windows only, see above
    } catch (e) { /* a broadcast failure must never surface to the user who just opened a window */ }
    return win;
  }

  /* v1.56.0: VW.bench -- the ONE canonical accessor for "My Bench", the technician's pinned list of
     parts, procedures and pages (multi-window support, PR 13 of
     docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 4, feature D). Rides
     VW.channel above, exactly the way VW.workspace does.

     WHY THIS MOVED HERE. The same two-line read/write pair had been written out twice,
     independently: once inline in bench.html (the page that renders the list) and once in palette.js
     (the pill that pins the current page). Both parsed the same "viewer_bench" key, both re-applied
     the same 100-entry cap, and neither knew the other existed -- so a change to the cap, or to how
     a corrupt stored value is handled, had to be made in two places or silently drift apart. That is
     the exact situation shared.js itself was created for, and the same promotion the two PRs before
     this one (VW.workspace, VW.windows) already established for this initiative.

     WHY EVERY WRITE PUBLISHES ON VW.channel, AND WHY THE PAYLOAD IS DELIBERATELY THIN. localStorage
     is already shared across every tab on this origin for free -- a second tab does not need the
     bench list pushed to it, it needs to be TOLD something changed so it can re-read and repaint.
     The channel is a notification layer over storage that is already shared, never a second copy of
     the truth. So put() publishes only {action, count, at}: enough for an open /bench tab to know it
     should repaint, small enough that the channel's storage-event fallback size guard can never fire
     on it, and incapable of going stale against the real stored value, since a receiver always
     re-reads. The write happens FIRST and the notification second, so a tab reacting to a
     notification always reads an already-committed value. get() publishes nothing -- there is
     nothing for another tab to react to, and a read that broadcast would be a live-lock waiting to
     happen the moment a subscriber repaints by calling get().

     CONFLICTS ARE LAST-WRITE-WINS, WITH NO MERGE -- decided early in this initiative's scoping and
     unchanged since. Two tabs writing the bench in the same instant leave the second write standing,
     whole. No merge is attempted, on purpose: the bench is a short, human-curated list a person
     edits deliberately one row at a time, not a shared document with concurrent editors, so merging
     would trade a rare and immediately-visible surprise (a pin that has to be added again) for a
     permanent family of subtle ones (rows the user explicitly removed quietly coming back). Because
     every write notifies, the losing tab repaints from storage within a frame instead of sitting on
     a list that no longer exists.

     The 100-entry cap and the stored record shape are carried over UNCHANGED from bench.html's own
     copy. Newest entries sit at the HEAD of the array (palette.js unshifts each new pin), so the cap
     keeps the 100 most recent and drops the oldest, which is the behavior that was already there. */
  var _BENCH_KEY = "viewer_bench";
  var _BENCH_MAX = 100;
  var _BENCH_CHANNEL = "bench";

  /* get() -> the pinned list, always an array: never null, never a throw. Plain localStorage access
     itself throws in a private-browsing profile, and the stored value could be anything at all if it
     was hand-edited in devtools or written by a future build. Anything that is not a JSON array
     reads as an empty bench rather than being handed to a caller that will immediately call .length
     or .filter on it -- palette.js's pin path did exactly that, so a stored JSON object used to make
     a pin fail silently. Entries that are not objects are dropped from the RETURNED VIEW only, the
     same way VW.workspace's own read filters its records; a read deliberately never rewrites
     storage, so a corrupt value stays inspectable in devtools instead of being destroyed by the act
     of looking at it, and the next put() clears it for good, which is the correct outcome since it
     was unusable either way. */
  function benchGet() {
    var raw = null;
    try { raw = window.localStorage.getItem(_BENCH_KEY); } catch (e) { return []; }
    if (!raw) return [];
    var parsed = null;
    try { parsed = JSON.parse(raw); } catch (e) { return []; }
    if (!parsed || Object.prototype.toString.call(parsed) !== "[object Array]") return [];
    var out = [];
    for (var i = 0; i < parsed.length; i++) {
      if (parsed[i] && typeof parsed[i] === "object") out.push(parsed[i]);
    }
    return out;
  }

  /* put(list) -> true when the list was really stored, false when it was not: a non-array argument,
     or storage refusing the write in a private-browsing profile or on a full origin quota. The
     boolean return is new -- bench.html's original put() returned nothing -- and it is here for the
     same reason VW.workspace.create() reports a refused write instead of handing back a
     plausible-looking id: a caller that cannot tell a stored bench from an unstored one can only
     ever lie to the user about it. Nothing at all is written for a non-array argument, which matches
     the old behavior exactly (the old copy called .slice on it, threw, and swallowed that in its own
     try/catch, so nothing was stored either way). Entries themselves are stored verbatim: this is
     the one canonical accessor for a shape other code owns, not a validator of it. */
  function benchPut(list) {
    if (Object.prototype.toString.call(list) !== "[object Array]") return false;
    var capped = list.slice(0, _BENCH_MAX);
    try { window.localStorage.setItem(_BENCH_KEY, JSON.stringify(capped)); }
    catch (e) { return false; }
    /* Wrapped because the write above has ALREADY committed: channelPublish throws by design on an
       oversized storage-fallback payload, and any transport can be missing in a hostile environment.
       A failure to hint at a repaint must never turn a saved bench into a reported failure. */
    try {
      channelPublish(_BENCH_CHANNEL, { action: "put", count: capped.length, at: Date.now() });
    } catch (e) { /* the list is safely stored; a missed repaint hint is not worth failing over */ }
    return true;
  }

  var VW = { esc: esc, $: $, $all: $all, getJSON: getJSON, postJSON: postJSON,
             toast: toast, debounce: debounce, fmtInt: fmtInt, kioskOn: kioskOn, confTier: confTier,
             trapFocus: trapFocus,
             channel: { publish: channelPublish, subscribe: channelSubscribe },
             workspace: { create: workspaceCreate, list: workspaceList,
                          get: workspaceGet, touch: workspaceTouch },
             windows: { open: windowsOpen, registry: windowsRegistry },
             bench: { get: benchGet, put: benchPut } };
  g.VW = VW;
  /* Back-compat: expose the classic names only when the page doesn't define its own. */
  if (g.esc === undefined) g.esc = esc;
  if (g.toast === undefined) g.toast = toast;
  if (g.viewerKioskOn === undefined) g.viewerKioskOn = kioskOn;
}(typeof window !== "undefined" ? window : this));
