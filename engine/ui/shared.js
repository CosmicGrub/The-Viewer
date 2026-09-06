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
     {page, params} entries. This original PR was CRUD only; v1.65.0 (PR 3 of 18) adds
     exportUrl/exportFile/importUrl/importFile directly below the CRUD functions, on exactly this
     same record shape and storage key. The built-in templates (PR 4) are still a later addition.

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
  /* v1.75.0: shape-coerces ANY parsed value -- a JSON.parse() result from localStorage, or a raw
     structured-clone value read back out of IndexedDB (see the IndexedDB-backing block below) --
     into a real workspace-record array: non-array input becomes [], and any entry that is not a
     plain object carrying a string id is dropped from the returned view. Pulled out of _wsRead()
     below so both storage backings share this exact rule rather than each keeping its own copy. */
  function _wsCoerceAll(parsed) {
    if (!parsed || Object.prototype.toString.call(parsed) !== "[object Array]") return [];
    var out = [];
    for (var i = 0; i < parsed.length; i++) {
      var w = parsed[i];
      if (w && typeof w === "object" && typeof w.id === "string") out.push(w);
    }
    return out;
  }

  /* v1.76.0: set by every _wsRead() call -- true when the raw stored value needed _wsCoerceAll()
     to silently drop something (corrupt/hostile storage: a non-array value, or an array with junk
     entries mixed in) to produce the array actually returned; false for a clean read. Read by
     _wsAllForRead() below so a SCHEMA-MIGRATION write-back (a new v1.76.0 behavior) never also
     doubles as a silent junk cleanup on a mere read -- preserving this file's original, deliberate
     "a read never rewrites storage" guarantee for corrupt/hostile values (see _wsRead()'s own
     long-standing comment above) even though a migration stamp on an otherwise-valid record now
     does get written back on a genuinely CLEAN read. A junk-mixed read still migrates the valid
     record in memory for THIS call's own return value -- only the durable write-back is deferred,
     to whichever real mutation (create/touch/delete, which already commits unconditionally) or
     later clean read completes it; nothing here ever produces a wrong answer, only a deferred one. */
  var _wsLastReadHadJunk = false;

  function _wsRead() {
    var raw = null;
    try { raw = window.localStorage.getItem(_WS_KEY); } catch (e) { _wsLastReadHadJunk = false; return []; }
    if (!raw) { _wsLastReadHadJunk = false; return []; }
    var parsed = null;
    try { parsed = JSON.parse(raw); } catch (e) { _wsLastReadHadJunk = false; return []; }
    var coerced = _wsCoerceAll(parsed);
    _wsLastReadHadJunk = !(Object.prototype.toString.call(parsed) === "[object Array]" &&
      parsed.length === coerced.length);
    return coerced;
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
     anywhere and never merged with another machine's set (importUrl/importFile below mint a fresh
     id via this same path rather than trusting one that might arrive in an imported payload). A
     base-36 timestamp plus 6 random base-36 characters is
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

  /* v1.75.0: IndexedDB-backed storage for VW.workspace (multi-window support, PR 21 of
     docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). Depends on PR 19's
     VW.capabilities.indexedDB and PR 2's CRUD above -- "swaps the storage backing PR 2 built
     (localStorage under viewer_workspaces) for IndexedDB, keeping create/list/get/touch's public
     contract byte-for-byte identical" (the plan doc's own words). On lite/legacy tier, or wherever
     the raw API is missing, nothing below this comment ever runs -- every mutation still goes
     straight to _wsRead()/_wsWrite() exactly as PR 2 wrote it, which is "the original localStorage
     path" the plan explicitly keeps for constrained hardware.

     THE UNAVOIDABLE PROBLEM: IndexedDB has no synchronous read or write anywhere -- every operation
     is callback/event-based (IDBRequest.onsuccess/onerror). create/list/get/touch/delete are called
     synchronously by every existing page today (workspaces.html's list render, jobcard.html/
     solve.html's launch buttons, palette.js) and per the plan's own text none of them may be made to
     start handling a Promise or a callback in this PR. A function cannot read or write IndexedDB and
     return a real value on the same synchronous call -- so this cannot be "the same functions, but
     now reading IndexedDB instead of localStorage"; it has to be a synchronous cache with IndexedDB
     underneath it.

     THE RESOLUTION -- a synchronous in-memory array (_wsCache), bootstrapped instantly and
     losslessly from a plain _wsRead() (localStorage is already synchronous, so this genuinely
     cannot be stale at the moment it runs), with IndexedDB reconciled in afterward, fully
     asynchronously, never delaying or blocking the call that triggered the bootstrap:

       1. _wsEnsureCache() runs on the FIRST workspace call this page ever makes (create/list/get/
          touch/delete/export/import all funnel through _wsAllForRead()/_wsAllForMutation() below,
          which call it). If _wsCache is still null, it is set to _wsRead()'s result right there,
          synchronously, before anything else happens -- so even the very first call a page ever
          makes sees a result that really did come from a valid read, never a placeholder.
       2. Immediately after that synchronous assignment, _wsIdbReconcile() fires -- fire-and-forget;
          its own callbacks never block or delay the return already in flight above:
            - IndexedDB already holds records (a prior session's own migration already ran) ->
              IndexedDB is the durable, authoritative store from here on; _wsCache is replaced
              wholesale with what IndexedDB actually holds.
            - IndexedDB reads back empty (first time on this browser profile) -> a ONE-TIME
              migration: _wsCache (the localStorage-sourced bootstrap value) is written into
              IndexedDB as-is. localStorage's own key is deliberately left untouched afterward,
              never cleared -- a frozen, unread backup costs nothing to leave in place, and clearing
              it would turn a hypothetical future rollback of this PR into a full data loss instead
              of "reads the last-known-good copy again".
       3. From that point on, every mutation updates _wsCache synchronously (the calling tab always
          sees an instantly-consistent result, matching today's behavior exactly) and fires an async,
          best-effort write-through to IndexedDB (_wsIdbPersist below) to make it durable. Once a page
          is on this path it never also writes to localStorage again -- only the original one-time
          bootstrap read from localStorage ever happens, by design, which is exactly what lets a
          payload too big for localStorage's own quota succeed here (see this PR's large-payload
          test).
       4. Any IndexedDB failure (open blocked/denied, a thrown exception, a failed transaction)
          degrades silently at the PERSISTENCE layer only -- _wsCache stays authoritative and every
          synchronous caller keeps working whether or not the background durability write actually
          landed. See _wsIdbNoteFailure() below for the one deliberate exception: a REPEATED failure
          streak gets a single one-time toast, on this file's own "fail loud enough to be seen, never
          silently misrepresent" R13 discipline (docs/MASTER-RECONCILIATION.md's standing-rules
          table) -- because past that point this tab's workspace data genuinely only lives in memory,
          a real and otherwise-invisible data-loss risk, not merely a transient hiccup that the
          in-memory cache already absorbs without incident.

     WHICH BACKING A PAGE USES IS DECIDED ONCE, AT BOOTSTRAP, NOT RE-CHECKED ON EVERY CALL -- the one
     deliberate departure from "gate on the live capabilities getter" being a per-call re-read
     everywhere else in this file (VW.locks re-reads _capabilities.webLocks on every withLock() call,
     since switching which lock implementation backs one call can never corrupt anything). Workspace
     storage is different: VW.capabilities' own comment documents that its non-tier fields are LIVE
     reads because window.RPS.mode can resolve from its "modern" default to the real tier only after
     this file has already loaded -- so a page's very first workspace call can observe indexedDB
     true, commit a mutation straight into _wsCache, and only later observe indexedDB false once
     RPS.boot() resolves. Re-deriving the backing on every call would then silently strand that
     already-committed cache entry against a resumed _wsRead()/_wsWrite() localStorage path that
     never saw it. _wsUsingIndexedDB() below reads the LIVE getter -- never a hand-rolled second copy
     of its check -- but only until _wsCache is first created; from then on this one page's backing
     choice is latched for the rest of its life, which is the only way "byte-for-byte identical
     contract" can also mean "internally consistent for this whole page load".

     THE ONE REAL LIMITATION THIS DESIGN CANNOT FULLY ELIMINATE, stated plainly rather than glossed
     over (the same honesty this initiative has applied to every other real-hardware/real-timing edge
     case since PR 5): open this app in TWO tabs at once on modern tier, and each tab bootstraps its
     OWN _wsCache from its OWN synchronous localStorage read at whatever moment IT first needs one,
     then reconciles against IndexedDB independently and asynchronously. There is a real, narrow
     window where the two tabs' caches can briefly disagree before both round trips finish -- and this
     PR adds no new cross-tab live-sync mechanism for workspace data to close it. _wsNotify() above
     (PR 2's existing VW.channel broadcast) is UNCHANGED and still fires on every create/touch/delete,
     but a receiving tab's own reconcile may not have settled yet when that notification arrives, so a
     repaint it triggers can still show a stale view for a moment. Deliberately NOT layering a second
     broadcast on top of _wsIdbReconcile()'s own cache replacement/migration step to paper over this:
     a receiving tab has no way to tell "my own reconcile already finished" apart from "it has not",
     so acting on such a broadcast could just as easily paint an intermediate, still-bootstrapping
     view with false confidence as a correct one -- worse than the narrow, self-healing window this
     already is (every later call on that tab, once its own reconcile lands, is correct again). */

  /* The in-memory cache -- null until _wsEnsureCache() bootstraps it; a real array from then on,
     exactly the shape _wsRead() already returns. _wsCacheOnIdb latches, at the moment the cache is
     first created, whether this page is running the IndexedDB-backed path -- see the big comment
     above for why this is a one-time decision rather than a live re-check. */
  var _wsCache = null;
  var _wsCacheOnIdb = false;

  function _wsUsingIndexedDB() {
    if (_wsCache !== null) return _wsCacheOnIdb;
    try { return !!_capabilities.indexedDB; } catch (e) { return false; }
  }

  /* Deep-clones via a JSON round trip -- deliberately the SAME mechanism a fresh localStorage parse
     already produces, so a cache-backed read is indistinguishable from _wsRead()'s own contract:
     returned records are never a live reference into the authoritative array, so a caller mutating
     what it gets back (see the node test's own "mutating a returned record does not corrupt storage"
     check) can never corrupt _wsCache. */
  function _wsCloneAll(all) {
    try { return JSON.parse(JSON.stringify(all)); } catch (e) { return []; }
  }

  /* IndexedDB constants, kept deliberately parallel to the localStorage shape above -- one
     JSON-serializable array holds the whole saved set, now under one fixed key in a "kv"-style
     object store instead of one localStorage key, so _wsCoerceAll() and every id/notify function
     above stay completely unaware of which backing is actually live underneath a given call. */
  var _WS_IDB_NAME = "viewer_workspaces_db";
  var _WS_IDB_STORE = "kv";
  var _WS_IDB_ROW_KEY = "viewer_workspaces";
  var _WS_IDB_VERSION = 1;

  /* The open IndexedDB connection, once reconciliation has produced one -- reused by every later
     write-through so a mutation never has to reopen the database. Stays null forever on a page
     where indexedDB.open() itself failed; _wsIdbPersist() below tries a fresh open on every call in
     that case, since a transient open failure (a blocked upgrade in another tab, say) may well
     succeed the next time. */
  var _wsIdbDb = null;

  /* Opens (creating the "kv" object store on first use) the database backing this cache. cb(db) on
     success, cb(null) on ANY failure -- a thrown open() call, onerror, or onblocked (another tab
     holding a version-change lock). Every failure path here is a reason to give up silently at THIS
     layer only, never to throw into a synchronous caller several frames up. */
  function _wsIdbOpenDb(cb) {
    var req;
    try { req = window.indexedDB.open(_WS_IDB_NAME, _WS_IDB_VERSION); }
    catch (e) { cb(null); return; }
    req.onupgradeneeded = function () {
      try {
        if (!req.result.objectStoreNames.contains(_WS_IDB_STORE)) {
          req.result.createObjectStore(_WS_IDB_STORE);
        }
      } catch (e) { /* a failed store creation surfaces through onerror/onsuccess below either way */ }
    };
    req.onsuccess = function () { cb(req.result || null); };
    req.onerror = function () { cb(null); };
    req.onblocked = function () { cb(null); };
  }

  /* Reads the single stored row back out. cb(array) on a real (possibly empty) read, cb(null) on
     any failure -- null vs. an empty array is exactly how _wsIdbReconcile() below tells "IndexedDB
     could not be read" apart from "IndexedDB was read and genuinely has nothing in it yet". */
  function _wsIdbReadAll(db, cb) {
    try {
      var tx = db.transaction([_WS_IDB_STORE], "readonly");
      var store = tx.objectStore(_WS_IDB_STORE);
      var req = store.get(_WS_IDB_ROW_KEY);
      req.onsuccess = function () { cb(_wsCoerceAll(req.result)); };
      req.onerror = function () { cb(null); };
    } catch (e) { cb(null); }
  }

  /* Writes the whole set back as the single stored row. cb(true) once the transaction has actually
     committed (never merely once put() was called -- oncomplete is the real durability signal),
     cb(false) on any error/abort/thrown exception. */
  function _wsIdbWriteAll(db, all, cb) {
    try {
      var tx = db.transaction([_WS_IDB_STORE], "readwrite");
      tx.objectStore(_WS_IDB_STORE).put(all, _WS_IDB_ROW_KEY);
      tx.oncomplete = function () { cb(true); };
      tx.onerror = function () { cb(false); };
      tx.onabort = function () { cb(false); };
    } catch (e) { cb(false); }
  }

  /* Failure bookkeeping for the one-time toast described in the big comment above. A single
     transient failure stays fully silent -- _wsCache already has every write this tab has made, so
     nothing the technician is doing right now is actually broken by it. Three in a row with no
     successful round trip in between means this tab's workspace data is, for the rest of this page's
     life, only ever going to live in memory -- closing the tab loses everything written since the
     last real success, with no other visible sign of it -- which is exactly the kind of silent
     misrepresentation this file's own R13 discipline exists to rule out. */
  var _wsIdbFailureStreak = 0;
  var _wsIdbFailureToastShown = false;
  var _WS_IDB_FAILURE_TOAST_AT = 3;
  function _wsIdbNoteFailure() {
    _wsIdbFailureStreak++;
    if (_wsIdbFailureStreak < _WS_IDB_FAILURE_TOAST_AT || _wsIdbFailureToastShown) return;
    _wsIdbFailureToastShown = true;
    try {
      toast("Workspace changes are not saving to this browser's long-term storage right now " +
        "— they will be lost if this tab is closed.", 6000);
    } catch (e) { /* the cache still works; a failed toast is not worth failing over */ }
  }
  function _wsIdbNoteSuccess() { _wsIdbFailureStreak = 0; }

  /* Fire-and-forget durability write for one mutation's already-final array. Reuses the cached
     connection when one exists; opens a fresh one otherwise (see _wsIdbDb's own comment above for
     why that retry is worth attempting rather than giving up for the rest of the page's life). */
  function _wsIdbPersist(all) {
    function go(db) {
      if (!db) { _wsIdbNoteFailure(); return; }
      _wsIdbDb = db;
      _wsIdbWriteAll(db, all, function (ok) {
        if (ok) _wsIdbNoteSuccess(); else _wsIdbNoteFailure();
      });
    }
    if (_wsIdbDb) go(_wsIdbDb); else _wsIdbOpenDb(go);
  }

  /* Runs exactly once per page, right after _wsEnsureCache()'s synchronous bootstrap -- see step 2
     of the big comment above for the replace-vs-migrate decision this makes. */
  function _wsIdbReconcile() {
    _wsIdbOpenDb(function (db) {
      if (!db) { _wsIdbNoteFailure(); return; }
      _wsIdbDb = db;
      _wsIdbReadAll(db, function (fromIdb) {
        if (fromIdb === null) { _wsIdbNoteFailure(); return; }
        if (fromIdb.length > 0) {
          _wsCache = fromIdb;
          _wsIdbNoteSuccess();
        } else {
          _wsIdbWriteAll(db, _wsCloneAll(_wsCache), function (ok) {
            if (ok) _wsIdbNoteSuccess(); else _wsIdbNoteFailure();
          });
        }
      });
    });
  }

  /* Bootstraps _wsCache on the first call that ever needs it (see step 1 of the big comment above);
     a no-op on every later call. */
  function _wsEnsureCache() {
    if (_wsCache !== null) return _wsCache;
    _wsCacheOnIdb = _wsUsingIndexedDB();
    _wsCache = _wsRead();
    if (_wsCacheOnIdb) _wsIdbReconcile();
    return _wsCache;
  }

  /* v1.76.0: VW.workspace schema versioning -- migrate-on-read or clean refusal (multi-window
     support, PR 22 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6).
     Depends on PR 2's CRUD above and applies at THIS chokepoint deliberately -- explicitly
     INDEPENDENT of PR 21's IndexedDB work immediately above: this logic runs identically no matter
     which backing (_wsRead()/_wsWrite(), or the _wsCache/_wsIdb* pair) is actually live for this
     page, because both ultimately store the exact same JSON-serializable record array and both
     already funnel through _wsAllForRead()/_wsAllForMutation()/_wsCommit() below -- the one shared
     place every CRUD/export/import function already goes through, so migration logic lives here
     exactly once rather than being duplicated into workspaceList()/workspaceGet()/etc. separately.

     THE THREE CASES the design spec's own edge case ("a saved workspace's schemaVersion is older
     than the running code understands: migrated on read where a safe migration path exists,
     refused with a clear message, never silently misinterpreted, where it doesn't") and this PR's
     plan entry name:

       - MISSING entirely -- every record this codebase has EVER written before this PR shipped
         (PR 2 through PR 21 never stamped schemaVersion at all, so this is the overwhelmingly
         common real case, not a hypothetical one): a trivially SAFE migration, since the record
         shape itself has not otherwise changed underneath it -- treated as pre-versioning and
         upgraded in place by stamping the CURRENT _WS_SCHEMA_VERSION onto it.
       - present and <= _WS_SCHEMA_VERSION -- understood. Only one version has ever existed as of
         this PR, so this is a straight pass-through today; a real future version bump with its own
         forward-migration would branch on the specific old number inside _wsMigrateAll below, in
         exactly the one place that already inspects every record, rather than a second place.
       - present and > _WS_SCHEMA_VERSION -- data written by a NEWER build than what is currently
         running (a technician's browser cache holding a newer build, or a rolled-back deploy
         running older code against already-upgraded data -- both real, not hypothetical). CLEAN
         REFUSAL: never silently treated as understood, and -- just as importantly -- never
         DELETED either. A rolled-back/stale build committing a write must not destroy data a
         newer build already wrote just because THIS build cannot interpret it; see _wsMigrateAll's
         own comment for exactly how "refused" still survives every commit.

     _wsClassifyRecordSchema() below is the ONE place that <= / > comparison is made. Both the
     read-path migration (_wsMigrateAll, used by _wsAllForRead()/_wsAllForMutation() further down)
     and the import-path validation (_wsValidateImportShape(), PR 3, further below) call this exact
     function -- never a second, independently-typed copy of the same comparison -- so "migrate vs
     refuse" can never quietly diverge between "a saved workspace this browser already has" and "a
     workspace file someone just handed this browser," which is the single most realistic way two
     different schemaVersions actually meet in practice: two technicians on two different app
     versions handing a workspace export to each other. Exposed read-only on VW.workspace as
     _classifySchemaVersion (leading-underscore, matching this file's existing debug-accessor
     convention, e.g. VW.locks._debugPendingCount) so this can be proven directly rather than only
     inferred from source text; engine/tests/test_vw_workspace_schema_version.py's own "not
     duplicated" check additionally confirms, structurally, that both call sites above really do
     read from this one function's text rather than each rolling their own comparison. */
  var _WS_SCHEMA_VERSION = 1;

  /* Classifies a raw schemaVersion value (whatever was actually stored, or handed in on an import
     payload -- may be a number, undefined, or garbage from a hand-edited/tampered file) against
     what THIS running build understands. Pure and side-effect-free on purpose, so it can be the
     one thing every call site above shares without any of them needing to also inherit a
     mutation or a console call they did not ask for.
       "missing" -- no field at all (typeof undefined) -- see the MISSING case above.
       "ok"      -- a real, finite number <= _WS_SCHEMA_VERSION.
       "future"  -- a real, finite number > _WS_SCHEMA_VERSION.
       "invalid" -- present but not a usable number (a string, NaN, null, an object) -- a
                    hand-edited or corrupted value this build cannot trust any more than an
                    unrecognized future one, refused the same way "future" is; kept as a distinct
                    status purely so the reason text stays accurate about which problem it is. */
  function _wsSchemaVersionStatus(schemaVersion) {
    if (typeof schemaVersion === "undefined") return "missing";
    if (typeof schemaVersion !== "number" || !isFinite(schemaVersion)) return "invalid";
    if (schemaVersion > _WS_SCHEMA_VERSION) return "future";
    return "ok";
  }

  /* Applies _wsSchemaVersionStatus() to one candidate record/payload's .schemaVersion field and
     turns it into a {ok, status, reason} verdict -- reason is only ever set when ok is false, and
     is always specific enough to name the actual value and what this build does understand, per
     the design spec's "refused with a clear message (never silently misinterpreted)" edge case
     and PR 3's own established specific-message convention for other malformed-import cases
     (_wsValidateImportShape below). Accepts a bare object (a parsed import payload need not be a
     real workspace record) -- reads only .schemaVersion off it, nothing else. */
  function _wsClassifyRecordSchema(rec) {
    var sv = rec ? rec.schemaVersion : undefined;
    var status = _wsSchemaVersionStatus(sv);
    if (status === "missing" || status === "ok") return { ok: true, status: status };
    return {
      ok: false,
      status: status,
      reason: status === "future"
        ? ("schemaVersion " + sv + " is newer than this app version understands (max " +
           _WS_SCHEMA_VERSION + ")")
        : "schemaVersion is not a recognized value"
    };
  }

  /* THE READ-PATH MIGRATION. Runs every record in the "all" array passed in (the LIVE mutation
     array on the IndexedDB-backed path -- see the big comment above _wsEnsureCache() for why
     mutating those objects in place matters there especially -- or a fresh parse on the
     localStorage path) through _wsClassifyRecordSchema() and:
       - "missing"          -> stamps _WS_SCHEMA_VERSION onto the record OBJECT ITSELF, in place
                                (never a copy), so the SAME reference committed back afterward
                                carries the stamp, and so an IndexedDB-cache-backed record keeps the
                                stamp for the rest of this page's life even before any
                                still-pending write-through resolves.
       - "ok"                -> left completely untouched.
       - "future"/"invalid"  -> left COMPLETELY untouched in the returned "all" (never dropped,
                                never overwritten) but left OUT of the returned "visible" array, the
                                one a caller-facing read actually gets back, and named in the
                                returned "refused" list with its id/reason so list()/get() below can
                                each surface a distinguishable signal rather than folding a refusal
                                into an identical-looking empty/not-found result. Keeping it in
                                "all" (not "visible") is what lets a plain commit of "all" --
                                workspaceCreate() pushing a sibling record, workspaceTouch()/
                                workspaceDelete() on a DIFFERENT id -- carry a record this build
                                cannot interpret safely through to the next write, unharmed, exactly
                                like _wsItems()'s established "drop what's invalid, keep the rest"
                                precedent is applied here to READS, not to the record's continued
                                existence in storage.
     A console.warn per refused record, naming the id and the reason, is this function's own
     "never silently misinterpreted" signal -- independent of whatever list()/get() layer on top of
     it (see their own comments below), and the one a technician actually watching devtools would
     see even if no UI code ever calls the debug accessors those expose. */
  function _wsMigrateAll(all) {
    var visible = [];
    var refused = [];
    var migrated = false;
    for (var i = 0; i < all.length; i++) {
      var rec = all[i];
      var verdict = _wsClassifyRecordSchema(rec);
      if (!verdict.ok) {
        refused.push({ id: rec && rec.id, schemaVersion: rec && rec.schemaVersion, reason: verdict.reason });
        try {
          console.warn("VW.workspace: record " + (rec && rec.id) + " has an unrecognized " +
            "schemaVersion (" + JSON.stringify(rec && rec.schemaVersion) + ") -- " + verdict.reason +
            "; excluded from list()/get(), left untouched in storage.");
        } catch (e) { /* devtools/console unavailable -- the refused[] list above still tells the story */ }
        continue;
      }
      if (verdict.status === "missing") {
        rec.schemaVersion = _WS_SCHEMA_VERSION;
        migrated = true;
      }
      visible.push(rec);
    }
    return { all: all, visible: visible, migrated: migrated, refused: refused };
  }

  /* The most recent workspaceList()/workspaceGet() call's refused-record list (see _wsMigrateAll
     above) -- exposed read-only as VW.workspace._lastReadSchemaRefusals() so a caller (a test, or a
     future UI) can distinguish "every record came back clean" from "something was excluded" without
     get()'s or list()'s own return shape ever having to grow a second, error-carrying variant. Reset
     at the top of every _wsAllForRead() call, so it always reflects only the most recent read. */
  var _wsLastReadRefusals = [];

  /* The two entry points every CRUD/export/import function below goes through instead of calling
     _wsRead()/_wsWrite() directly. On lite/legacy tier (or wherever indexedDB is unavailable) these
     are exactly _wsRead()/_wsWrite() -- nothing about that path changes in this PR. On the
     IndexedDB-backed path, reads return a fresh clone of _wsCache (matching _wsRead()'s own "always
     a fresh copy" contract) and mutations get the LIVE _wsCache array to modify directly, committed
     back via _wsCommit().

     v1.76.0: both now additionally run every record through _wsMigrateAll() (above) before handing
     anything to a caller. _wsAllForMutation() returns the FULL (post-stamp, pre-filter) array,
     unchanged in length -- create()'s id-uniqueness scan and touch()/delete()'s id lookups need the
     real underlying set, and any refused/unrecognized-future record MUST still be present in what
     gets committed back, or the very next mutation from this page would silently erase it. Only
     _wsAllForRead() applies the visibility filter (a caller-facing list()/get() must never even see
     a record it should refuse to interpret) -- and, when _wsMigrateAll() reports a genuine in-place
     stamp AND this was a CLEAN read (_wsLastReadHadJunk false -- see that variable's own comment),
     immediately commits the result back via the SAME _wsCommit() every mutation already uses
     ("via the existing commit path", per this PR's own plan entry), so a stamped record is durably
     upgraded on its very first CLEAN read rather than waiting on some future unrelated write to
     carry it along -- an idempotent, one-time upgrade-on-first-touch for the overwhelmingly common
     real case (every already-saved workspace, on otherwise-healthy storage). The junk-mixed-in case
     defers the durable write specifically to preserve this file's older, still-deliberate "a read
     never rewrites storage" guarantee for corrupt/hostile values -- the in-memory stamp still makes
     THIS call's own return value correct; only persisting it waits for a real mutation (or a later
     clean read) instead of happening as a side effect of merely looking at hostile data. The
     IndexedDB-backed path has no equivalent concern (_wsLastReadHadJunk only ever reflects the
     localStorage path _wsRead() actually took) -- its own cache/commit model already documented
     above never treated "read" as side-effect-free in the first place (_wsEnsureCache() itself
     always kicks off an asynchronous reconcile). */
  function _wsAllForMutation() {
    var all = _wsUsingIndexedDB() ? _wsEnsureCache() : _wsRead();
    return _wsMigrateAll(all).all;
  }
  function _wsAllForRead() {
    var onIdb = _wsUsingIndexedDB();
    var all = onIdb ? _wsEnsureCache() : _wsRead();
    var hadJunk = onIdb ? false : _wsLastReadHadJunk;
    var migration = _wsMigrateAll(all);
    _wsLastReadRefusals = migration.refused;
    /* onIdb: only commit a migration stamp eagerly once _wsIdbDb is already a real, established
       connection -- i.e. _wsIdbReconcile() (kicked off by _wsEnsureCache() above, at most once per
       page) has ALREADY decided replace-vs-migrate and this page's cache is no longer the
       still-provisional localStorage-sourced bootstrap value. Committing BEFORE that point would
       open a second, independent IndexedDB connection out of band and could write this page's
       bootstrap cache into the durable store before reconcile's own read of it resolves -- which
       would make reconcile see "IndexedDB already has records" and wrongly skip replacing the
       cache with truly-authoritative IndexedDB data from a prior session (a real, observed failure
       mode this exact ordering was written specifically to prevent; see the big comment above
       _wsEnsureCache() for the bootstrap/reconcile contract this must never race against). Skipping
       the eager commit here costs nothing: the stamp already lives in _wsCache (mutated in place by
       _wsMigrateAll above) for the rest of THIS page's life regardless, and reconcile's own
       eventual write (the "IndexedDB reads back empty" branch clones _wsCache AT THE TIME IT
       RUNS, so it already carries any migration applied by then) or the next real mutation's own
       commit persists it durably either way. */
    if (migration.migrated && !hadJunk && (!onIdb || _wsIdbDb)) _wsCommit(migration.all);
    return onIdb ? _wsCloneAll(migration.visible) : migration.visible;
  }
  function _wsCommit(all) {
    if (_wsUsingIndexedDB()) {
      _wsCache = all;
      _wsIdbPersist(_wsCloneAll(all));
      return true;
    }
    return _wsWrite(all);
  }

  /* create(name, items) -> id, or null if storage refused the write.
     The third argument is the record's "source" field, defaulting to "manual" and accepting only
     "template" as the alternative. It exists now, rather than being bolted on in PR 4, because the
     design spec's record shape carries "source" from the start -- without it this function could
     only ever write "manual" and the field would be a constant with a misleading name. */
  function workspaceCreate(name, items, source) {
    var all = _wsAllForMutation();
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
      source: source === "template" ? "template" : "manual",
      /* v1.76.0: every NEWLY-created record is stamped with the current schema version -- see the
         big comment above _wsMigrateAll() for the full read-side migration story. A record with no
         schemaVersion at all is therefore, from this PR forward, unambiguously "written before this
         PR shipped", never a record this build itself just created. */
      schemaVersion: _WS_SCHEMA_VERSION
    };
    all.push(ws);
    if (!_wsCommit(all)) return null;
    _wsNotify("create", ws);
    return ws.id;
  }

  /* list() -> array of workspace records in creation order (oldest first), newest appended last.
     Every call re-reads the active backing, so the returned records are fresh copies -- a caller
     mutating what it gets back cannot corrupt what is stored, and cannot hold a stale view across
     another tab's write either (on the IndexedDB-backed path this is a fresh clone of _wsCache; on
     the localStorage path it is _wsRead()'s own fresh parse, unchanged). A UI wanting
     most-recently-opened order sorts by lastOpened itself. */
  function workspaceList() { return _wsAllForRead(); }

  /* get(id) -> the workspace record, or null when no such id is stored. v1.76.0: null is ALSO
     returned when the id genuinely IS stored but this build refuses to interpret its schemaVersion
     (see _wsMigrateAll above) -- get()'s long-established not-found convention is kept exactly
     as-is (never a second return shape for this rarer case) rather than changed, but the two null
     cases are not identical under the hood: _wsMigrateAll() already emitted a console.warn naming
     this id and its unrecognized schemaVersion during the _wsAllForRead() call just above, and
     _wsLastGetSchemaRefusal (reset at the top of every call, so it always reflects only the most
     recent one) additionally lets a caller -- or a future UI -- ask "was that null a genuine
     not-found, or a refused schema mismatch?" without get() itself ever lying about which one it
     was. Exposed read-only as VW.workspace._lastGetSchemaRefusal(). */
  var _wsLastGetSchemaRefusal = null;
  function workspaceGet(id) {
    _wsLastGetSchemaRefusal = null;
    if (id === null || id === undefined) return null;
    var want = String(id);
    var all = _wsAllForRead();
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === want) return all[i];
    }
    for (var j = 0; j < _wsLastReadRefusals.length; j++) {
      if (_wsLastReadRefusals[j].id === want) { _wsLastGetSchemaRefusal = _wsLastReadRefusals[j]; break; }
    }
    return null;
  }

  /* touch(id) -> true when it updated lastOpened, false when the id is not stored (so a caller can
     tell a stale id from a real one) or when storage refused the write. Only lastOpened moves --
     created, name, items and source are left exactly as they were. */
  function workspaceTouch(id) {
    if (id === null || id === undefined) return false;
    var want = String(id);
    var all = _wsAllForMutation();
    var hit = null;
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === want) { hit = all[i]; break; }
    }
    if (!hit) return false;
    hit.lastOpened = Date.now();
    if (!_wsCommit(all)) return false;
    _wsNotify("touch", hit);
    return true;
  }

  /* v1.66.0: delete(id) -- the one CRUD operation VW.workspace shipped without originally
     (create/list/get/touch only). Added for F -- save & reopen named workspaces (PR 16 of 25,
     stage 5): a list UI that only ever grows is a real usability problem for a page a technician
     returns to across a whole career, not a hypothetical one. Same read-all/mutate/write-back shape
     as touch() above (a boolean return that tells a caller a stale id from a real removal apart
     from a write storage refused), same "notify only after the write has already committed"
     ordering as every other mutating call in this section. */
  function workspaceDelete(id) {
    if (id === null || id === undefined) return false;
    var want = String(id);
    var all = _wsAllForMutation();
    var hit = null, kept = [];
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === want) { hit = all[i]; } else { kept.push(all[i]); }
    }
    if (!hit) return false;
    if (!_wsCommit(kept)) return false;
    _wsNotify("delete", hit);
    return true;
  }

  /* v1.65.0: VW.workspace export/import (PR 3 of 18, stage 2 -- inserted after PR 15/B/16-F's
     launcher work because PR 16 (F, save & reopen named workspaces) depends on this landing first;
     see the plan doc's own note on the reordering). The point is handing one saved workspace to a
     DIFFERENT technician's browser -- a shareable link (exportUrl/importUrl) or a downloadable
     .json (exportFile/importFile) -- so export/import deliberately carry only {name, items}, never
     this browser's internal id/created/lastOpened. Leaking the id would be actively misleading
     (it means nothing on another machine) and leaking timestamps would misrepresent when the
     RECEIVING technician actually created their own copy.

     WHY IMPORT IS STRICTER THAN create()'s OWN COERCION: create() is fed a payload this same page
     built for its own use, so _wsItems() quietly drops any one bad entry and keeps the rest moving
     -- there is no "someone else's file" to distrust. Import is different: the JSON came from a
     file or a URL that could have been hand-edited, corrupted in transit, or deliberately tampered
     with, so the design spec's edge case ("Workspace import of a malformed/tampered file")
     requires the WHOLE thing validated before anything is written, and rejected with a clear
     message on any mismatch -- never a silent partial import. _wsValidateImportShape below reuses
     _wsItems() itself as the arbiter of "is this item well-formed" (rather than re-implementing
     the same {page, params} checks a second time): if _wsItems() would drop an entry, that entry
     was invalid, and unlike create() that is treated as a reason to refuse the whole import.

     WHY IMPORT ALWAYS MINTS A FRESH ID: an imported payload never even carries an id field (see
     _wsExportPayload below), and even if a crafted/tampered payload smuggled one in, _wsImportFromJson
     only ever reads .name and .items off the parsed object and hands them to workspaceCreate(),
     which mints via the same _wsNewId() path every other workspace goes through -- there is no code
     path anywhere in here that could reuse an incoming id even by accident. */

  /* The data an export hands to a different browser: name + items + schemaVersion. Shared by
     exportUrl and exportFile so this shape is written exactly once.
     v1.76.0: schemaVersion joins name/items here because two technicians running different app
     versions handing a workspace file to each other is the single most realistic real-world
     scenario for a genuine version mismatch -- see _wsValidateImportShape below for the matching
     import-side check. Uses the build's own _WS_SCHEMA_VERSION rather than reading ws.schemaVersion
     back off the record: by the time any caller reaches a real "ws" argument here, it already came through
     workspaceGet() -> _wsAllForRead() -> _wsMigrateAll(), which never returns a record this build
     doesn't fully understand (a refused one comes back as get()'s null instead, so exportUrl/
     exportFile already return null for it via their own existing not-found convention) -- so the
     two are always equal in practice, and using the named constant directly says plainly "this
     export reflects what THIS build understands", which is the actually-true claim being made. */
  function _wsExportPayload(ws) {
    return { name: ws.name, items: ws.items, schemaVersion: _WS_SCHEMA_VERSION };
  }

  /* Shape-validates a parsed import payload before ANYTHING is written to storage. Returns null
     when the payload is well-formed, or a short, specific reason string otherwise (never throws
     itself -- the caller turns a non-null reason into a real Error with a clear .message). */
  function _wsValidateImportShape(parsed) {
    if (!parsed || typeof parsed !== "object" ||
        Object.prototype.toString.call(parsed) !== "[object Object]") {
      return "expected a workspace object";
    }
    if (typeof parsed.name !== "string") return "workspace name must be a string";
    if (Object.prototype.toString.call(parsed.items) !== "[object Array]") {
      return "workspace items must be an array";
    }
    /* _wsItems() drops any entry that is not a plain object with a non-empty page: if the coerced
       array is shorter than the raw one, at least one item failed that check, and the whole import
       is refused rather than silently keeping only the entries that happened to survive. */
    if (_wsItems(parsed.items).length !== parsed.items.length) {
      return "one or more workspace items is missing a valid page";
    }
    /* v1.76.0: the SAME migrate-or-refuse decision the read path uses (_wsClassifyRecordSchema,
       shared verbatim -- see its own big comment above _wsMigrateAll for why this must never be a
       second, independently-typed copy of the comparison). A payload with no schemaVersion at all
       (every export this codebase produced before this PR shipped) classifies as "missing", which
       is "ok" here exactly as it is on the read path -- an old export stays importable. Only a
       schemaVersion NEWER than this build understands is refused, with the same specific-message
       convention as every other reason string in this function. */
    var schemaVerdict = _wsClassifyRecordSchema(parsed);
    if (!schemaVerdict.ok) return schemaVerdict.reason;
    return null;
  }

  /* Shared by importUrl/importFile: parses JSON text, validates its shape, and on success creates a
     BRAND NEW workspace from just its name/items -- never anything else the payload might carry.
     source is hardcoded "manual": a technician importing someone else's hand-off is not "using a
     template". Throws a real Error with a specific, catchable .message on ANY parse or shape
     failure, and -- because the throw happens before workspaceCreate() is ever reached -- storage
     is never touched on a rejected import. */
  function _wsImportFromJson(raw) {
    var parsed;
    try { parsed = JSON.parse(raw); }
    catch (e) { throw new Error("Workspace import failed: not valid JSON."); }
    var reason = _wsValidateImportShape(parsed);
    if (reason) throw new Error("Workspace import failed: " + reason + ".");
    return workspaceCreate(parsed.name, parsed.items, "manual");
  }

  /* exportUrl(id) -> a compact, URL-safe query-string encoding of the workspace ("ws=<json>"),
     meant to be handed to a different technician's browser via importUrl(). A plain
     JSON.stringify + encodeURIComponent under one query key -- consistent with this file's
     no-dependencies style, no compression/base64 library reached for. Returns null (never throws)
     when the id is not stored, matching get()'s own not-found convention: exportUrl is a read, not
     an import, so it stays on the soft-null side of this file's error-handling split. */
  function workspaceExportUrl(id) {
    var ws = workspaceGet(id);
    if (!ws) return null;
    return "ws=" + encodeURIComponent(JSON.stringify(_wsExportPayload(ws)));
  }

  /* exportFile(id) -> the same payload as exportUrl, wrapped as a real downloadable Blob (caller's
     choice how to hand it off -- a download link, or the File System Access API later; both are
     explicitly out of scope here). Returns null under the same not-found convention as exportUrl. */
  function workspaceExportFile(id) {
    var ws = workspaceGet(id);
    if (!ws) return null;
    return new Blob([JSON.stringify(_wsExportPayload(ws))], { type: "application/json" });
  }

  /* importUrl(qs) -> id. Accepts either a bare query string (as exportUrl returns it) or a full
     "?"-prefixed fragment (e.g. handed location.search directly), so a caller never has to strip a
     leading "?" first. Parses the "ws" key by hand rather than reaching for URLSearchParams (not
     available on the legacy tier this file supports elsewhere). Throws with a clear message (never
     returns null) on any parse or shape failure -- per the design spec's malformed/tampered-import
     edge case, unlike this file's usual not-found convention, a bad import is a caller mistake or a
     tampered file, not a routine "nothing there yet". */
  function workspaceImportUrl(qs) {
    var s = (qs === null || qs === undefined) ? "" : String(qs);
    if (s.charAt(0) === "?") s = s.slice(1);
    var raw = null;
    var parts = s.split("&");
    for (var i = 0; i < parts.length; i++) {
      var eq = parts[i].indexOf("=");
      var key = eq === -1 ? parts[i] : parts[i].slice(0, eq);
      if (key === "ws") { raw = eq === -1 ? "" : parts[i].slice(eq + 1); break; }
    }
    if (raw === null) throw new Error("Workspace import failed: no 'ws' value found.");
    var decoded;
    try { decoded = decodeURIComponent(raw); }
    catch (e) { throw new Error("Workspace import failed: could not decode the share link."); }
    return _wsImportFromJson(decoded);
  }

  /* importFile(blob) -> a Promise resolving to the new id. Blob reading is inherently
     asynchronous; this follows the same ES5-safe .then()-chain pattern already used elsewhere in
     this codebase (e.g. palette.js's window.fetch call, chained with plain .then() callbacks),
     never an arrow function or async/await. Rejects with the same clear-message Error as importUrl
     on any parse or shape failure (a synchronous throw inside a .then() callback becomes a
     rejection, so _wsImportFromJson's throws propagate correctly here). */
  function workspaceImportFile(blob) {
    if (!blob || typeof blob.text !== "function") {
      return Promise.reject(new Error("Workspace import failed: not a readable file."));
    }
    return blob.text().then(function (text) {
      return _wsImportFromJson(text);
    });
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
          and so a later PR can record and restore each window's real screen position (PR 6, layered
          on top of this same registry below -- screenX/screenY/outerWidth/outerHeight are read LIVE
          off the handle this registry already holds, not captured once and cached, since a
          technician can move/resize a window after opening it).
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

     No window-features argument is passed UNLESS opts carries a position/size hint (v1.67.0, PR 6):
     supplying one turns what the browser would have opened as an ordinary tab into a stripped
     chrome-less popup, overriding the user's own new-window preference, so the plain 1/2-argument
     form stays the default for every call site that never asks for placement. opts.left/opts.top/
     opts.width/opts.height are the hint vocabulary (matching window.open()'s own features-string
     keys directly, so there is exactly one translation step, not two) -- present only when a caller
     genuinely wants to request an initial position/size, which today means restoreLayout() below,
     but is not restricted to it; any caller may pass them. Threaded into the third window.open()
     argument ONLY when a genuinely NEW window is being opened, never on a reuse: browsers generally
     only honor position/size features on a window's very FIRST open, not a later reuse/refocus of an
     already-named one, so re-sending them on reuse would be at best a no-op and at worst
     browser-inconsistent -- a real, honest platform limitation stated here rather than glossed over
     (also stated plainly in the PR body, per the plan's own instruction not to paper over what
     cannot actually be verified/guaranteed without a real second monitor and multiple browsers).
     Hints are sanity-checked against THIS screen's own window.screen.availWidth/availHeight before
     use (_winBoundsSane below) -- the design doc's own named "monitor unplugged since the position
     was saved" fallback case -- and any hint that fails is dropped ENTIRELY (never partially
     applied), degrading silently to a normal, unhinted open rather than risking a window placed
     off-screen where a technician could not find or reach it. A bad hint never throws; it only ever
     falls back to the browser's own default placement.

     Popup blockers: every intended call site is a real click handler and browsers permit
     user-gesture-initiated opens, so a block should never happen in practice. It is still handled,
     because window.open() returns null when it does happen and can throw outright in a locked-down
     configuration: open() returns null, and the toast, the registry write and the broadcast are all
     skipped, since none of them may claim a window opened when none did.

     opts.screen (v1.68.0, PR 17, C -- screen-aware placement): a truthy hint meaning "prefer a
     different screen than this tab's own, if one exists and is available" -- ignored gracefully
     everywhere the feature-detected Window Management API isn't available or the hardware tier
     doesn't qualify. Handled entirely AFTER this function's own synchronous open/reuse/toast/
     broadcast steps above, by _attemptScreenPlacement below -- see its own header comment for the
     full permission-timing reasoning (the crux of this whole PR) and the doc/code gap it resolves. */
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

  /* v1.67.0 (PR 6): reads ONE bounds property off a same-origin window handle, defensively. This app
     only ever opens its OWN pages via window.open(), so every handle _winReg holds is same-origin and
     screenX/screenY/outerWidth/outerHeight are ordinary, no-permission-needed properties -- there is
     nothing here for PR 17's feature-detected getScreenDetails() to layer under; that is a separate,
     permission-gated API this PR does not touch. The property read is wrapped on its OWN, one field
     at a time, rather than wrapping the whole four-field build in one try/catch: a handle mid
     teardown (closed === true already ruled out by _winPrune() above, but a rarer half-torn-down
     state can still throw on some property access, per the same honest note _winPrune()'s own comment
     already makes) might allow SOME properties to read fine and throw on others, and a caller is
     better served by a partially-filled entry than by losing every field over one throwing property. Also
     guards against a non-finite/non-number value some embedding could hand back instead of a real
     throw -- either way this returns null, never lets a bad value through. */
  function _winBoundsField(win, prop) {
    try {
      var v = win[prop];
      return (typeof v === "number" && isFinite(v)) ? v : null;
    } catch (e) { return null; }
  }

  /* All four live bounds fields for one window handle, each independently guarded by
     _winBoundsField above -- one throwing/unreadable property degrades ONLY that field to null,
     never the other three, and never the caller's whole loop over every OTHER tracked window
     (windowsRegistry() below calls this once per entry, inside its own loop, so a bad handle for
     window A can never take down what is reported for window B). */
  function _winLiveBounds(win) {
    return {
      screenX: _winBoundsField(win, "screenX"),
      screenY: _winBoundsField(win, "screenY"),
      outerWidth: _winBoundsField(win, "outerWidth"),
      outerHeight: _winBoundsField(win, "outerHeight")
    };
  }

  /* Currently-tracked open windows THIS tab opened, newly-built plain objects each call, so a caller
     can never reach in and corrupt the registry by mutating what it was handed. v1.67.0 (PR 6): each
     entry now also carries LIVE screenX/screenY/outerWidth/outerHeight, read off the handle at THIS
     call, not captured once at open-time and cached -- a technician can move or resize a window after
     opening it, and re-reading off the handle this registry already holds costs nothing extra and
     stays accurate. A field that could not be read for a given window is null, not omitted -- every
     entry has the same six keys, whether or not every value could be filled in. */
  function windowsRegistry() {
    _winPrune();
    var out = [], name, entry, bounds;
    for (name in _winReg) {
      if (!Object.prototype.hasOwnProperty.call(_winReg, name)) continue;
      entry = _winReg[name];
      bounds = _winLiveBounds(entry.win);
      out.push({ name: entry.name, url: entry.url,
        screenX: bounds.screenX, screenY: bounds.screenY,
        outerWidth: bounds.outerWidth, outerHeight: bounds.outerHeight });
    }
    return out;
  }

  /* v1.67.0 (PR 6): sanity-checks a caller's position/size hint against THIS screen's own reasonable
     extent before it is ever threaded into a window.open() features string -- the design doc's own
     named "monitor unplugged since the position was saved" fallback case. Returns null (meaning
     "use no hint at all, fall back to the browser's normal placement") when window.screen itself is
     unreadable, when NEITHER availWidth NOR availHeight comes back as a usable positive number, or
     when ANY hint field that WAS provided fails its own check -- deliberately all-or-nothing, never a
     partial application of "the width looked fine but the left didn't": a window positioned by only
     half of a stale hint is not obviously better than one placed by the browser's own default, and
     "skip gracefully" is simpler and safer to reason about than partial credit.

     The ceiling is deliberately generous, not a single screen's own availWidth/availHeight: a real
     multi-monitor span (a technician's second screen sitting to the right of, above, or below the
     first) can legitimately put a saved left/top well past this one screen's own extent, and this PR
     has no access to the actual multi-monitor geometry (that is PR 17's permission-gated
     getScreenDetails() job, explicitly out of scope here) -- only this one screen's availWidth/
     availHeight as a sanity CEILING, per the plan's own suggestion. 4x this screen's own span is
     comfortably wide enough to admit a plausible second-or-third-monitor position while still
     rejecting the actual failure mode this exists for: a wildly stale, negative-beyond-reason, or
     just-plain-nonsensical value left over from hardware that is no longer connected at all. */
  function _winBoundsSane(o) {
    var availW = null, availH = null;
    try { availW = window.screen ? window.screen.availWidth : null; } catch (e) { availW = null; }
    try { availH = window.screen ? window.screen.availHeight : null; } catch (e) { availH = null; }
    if (typeof availW !== "number" || !isFinite(availW) || availW <= 0) return null;
    if (typeof availH !== "number" || !isFinite(availH) || availH <= 0) return null;

    function within(v, lo, hi) { return typeof v === "number" && isFinite(v) && v >= lo && v <= hi; }

    var out = {};
    if (o.left !== undefined) {
      if (!within(o.left, -availW, availW * 4)) return null;
      out.left = o.left;
    }
    if (o.top !== undefined) {
      if (!within(o.top, -availH, availH * 4)) return null;
      out.top = o.top;
    }
    if (o.width !== undefined) {
      if (!within(o.width, 1, availW * 4)) return null;
      out.width = o.width;
    }
    if (o.height !== undefined) {
      if (!within(o.height, 1, availH * 4)) return null;
      out.height = o.height;
    }
    return out;
  }

  /* v1.67.0 (PR 6): builds the window.open() THIRD-argument features string ("left=100,top=50,
     width=800,height=600") from opts.left/opts.top/opts.width/opts.height, or returns null when
     there is nothing usable to build -- either no hint fields were offered at all (the overwhelming
     common case; window.screen is never even touched then, so this stays free for every ordinary
     call), or the hint(s) offered failed _winBoundsSane's check above. null, never an empty string:
     an EMPTY features string is itself a different, real request some browsers read as "open a
     stripped-down popup with nothing specified" -- not the same as "no hint", which must fall through
     to the plain 1/2-argument window.open() call windowsOpen() already made before this PR. */
  function _winFeaturesString(o) {
    if (o.left === undefined && o.top === undefined && o.width === undefined && o.height === undefined) {
      return null;
    }
    var sane = _winBoundsSane(o);
    if (!sane) return null;
    var parts = [];
    if (sane.left !== undefined) parts.push("left=" + Math.round(sane.left));
    if (sane.top !== undefined) parts.push("top=" + Math.round(sane.top));
    if (sane.width !== undefined) parts.push("width=" + Math.round(sane.width));
    if (sane.height !== undefined) parts.push("height=" + Math.round(sane.height));
    return parts.length ? parts.join(",") : null;
  }

  function windowsOpen(url, opts) {
    var o = opts || {};
    var name = (typeof o.name === "string" && o.name) ? o.name : null;
    _winPrune();                       // a window the user closed must not be reported as reused
    var reused = !!(name && _winReg[name]);
    var win = null;
    /* v1.67.0 (PR 6): a position/size hint is only ever considered for a genuinely NEW open -- never
       computed at all on a reuse, far less passed to window.open(). Reusing an existing named window
       must not attempt to reposition it (see the big comment above this function for the honest
       browser limitation this reflects: position/size features are generally only honored on a
       window's first open). Skipping the computation entirely on reuse, rather than computing it and
       simply not using it, also means a reuse never touches window.screen at all. */
    var features = reused ? null : _winFeaturesString(o);
    /* Always really call window.open, reuse or not: the reuse, the navigation to a possibly-new url,
       and the raise-to-front are all things the BROWSER does in response to this call. Skipping it
       because the registry already knows the name would leave the existing window untouched and
       still sitting behind whatever is in front of it. */
    try {
      if (features) win = window.open(url, name || "", features);
      else win = name ? window.open(url, name) : window.open(url);
    } catch (e) { win = null; }
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
    /* v1.68.0 (PR 17, C -- screen-aware placement): opt-in per call via opts.screen, attempted ONLY
       after every synchronous step above -- see the big comment on _attemptScreenPlacement (below in
       source order, hoisted, callable from here) for why that ordering is the entire point.
       Fire-and-forget; never awaited, never delays this synchronous return by even one tick. */
    _attemptScreenPlacement(win, o.screen);
    return win;
  }

  /* v1.67.0: VW.windows.restoreLayout(entries) -- PR 6, "layout capture + user-triggered restore"
     (docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 2, closing out the item PR 5's
     own header comment named and deliberately deferred). Takes an array shaped like what registry()
     returns (or a previously-saved snapshot of it -- a workspace/checkpoint entry that has grown these
     same fields now that registry() reports them) and, for each entry carrying a usable name AND url,
     calls windowsOpen() -- THE SAME open/reuse/toast/broadcast path above, not a second, parallel copy
     of any of it -- translating the registry's screenX/screenY/outerWidth/outerHeight field names into
     windowsOpen()'s own left/top/width/height opts vocabulary (see _winFeaturesString above for why
     the two vocabularies differ: one matches what a live window handle reports back, the other
     matches window.open()'s own features-string keys directly).

     CONTRACT, since nothing in this codebase calls this yet: entries missing a usable name or url are
     SKIPPED, never thrown over -- one bad row in a batch (a hand-edited file, a stale snapshot
     referencing a page that no longer exists) must not abort every OTHER entry. Returns an array, one
     result object per INPUT entry, in the same order: {name, url, ok, reused}. ok is true when
     windowsOpen() returned a real window handle for that entry (false for a skipped/malformed entry,
     or one windowsOpen() itself returned null for -- popup-blocked, refused, or a thrown window.open);
     reused reports whether that entry's name was already tracked in THIS tab's registry before this
     call reached it (read before calling windowsOpen(), which is the one place that actually decides
     and acts on reuse -- this only observes and reports it, never re-decides it).

     MUST NEVER BE CALLED FROM A LOAD/INIT/DOMCONTENTLOADED-STYLE HANDLER ANYWHERE IN THIS CODEBASE.
     restoreLayout() reopens windows unprompted, which is exactly the case the design doc's own honest
     note names: "a web page cannot run code 'on app launch' unprompted, so 'restore my layout' is a
     button, not silent magic." It is only ever safe to call from a genuine click handler -- a
     technician pressing an explicit "restore my layout" button on some future page. Nothing in this
     diff wires one; see the PR body for why that UI is deliberately out of this PR's scope. */
  function windowsRestoreLayout(entries) {
    var list = (Object.prototype.toString.call(entries) === "[object Array]") ? entries : [];
    var out = [], i, e, name, url, openOpts, wasTracked, win;
    for (i = 0; i < list.length; i++) {
      e = list[i] || {};
      name = (typeof e.name === "string" && e.name) ? e.name : null;
      url = (typeof e.url === "string" && e.url) ? e.url : null;
      if (!name || !url) {
        out.push({ name: name, url: url, ok: false, reused: false });
        continue;
      }
      openOpts = { name: name };
      if (typeof e.screenX === "number" && isFinite(e.screenX)) openOpts.left = e.screenX;
      if (typeof e.screenY === "number" && isFinite(e.screenY)) openOpts.top = e.screenY;
      if (typeof e.outerWidth === "number" && isFinite(e.outerWidth)) openOpts.width = e.outerWidth;
      if (typeof e.outerHeight === "number" && isFinite(e.outerHeight)) openOpts.height = e.outerHeight;
      wasTracked = !!_winReg[name];
      win = null;
      try { win = windowsOpen(url, openOpts); } catch (ex) { win = null; }
      out.push({ name: name, url: url, ok: !!win, reused: wasTracked && !!win });
    }
    return out;
  }

  /* v1.68.0: C -- screen-aware placement, extending VW.windows.open() with an opts.screen hint
     (multi-window support, PR 17 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md,
     stage 5, depending on PR 6's registry/bounds machinery above). Feature-detected via the Window
     Management API's getScreenDetails() -- Chromium-only, requires an explicit one-time user
     permission grant -- per the design doc's own item 10: "gated behind the capability ladder
     (modern tier only)."

     THE DOC/CODE GAP, and how this resolves it. The design doc names VW.capabilities.windowPlacement
     as the feature-detection gate, but VW.capabilities is Stage 6 (PR 19-25) and does not exist yet;
     nothing here builds any part of it. PR 15 hit the identical shape of gap for
     VW.capabilities.tier and had genuinely nothing real to fall back to, so it shipped
     feature-detected but INERT -- reading as "no tier info, do nothing" until Stage 6 actually lands
     (see jobcard.html's launchWorkOrder()). This PR is not in that position: window.RPS.mode is a
     real, ALREADY-LIVE hardware-tier signal, set by rps.js on every page that loads it
     ("modern"|"lite"|"legacy" -- rps.js's own RPS.MODES/applyMode). window.RPS.mode IS the capability
     ladder the design doc's item 10 asks for, just not yet wrapped in the Stage-6 name -- so this
     gates for REAL, right now, on window.RPS.mode directly, checked as an EXACT string match against
     "modern" (never a truthy/falsy read): "premium" is an additive, opt-in visual-effects FLAG
     layered on top of an already-"modern" mode (rps.js's own applyMode comment: the server only ever
     sets flags.premium_ui when mode is already "modern"; RPS.mode itself is never literally the
     string "premium" -- confirmed against rps.py's VALID_MODES/mode_for_setting()), not itself a mode
     value this check should treat as modern on its own terms. A FUTURE Stage 6 PR may replace this
     direct window.RPS.mode check with VW.capabilities.windowPlacement once that exists -- the same
     way PR 15's own tier-check comment above already points a future PR at itself.

     Not every page loads rps.js (17 of this app's 49 pages do, as of this PR) -- window.RPS is
     genuinely undefined on the rest, and _screenPlacementAvailable below treats that exactly like
     "not modern tier": skip placement, never throw, same as every other unavailable case here.

     THE PERMISSION-TIMING CONSTRAINT THIS EXISTS TO RESPECT. getScreenDetails() returns a Promise --
     it IS how the permission prompt itself surfaces -- but window.open() must run SYNCHRONOUSLY
     inside the original click-handler call stack, or a popup blocker can treat the resulting open as
     not user-gesture-initiated. So this NEVER awaits/then()s getScreenDetails() before window.open():
     windowsOpen() above already runs its entire synchronous open/reuse/toast/broadcast path and has
     its real window handle, COMPLETELY UNCHANGED from before this PR, for every caller -- a caller
     that never passes opts.screen never reaches any code below at all, and getScreenDetails() is
     never even referenced, much less called, so no permission prompt can ever appear for a click that
     never asked for one (proven by the "opts.screen absent" test in
     engine/tests/test_windows_screen_placement.py, the single most important guarantee given this
     feature's own stated permission philosophy). ONLY when opts.screen is truthy AND the gate below
     passes does this fire getScreenDetails(), fire-and-forget, AFTER windowsOpen() already returned
     its handle to the caller -- when/if that promise resolves, the ALREADY-OPEN window is repositioned
     via win.moveTo(), a same-origin operation on a window this same script opened that needs no
     special permission beyond the window still being open (a long-standing browser capability,
     unrelated to the newer Window Management permission, which gates only getScreenDetails() itself).

     ANY failure anywhere in this tail -- the API absent, the permission denied, the promise
     rejecting, only one screen existing, the window having been closed before the promise resolved,
     getScreenDetails() itself throwing synchronously -- is caught and silently ignored, exactly like
     every other "can't place it, leave it where the browser already put it" case in this file.
     Nothing here may ever throw an unhandled rejection or surface a console error under normal
     denial: ["catch"] (bracket form, matching this file's own established convention for calling this
     exact reserved-word-shaped method -- see importFile() above / palette.js's fetch chain) is wired
     on every promise this creates. */
  function _screenPlacementAvailable() {
    try {
      if (typeof window.getScreenDetails !== "function") return false;
      return !!(window.RPS && window.RPS.mode === "modern");
    } catch (e) { return false; }
  }

  /* A stable comparable key for a ScreenDetailed-shaped object (left/top -- present on every screen
     in a real multi-screen span, per the Window Management API's own shape; availLeft/availTop as a
     defensive fallback for a differently-shaped mock/object). null means "not comparable this way,"
     which _screenPlacementPick below only ever treats as "assume different" alongside a failed
     reference-equality check, never on its own. */
  function _screenKey(s) {
    try {
      if (!s) return null;
      var l = (typeof s.left === "number") ? s.left : s.availLeft;
      var t = (typeof s.top === "number") ? s.top : s.availTop;
      if (typeof l !== "number" || typeof t !== "number") return null;
      return l + "," + t;
    } catch (e) { return null; }
  }

  /* Picks a screen genuinely DIFFERENT from details.currentScreen out of a resolved ScreenDetails
     object's own .screens array -- matched by reference identity first (per the Window Management
     API, currentScreen IS the same ScreenDetailed instance found in .screens), falling back to the
     comparable left/top key above when reference equality does not hold. Returns null when there is
     nothing to move to -- fewer than two screens enumerated, or every entry compares equal to
     currentScreen -- so the caller can skip silently, same as any other "nothing available" case
     (the design doc's own opts.screen "hint" wording: prefer a different screen WHEN ONE EXISTS). */
  function _screenPlacementPick(details) {
    try {
      var screens = details && details.screens;
      if (Object.prototype.toString.call(screens) !== "[object Array]" || screens.length < 2) return null;
      var current = details.currentScreen;
      var curKey = _screenKey(current);
      var i, s, sKey;
      for (i = 0; i < screens.length; i++) {
        s = screens[i];
        if (!s || s === current) continue;
        sKey = _screenKey(s);
        if (curKey !== null && sKey !== null && sKey === curKey) continue;   // same physical screen
        return s;
      }
      return null;
    } catch (e) { return null; }
  }

  /* Fire-and-forget: called by windowsOpen() AFTER its own synchronous return value is already
     decided, never before and never in any way that could delay it. win is the handle windowsOpen()
     already produced (new open or reuse -- either way, an already-open window this repositions);
     hint is opts.screen exactly as the caller passed it. Only its truthiness matters today: a bare
     true (or any other truthy value, e.g. "other") means "prefer a different screen than this tab's
     own, if one exists and is available" -- the simplest correct reading of the design doc's own
     "screen is a hint" wording, and exactly what PR 18 (G, next in the plan) is already named to need:
     "preferring a different screen than the request's origin where PR 17's placement is available." */
  function _attemptScreenPlacement(win, hint) {
    if (!hint) return;                       // no hint offered -- getScreenDetails must never be touched
    if (!_screenPlacementAvailable()) return;
    try {
      window.getScreenDetails().then(function (details) {
        try {
          if (!win || win.closed === true) return;    // closed before the promise resolved
          var target = _screenPlacementPick(details);
          if (!target) return;                         // only one screen, or nothing genuinely different
          var left = (typeof target.availLeft === "number") ? target.availLeft : target.left;
          var top = (typeof target.availTop === "number") ? target.availTop : target.top;
          if (typeof left !== "number" || typeof top !== "number") return;
          try { win.moveTo(left, top); } catch (e) { /* same-origin move refused by some embedding */ }
        } catch (e) { /* never allow a resolved-promise handler to throw back at the browser */ }
      })["catch"](function () { /* denied/rejected -- the window stays wherever it already opened */ });
    } catch (e) { /* getScreenDetails() itself threw synchronously -- nothing left to do */ }
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

  /* v1.66.0: the auto-checkpoint -- design doc item 9's "Addition this revision" (F -- save & reopen
     named workspaces, PR 16 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage
     5). Distinct from a deliberately named/saved VW.workspace record on every axis that matters: ONE
     well-known slot under its OWN storage key, never appended to, always overwritten; silent --
     nothing here ever prompts a technician the way workspaceCreate()'s UI does; and structurally
     invisible to workspaceList(), which only ever reads _WS_KEY above and never this one, so a
     checkpoint entry can never leak into the named-workspaces list by accident the way it could if
     this were merely a differently-flagged row on the SAME key.

     WHAT IT HOLDS: {at, windows}, where windows is exactly this tab's own VW.windows.registry() at
     save time -- the same {name, url} pairs, no reshaping into {page, params}, since restoring only
     ever needs to feed them straight back into VW.windows.open(w.url, {name: w.name}), the same
     function the registry itself was built from in the first place.

     WHY THE SAVE IS WIRED HERE, AT THE SHARED.JS TOP LEVEL, RATHER THAN ONLY FROM workspaces.html:
     shared.js already loads first on every page this app adopts it on (A1/A2/B/D/F all ride that
     same fact), so wiring the save here -- once -- is what lets the checkpoint reflect windows
     opened from ANY feature (a jobcard.html launch, an A2 pop-out, an A1 home-nav link), not only
     ones opened while workspaces.html itself happened to be the active tab. workspaces.html below is
     still the one place that ever OFFERS to restore from it -- see its own script for why that split
     (write everywhere, offer in one place) is deliberate.

     WHY THE WRITE ONLY HAPPENS WHEN THIS TAB'S REGISTRY IS NON-EMPTY: VW.windows.registry() is per
     TAB, and most tabs open on this origin (a technician reading /part or /procedure directly,
     never popping anything out from it) have an empty registry for their entire lifetime. Saving
     unconditionally would make the LAST tab to fire this save win regardless of what it actually had
     open -- and that tab is overwhelmingly likely to be one of those empty-registry ones, silently
     erasing a real, useful checkpoint moments after a different tab wrote it. Skipping empty writes
     is what makes "wire it in shared.js so every feature benefits" safe rather than actively harmful.
     The residual case -- two different tabs BOTH genuinely having windows open at save time -- is
     still last-write-wins with no merge, the same conflict resolution VW.bench above already accepts
     for the identical reason, and a real but rare scenario next to the common one this guard fixes.

     WHY pagehide, NOT beforeunload/unload: this codebase already uses both elsewhere with no single
     established preference to follow (readaloud.js: beforeunload; scan.html: pagehide), so the
     design doc's own instruction ("pick the most reliable one and say why in a comment") applies
     directly. pagehide fires reliably on every real navigation-away AND on back-forward-cache
     eviction, where beforeunload is increasingly throttled or ignored by modern browsers
     specifically to make bfcache viable, and unload is deprecated outright in the same browsers for
     the same reason. This write is a synchronous localStorage call with no need for beforeunload's
     ability to prompt the user before leaving, so none of beforeunload's own reasons to exist apply.

     WHY ALSO A setInterval, belt-and-suspenders: the design doc names the real risk this exists for
     directly -- "a browser or OS crash mid-shift" fires NO unload-family event at all, since there is
     no orderly unload, only an ungraceful stop. The interval is the only path that can still have
     written a recent checkpoint when that happens. 2 minutes is deliberately not shorter: this is a
     safety net against a rare event, not a live-sync feature, and the non-empty-registry guard above
     already makes each tick cheap (one localStorage read, at most one conditional write) regardless
     of interval length -- but a several-times-a-minute tick, on every open tab, multiplied across
     however many tabs a technician has open across a shift, is exactly the kind of small-cost-
     multiplied-by-everything this app's own "long-term durability" design priority argues against
     for no benefit a several-minute interval does not already provide just as well. */
  var _CHECKPOINT_KEY = "viewer_last_session";

  /* Defensive read, same shape-checking convention as _wsRead()/benchGet() above: never throws,
     returns null (not a throw, not a default object) for anything that is missing, unparsable, or
     does not look like a real checkpoint -- a caller treats null exactly like "nothing to offer". */
  function _checkpointRead() {
    var raw = null;
    try { raw = window.localStorage.getItem(_CHECKPOINT_KEY); } catch (e) { return null; }
    if (!raw) return null;
    var parsed = null;
    try { parsed = JSON.parse(raw); } catch (e) { return null; }
    if (!parsed || typeof parsed !== "object") return null;
    if (Object.prototype.toString.call(parsed.windows) !== "[object Array]") return null;
    return parsed;
  }

  function _checkpointSave() {
    try {
      var wins = windowsRegistry();
      if (!wins.length) return;    // nothing open in THIS tab -- never clobber a real checkpoint
                                    // another tab wrote with an empty one of our own (see above).
      window.localStorage.setItem(_CHECKPOINT_KEY, JSON.stringify({ at: Date.now(), windows: wins }));
    } catch (e) { /* best-effort safety net -- never break the host page over a checkpoint write */ }
  }

  try {
    if (typeof window !== "undefined" && window.addEventListener) {
      window.addEventListener("pagehide", _checkpointSave);
      setInterval(_checkpointSave, 2 * 60 * 1000);
    }
  } catch (e) { /* never break the host page over checkpoint wiring */ }

  /* get() -> {at, windows}, or null when no checkpoint is stored (or the stored value does not look
     like one). Read-only, matching VW.workspace's own list()/get() convention: never writes, never
     notifies -- there is no cross-tab UI reacting live to a checkpoint, unlike VW.workspace/VW.bench
     above, so there is nothing for a notification to usefully trigger. */
  function checkpointGet() { return _checkpointRead(); }

  /* clear() -> true when a stored checkpoint was actually removed, false when there was nothing to
     remove or storage refused the write. Exposed for symmetry with workspaceDelete() above and so a
     restore flow can retire a checkpoint it just acted on -- callers choose whether to call this;
     nothing in this file does automatically, since the entire point of this slot is that it keeps
     itself current on its own without anything downstream having to manage its lifecycle. */
  function checkpointClear() {
    var had = _checkpointRead() !== null;
    try { window.localStorage.removeItem(_CHECKPOINT_KEY); } catch (e) { return false; }
    return had;
  }

  /* v1.73.0: VW.capabilities -- centralized feature-detection + tier registry (multi-window support,
     PR 19 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). A single object
     exposing:
       {tier, broadcastChannel, windowPlacement, wakeLock, pictureInPicture, fileSystemAccess,
        webLocks, indexedDB}
     -- see the design doc's own "VW.capabilities (Stage 6, new)" API block. Depends on nothing; PRs
     20-24 read this instead of each reimplementing its own tier/feature-detection ad hoc. Per the
     plan's own text this PR only ADDS the registry -- VW.channel/VW.workspace/VW.windows's existing
     contracts, PR 15's jobcard.html tier check, and PR 17's _screenPlacementAvailable() above are NOT
     retrofitted to read it; that retrofit is explicitly out of scope here ("a later cleanup PR, not
     part of this plan").

     LIVE READS, NOT A ONE-TIME SNAPSHOT -- the one design choice here most worth explaining. The plan
     doc calls this "computed once," but window.RPS.mode -- the tier signal every non-tier field below
     is AND-ed against -- is set on a delay: rps.js's boot() only replaces the {mode:"modern"} default
     once its own fetch("/api/rps") call resolves, and boot() itself does not even run until
     document.body exists. shared.js's own top-level code (this whole IIFE) runs on every page BEFORE
     that resolution happens, and often before rps.js has run at all (rps.js loads near the bottom of
     the body today, well after shared.js in the head) -- and most of this app's pages never load
     rps.js at all, so window.RPS stays undefined there permanently. A plain object computed once at
     this exact moment (shared.js's own module-load time) and cached forever would either capture
     "undefined" (most pages) or capture the "modern" default before the real tier ever arrives (the
     pages that do eventually load rps.js) -- silently locking every AND-ed-with-tier flag to whatever
     RPS happened to look like at that one early instant, forever, even after the real tier becomes
     known moments later. This is the same "live vs. cached" correctness question windowsRegistry()
     above already answered once (it reads screenX/screenY/etc. LIVE off the window handle at CALL
     TIME, never a stale open-time snapshot) -- so every field below is a live getter, re-evaluated on
     each access, via Object.defineProperty (plain ES5 -- deliberately NOT the newer getter/setter
     shorthand syntax built into an object literal, which rps_lint's own ES6-syntax scan would flag).
     "Computed once" is read here as "the CHECK is written once, when this file loads," never "the
     VALUE is captured once."

     Every non-tier field is a raw browser-feature check AND-ed with tier === "modern" exactly (a
     strict string match, never a truthy read -- matching _screenPlacementAvailable()'s own established
     convention above: "premium" is an additive flag layered on top of an already-"modern" mode per
     rps.js's own applyMode comment, never a mode value of its own, and unlocks nothing here beyond what
     "modern" already does). windowPlacement calls _screenPlacementAvailable() itself rather than
     re-typing a second, potentially-drifting copy of its raw getScreenDetails check, so the two can
     never diverge. Every getter below is individually wrapped in its own try/catch so one hostile or
     throwing global degrades only that one field to false, never breaking any other field's read. */
  function _capTier() {
    try {
      return (g.RPS && typeof g.RPS.mode === "string") ? g.RPS.mode : "modern";
    } catch (e) { return "modern"; }
  }
  function _capIsModernTier() {
    try { return _capTier() === "modern"; } catch (e) { return false; }
  }
  var _capabilities = {};
  Object.defineProperty(_capabilities, "tier", {
    enumerable: true,
    get: function () { return _capTier(); }
  });
  Object.defineProperty(_capabilities, "broadcastChannel", {
    enumerable: true,
    get: function () {
      try { return typeof BroadcastChannel === "function" && _capIsModernTier(); }
      catch (e) { return false; }
    }
  });
  Object.defineProperty(_capabilities, "windowPlacement", {
    enumerable: true,
    get: function () {
      try { return _screenPlacementAvailable(); }
      catch (e) { return false; }
    }
  });
  Object.defineProperty(_capabilities, "wakeLock", {
    enumerable: true,
    get: function () {
      try { return ("wakeLock" in navigator) && _capIsModernTier(); }
      catch (e) { return false; }
    }
  });
  Object.defineProperty(_capabilities, "pictureInPicture", {
    enumerable: true,
    get: function () {
      try { return typeof window.documentPictureInPicture !== "undefined" && _capIsModernTier(); }
      catch (e) { return false; }
    }
  });
  Object.defineProperty(_capabilities, "fileSystemAccess", {
    enumerable: true,
    get: function () {
      try { return typeof window.showSaveFilePicker === "function" && _capIsModernTier(); }
      catch (e) { return false; }
    }
  });
  Object.defineProperty(_capabilities, "webLocks", {
    enumerable: true,
    get: function () {
      try { return ("locks" in navigator) && _capIsModernTier(); }
      catch (e) { return false; }
    }
  });
  Object.defineProperty(_capabilities, "indexedDB", {
    enumerable: true,
    get: function () {
      try { return typeof window.indexedDB !== "undefined" && _capIsModernTier(); }
      catch (e) { return false; }
    }
  });

  /* v1.74.0: VW.locks -- Web Locks API wrapper (multi-window support, PR 20 of
     docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6): "VW.locks.withLock(name,
     fn); falls back to a best-effort in-memory single-tab lock on lite/legacy tier or where
     navigator.locks is absent." Depends on PR 19's VW.capabilities.webLocks -- this is the FIRST real
     consumer of VW.capabilities anywhere in this codebase, and it gates on the live _capabilities.webLocks
     getter directly (matching how VW.capabilities.windowPlacement above calls straight into
     _screenPlacementAvailable() rather than re-deriving its own copy) -- never a second, independently-
     typed "locks" in navigator && tier === "modern" check of its own. Writing that second check here
     would be exactly the kind of duplicated-logic-that-can-drift PR 19 was built to rule out: the two could silently diverge the
     next time either one's condition changes.

     withLock(name, fn) always returns a Promise settling with whatever fn() itself settles with -- fn
     may return a plain value or a Promise, the same duck-typing navigator.locks.request()'s own callback
     return value already supports, since both paths below feed it through a plain .then() chain (a bare
     value and a thenable are both handled identically by Promise semantics).

     REAL-API PATH (_capabilities.webLocks true): delegates straight to navigator.locks.request() --
     the browser's own implementation already handles lock acquisition, release-on-settle (success or
     failure), and cross-tab serialization; nothing here reimplements any of that.

     FALLBACK PATH (webLocks false -- lite/legacy tier, or the raw API absent, or a non-modern tier even
     with the raw API technically present): a best-effort in-memory PROMISE-CHAIN MUTEX, scoped to just
     this tab -- not a real cross-tab guarantee, but "never blocks" (see the design doc's own "VW.locks
     on a tier/browser without the Web Locks API" edge case: correctness within one tab is unaffected;
     cross-tab races the real API would have prevented become possible again, an accepted, explicitly-
     known regression on older hardware rather than a silent one).

     _lockQueues maps a lock name to the current "tail" promise for that name:
       - a call whose name has no tail yet chains off Promise.resolve() -- it runs on the next
         microtask, "never blocks" on anything.
       - a call sharing an EXISTING name chains its own fn() invocation onto that name's current tail,
         so calls sharing a name run strictly one at a time, in call order -- genuine same-tab mutual
         exclusion.
       - calls with DIFFERENT names never share a tail, so they never wait on each other.
       - the tail stored in the map (the "advance" variable below) is always a SETTLED-REGARDLESS-OF-
         OUTCOME derivative of each call's own result (.then(onFulfilled, onRejected) with both handlers
         returning normally, so "advance" itself never rejects) -- so a fn() that rejects or throws
         still lets the NEXT queued call for that name run once it settles; a failure can never
         permanently jam a name's queue. The promise actually handed back to THIS withLock() call
         (the "outcome" variable below), by contrast, is built directly off fn()'s real result, so the
         original rejection still reaches whoever made this specific call -- only the internal chain-
         advancing copy swallows it, never the value the caller sees.
       - once a name's queue drains -- "advance" is still the map's current entry for that name at the
         moment it settles, i.e. no newer call replaced it in the meantime -- that entry is deleted, so
         _lockQueues never grows without bound across a long session. */
  var _lockQueues = {};

  function _locksFallback(name, fn) {
    var priorTail = _lockQueues[name] || Promise.resolve();
    var outcome = priorTail.then(function () { return fn(); });
    var advance = outcome.then(function () {}, function () {});
    _lockQueues[name] = advance;
    advance.then(function () {
      if (_lockQueues[name] === advance) { delete _lockQueues[name]; }
    });
    return outcome;
  }

  function locksWithLock(name, fn) {
    if (_capabilities.webLocks) {
      return navigator.locks.request(name, function (lock) { return fn(); });
    }
    return _locksFallback(name, fn);
  }

  /* Debug/introspection only -- deliberately NOT part of the documented VW.locks API surface (the
     design doc's own "VW.locks (Stage 6, new)" block names exactly one member: withLock). The
     queue-cleanup guarantee above ("_lockQueues never grows without bound") has no other externally
     observable signature: an already-settled promise chain is O(1) to build on whether or not the
     dead map entry is cleaned up, so nothing about call ORDER or TIMING would ever differ if the
     cleanup line above were silently deleted -- only long-run memory retention would. Exposing this
     one read-only count is the only way to prove that guarantee with a real executed assertion rather
     than guessing from source text; kept leading-underscore-named and off the public locks object's
     documented shape for exactly that reason. */
  function _locksDebugPendingCount() { return Object.keys(_lockQueues).length; }

  /* v1.63.0: VW.popoutControl -- A2, per-page pop-out control (multi-window support, PR 14 of
     docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 4). A1 (index.html's home-nav
     ↗ buttons, v1.55.0) pops a SECTION out from the home page; A2 is the mirror image -- a page a
     technician is ALREADY on gets its own control to pop ITSELF out into a second window, so the
     mechanic doesn't have to navigate back to the home nav first just to duplicate the page they're
     already reading onto a second monitor. Called once, zero-config, by a page's own inline script
     (adopted first on part.html/procedure.html/torque.html/jobcard.html/bench.html) -- everything it
     needs (path, query, title) is read off location/document itself, matching this file's own
     _footerNav/_staleBanner "call once, self-contained" shape rather than accepting per-page
     options that would add no real value here.

     WHY THE WINDOW NAME MUST MATCH A1's popoutName() (engine/ui/index.html, ~line 592) EXACTLY, and
     why this is not a coincidence to maintain by hand: the name is the ENTIRE mechanism VW.windows.
     open() uses to reuse a window instead of stacking up a new one, so two different pop-out controls
     for the SAME destination page have to compute the identical string or a mechanic who pops
     /torque out from the home nav and then, already on /torque, clicks THIS page's own pop-out
     control ends up with two separate "torque" windows fighting for the same monitor real estate
     instead of the second click simply refocusing the first window -- exactly the failure mode A1's
     own comment names this PR to avoid. _popoutWindowName below is therefore a deliberate
     byte-for-byte copy of index.html's popoutName(href) transform (strip the query, strip the
     hash, strip leading/trailing slashes, replace every run of anything outside [A-Za-z0-9_-] with a
     single "-", prefix "vw-", fall back to "home" for the empty/root path) -- if that transform is
     ever revised, both copies have to move together (engine/tests/test_a2_popout.py asserts the two
     source files' regex literals stay identical, specifically to catch a drift like that). Applied
     here to location.pathname (which already carries no query/hash of its own -- the same
     stripping is still applied for defensive symmetry with the href-based caller).

     v1.64.0 (B, curated workspace launcher, PR 15 of the same plan): also exported directly below as
     VW.popoutWindowName, not just used internally by popoutControl -- B opens OTHER pages (from
     jobcard.html/solve.html, neither of which IS /procedure or /torque), so it needs this same
     transform for a page it is not currently on, which popoutControl()'s own location.pathname read
     cannot give it. Exporting the existing function is a one-line addition, not a new naming rule --
     the byte-for-byte-identical-with-A1 guarantee above holds exactly the same for every caller. */
  function _popoutWindowName(pathOrHref) {
    var base = String(pathOrHref || "").split("?")[0].split("#")[0].replace(/^\/+/, "").replace(/\/+$/, "");
    return "vw-" + (base ? base.replace(/[^A-Za-z0-9_-]+/g, "-") : "home");
  }

  /* THE PALETTE-QUEUE HANDOFF (window.__paletteQueue). On every page this adopts today, shared.js
     runs first (in <head>) and palette.js runs last (just before </body>) -- but nothing here may
     assume that stays true for every future page, so this never reaches into palette.js's internal
     COMMANDS array directly (which does not exist yet on the normal load order, and reaching into
     another module's private closure state would be fragile even when it does). Instead it always
     pushes a small, plain, JSON-shaped descriptor onto a shared array on window, creating that
     array on its first use. palette.js drains this queue into COMMANDS during its own init (after
     building COMMANDS, before the palette can ever be opened/searched) AND again right before every
     open(), so a descriptor lands correctly whichever of the two real script orders this app ends up
     with on some future page -- see palette.js's _drainPaletteQueue for the other half of this. */
  function popoutControl(opts) {
    try {
      var o = opts || {};
      var path = (g.location && g.location.pathname) || "/";
      if (path === "/" || path === "/index.html" || path === "") return;   // A1 already covers home
      if (document.getElementById("vw-popout-pill")) return;                // never wired twice
      var qs = (g.location && g.location.search) || "";
      var url = path + qs;
      var name = _popoutWindowName(path);
      var title = (typeof o.title === "string" && o.title) ? o.title :
        (document.title || path).replace(/\s*[—–-]\s*THE VIEWER.*$/i, "").trim() || path;
      var label = "Open " + title + " in a new window";

      /* The ONE shared action -- the visible button and the Ctrl+K palette entry must perform
         exactly this, never two independent copies of the open call. Mirrors index.html's
         wirePopouts() fallback exactly: shared.js loads first on every adopting page, so VW.windows
         is normally right there; if it somehow is not (a failed/blocked /shared.js -- which, since
         this very function lives inside shared.js, would mean this code never ran at all, but the
         same defensive shape is kept here for consistency with every other pop-out call site and in
         case a future refactor ever calls this helper from outside this closure), fall back to a
         plain NAMED window.open() rather than leaving a dead control. */
      function doPopout() {
        if (g.VW && VW.windows && typeof VW.windows.open === "function") {
          VW.windows.open(url, { name: name });
        } else {
          try { g.open(url, name); } catch (e) { /* blocked/refused -- nothing left to do */ }
        }
      }

      function mount() {
        try {
          if (!document.body || document.getElementById("vw-popout-pill")) return;
          var b = document.createElement("button");
          b.type = "button";
          b.id = "vw-popout-pill";
          b.textContent = "↗ Pop out";
          b.setAttribute("aria-label", label);
          b.title = label;
          if (!document.querySelector('link[href="/base.css"]')) {
            b.style.cssText = "position:fixed;right:288px;bottom:12px;z-index:9998;" +
              "background:#171d26;color:#9aa6b6;border:1px solid #2b333f;border-radius:20px;" +
              "padding:10px 16px;font-size:13px;line-height:1;" +
              "font-family:-apple-system,Segoe UI,Arial,sans-serif;cursor:pointer;opacity:.85;" +
              "box-shadow:0 4px 14px rgba(0,0,0,.35);min-height:44px;display:flex;" +
              "align-items:center;box-sizing:border-box";
          }
          b.onclick = doPopout;
          document.body.appendChild(b);
        } catch (e) { /* never break the host page over a pop-out pill */ }
      }
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", mount);
      } else {
        mount();
      }

      try {
        if (!g.__paletteQueue) g.__paletteQueue = [];
        g.__paletteQueue.push({ ic: "↗", label: label,
          hint: "opens (or refocuses) this page in its own window", act: doPopout });
      } catch (e) { /* never break the host page over a palette registration */ }
    } catch (e) { /* never break the host page over the pop-out control */ }
  }

  var VW = { esc: esc, $: $, $all: $all, getJSON: getJSON, postJSON: postJSON,
             toast: toast, debounce: debounce, fmtInt: fmtInt, kioskOn: kioskOn, confTier: confTier,
             trapFocus: trapFocus, popoutControl: popoutControl, popoutWindowName: _popoutWindowName,
             channel: { publish: channelPublish, subscribe: channelSubscribe },
             workspace: { create: workspaceCreate, list: workspaceList,
                          get: workspaceGet, touch: workspaceTouch, delete: workspaceDelete,
                          exportUrl: workspaceExportUrl, exportFile: workspaceExportFile,
                          importUrl: workspaceImportUrl, importFile: workspaceImportFile,
                          /* v1.76.0: schema-versioning debug/introspection members -- deliberately
                             NOT part of the design doc's documented VW.workspace shape (same
                             leading-underscore convention as VW.locks._debugPendingCount above),
                             kept only so the migrate-or-refuse guarantees can be proven with real
                             executed assertions rather than inferred from source text alone. */
                          _schemaVersion: _WS_SCHEMA_VERSION,
                          _classifySchemaVersion: _wsClassifyRecordSchema,
                          _lastGetSchemaRefusal: function () { return _wsLastGetSchemaRefusal; },
                          _lastReadSchemaRefusals: function () { return _wsLastReadRefusals.slice(); } },
             windows: { open: windowsOpen, registry: windowsRegistry,
                        restoreLayout: windowsRestoreLayout },
             bench: { get: benchGet, put: benchPut },
             checkpoint: { get: checkpointGet, clear: checkpointClear },
             capabilities: _capabilities,
             locks: { withLock: locksWithLock, _debugPendingCount: _locksDebugPendingCount } };
  g.VW = VW;
  /* Back-compat: expose the classic names only when the page doesn't define its own. */
  if (g.esc === undefined) g.esc = esc;
  if (g.toast === undefined) g.toast = toast;
  if (g.viewerKioskOn === undefined) g.viewerKioskOn = kioskOn;
}(typeof window !== "undefined" ? window : this));
