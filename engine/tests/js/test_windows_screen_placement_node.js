/* THE VIEWER -- C: screen-aware placement, real behavior test (PR 17 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 5). Run under plain Node, same
dual-sandbox convention test_windows_node.js (PR 5) and test_windows_layout_node.js (PR 6) already
established.

Invoked by engine/tests/test_windows_screen_placement.py via `node this-file.js`; prints PASS/FAIL
lines and exits 1 on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js:
  - opts.screen ABSENT never calls window.getScreenDetails() at all -- the single most important
    guarantee given this feature's own stated permission philosophy: a caller who never asks for
    screen placement must never see a permission prompt.
  - opts.screen present but typeof window.getScreenDetails !== "function" -> silent no-op, the window
    still opens normally through the existing synchronous path, no throw.
  - opts.screen present, API present, but window.RPS.mode is "lite"/"legacy" -> still skipped (the
    tier gate is honored); window.RPS undefined entirely -> also skipped, never throws.
  - opts.screen present, API present, window.RPS.mode === "modern", getScreenDetails() resolves with
    2+ screens -> win.moveTo() is called with a DIFFERENT screen's bounds than currentScreen's.
  - getScreenDetails() resolves with only 1 screen -> no move is attempted (nothing to move to).
  - getScreenDetails() REJECTS (permission denied) -> caught silently: no throw, no unhandled
    rejection anywhere in the process, and the window handle already returned synchronously is
    unaffected.
  - getScreenDetails() itself THROWS SYNCHRONOUSLY (e.g. a spec-compliant browser refusing a call
    outside a user gesture) -> also caught silently, same guarantees.
  - window.open() happens SYNCHRONOUSLY, strictly before any getScreenDetails() call -- proven by the
    ORDER of operations via a shared call-order log both mocks push into, not just by the end state.

WHAT THIS CANNOT PROVE, stated plainly rather than glossed over: whether a real Chromium browser's
actual permission prompt behaves this way, whether win.moveTo() actually lands the window on the
correct physical monitor, and whether a real multi-monitor OS/window-manager honors moveTo() at all in
every configuration. Node has no getScreenDetails, no window.open, and no real screens to be right or
wrong about any of that. Confirming the actual on-screen placement needs a human on a real
multi-monitor Chromium machine -- called out as manual in the PR body, the same honest framing every
other real-hardware-only behavior in this initiative already uses.

Gracefully skips (never false-fails) in an environment without node, same as the rest of this
codebase's node-dependent checks (enforced by the calling .py file, not here). */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

// Any unhandled promise rejection anywhere in this process is a hard failure of this whole file's
// central guarantee ("a denial is caught silently, never an unhandled rejection") -- caught globally,
// not just per-test, since an unhandled rejection can surface asynchronously after the test that
// triggered it already finished checking its own synchronous assertions.
var unhandledRejections = [];
process.on("unhandledRejection", function (err) {
  unhandledRejections.push(err);
});

function makeDoc() {
  var byId = {};
  function el(tag) {
    var e = {
      tagName: tag, id: "", className: "", style: {}, attrs: {},
      setAttribute: function (k, v) { e.attrs[k] = v; },
      appendChild: function (c) { if (c && c.id) byId[c.id] = c; },
      querySelector: function () { return null; },
      querySelectorAll: function () { return []; },
      addEventListener: function () {}
    };
    var text = "";
    Object.defineProperty(e, "textContent", {
      get: function () { return text; },
      set: function (v) { text = v; }
    });
    return e;
  }
  var body = el("body");
  return {
    readyState: "complete",
    getElementById: function (id) { return byId[id] || null; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    createElement: el,
    addEventListener: function () {},
    body: body, head: el("head"), documentElement: el("html")
  };
}

/* window.open mock -- same shape as PR 5/PR 6's own mocks, extended with an optional shared `order`
   log (pushed to on every real call) and a moveTo/resizeTo spy on every handle it hands back, so a
   test can assert what screen-placement code actually did to an already-open window. */
function makeOpener(order) {
  var named = {};
  var api = {
    calls: [],
    open: function (url, name, features) {
      if (order) order.push("window.open");
      api.calls.push({ url: url, name: name, features: features, argc: arguments.length });
      if (name && named[name] && named[name].closed !== true) {
        named[name].url = url;
        return named[name];
      }
      var h = { closed: false, url: url, name: name || null, moveToCalls: 0, resizeToCalls: 0 };
      h.focus = function () {};
      h.moveTo = function (x, y) { h.moveToCalls++; h.movedTo = { x: x, y: y }; };
      h.resizeTo = function (w, ht) { h.resizeToCalls++; h.resizedTo = { w: w, h: ht }; };
      if (name) named[name] = h;
      return h;
    }
  };
  return api;
}

/* getScreenDetails mock factory. `behavior`:
     { screens: [...], current: <one of screens> }  -> resolves with that ScreenDetails shape
     { reject: true }                                -> rejects (permission denied)
     { throwSync: true }                              -> the CALL ITSELF throws, no promise at all
   Every call is logged onto the shared `order` array (when provided) and counted on `.callCount`. */
function makeGetScreenDetails(order, behavior) {
  var fn = function () {
    fn.callCount++;
    if (order) order.push("getScreenDetails");
    if (behavior && behavior.throwSync) { throw new Error("getScreenDetails: no active user gesture"); }
    return new Promise(function (resolve, reject) {
      if (behavior && behavior.reject) { reject(new Error("permission denied")); return; }
      resolve({ screens: (behavior && behavior.screens) || [], currentScreen: behavior && behavior.current });
    });
  };
  fn.callCount = 0;
  return fn;
}

/* Builds one sandboxed "tab" running the real production shared.js.
   opts: { opener, rps (undefined | {mode: "..."} | "OMIT"), getScreenDetails (function | undefined) } */
function makeTab(opts) {
  opts = opts || {};
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date, Object: Object, Array: Array,
    String: String, Error: Error, Promise: Promise, setTimeout: setTimeout, clearTimeout: clearTimeout,
    BroadcastChannel: BroadcastChannel, module: {}, exports: {}
  };
  sandbox.document = makeDoc();
  sandbox.window = sandbox;
  sandbox.window.addEventListener = function () {};
  sandbox.window.location = { pathname: "/probe", href: "" };
  sandbox.window.localStorage = (function () {
    var store = {};
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
      setItem: function (k, v) { store[k] = String(v); }
    };
  })();
  sandbox.window.screen = { availWidth: 1920, availHeight: 1080 };
  if (opts.opener) sandbox.window.open = opts.opener.open;
  if (typeof opts.rps !== "undefined" && opts.rps !== "OMIT") sandbox.window.RPS = opts.rps;
  // opts.rps === "OMIT" (or simply not passed) leaves window.RPS genuinely undefined, matching a
  // page that never loaded rps.js -- the real-world case this PR must treat exactly like "not modern".
  if (typeof opts.getScreenDetails === "function") sandbox.window.getScreenDetails = opts.getScreenDetails;
  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
  return ctx;
}

var failures = [];
var total = 0;
function check(name, cond) {
  total++;
  if (!cond) failures.push(name);
  console.log((cond ? "PASS " : "FAIL ") + name);
}

function afterAsync(fn) {
  setTimeout(fn, 50);
}

/* ================================================================================================
   1) opts.screen ABSENT -> getScreenDetails is NEVER called. The single most important guarantee:
      a caller who never asks for placement must never trigger a permission prompt.
   ================================================================================================ */
(function () {
  var order = [];
  var opener = makeOpener(order);
  var gsd = makeGetScreenDetails(order, { screens: [{ left: 0, top: 0 }, { left: 1920, top: 0 }] });
  var tab = makeTab({ opener: opener, rps: { mode: "modern" }, getScreenDetails: gsd });

  var w = tab.VW.windows.open("/torque.html", { name: "vw-noscreen-opt" });
  check("opts.screen absent still opens the window normally", !!w);
  check("opts.screen absent -> getScreenDetails is NEVER called (no permission prompt possible)",
    gsd.callCount === 0 && order.indexOf("getScreenDetails") === -1);

  // Same, with opts present but explicitly falsy -- must behave identically to fully absent.
  var w2 = tab.VW.windows.open("/torque2.html", { name: "vw-falsyscreen", screen: false });
  check("opts.screen: false also never calls getScreenDetails", gsd.callCount === 0);
  var w3 = tab.VW.windows.open("/torque3.html", { name: "vw-nullscreen", screen: null });
  check("opts.screen: null also never calls getScreenDetails", gsd.callCount === 0 && !!w2 && !!w3);
})();

/* ================================================================================================
   2) opts.screen present but getScreenDetails is not a function at all (API absent) -> silent
      no-op, the window still opens normally via the existing path, no throw.
   ================================================================================================ */
(function () {
  var opener = makeOpener();
  var tab = makeTab({ opener: opener, rps: { mode: "modern" } });   // no getScreenDetails at all

  var threw = false, w;
  try { w = tab.VW.windows.open("/part.html", { name: "vw-noapi", screen: true }); }
  catch (e) { threw = true; }

  check("opts.screen with the API absent never throws", !threw);
  check("opts.screen with the API absent still opens the window normally", !!w);
})();

/* ================================================================================================
   3) tier gate: window.RPS.mode "lite"/"legacy" -> skipped; window.RPS undefined -> also skipped.
      Never throws in any of these cases.
   ================================================================================================ */
(function () {
  var cases = [
    { label: "lite", rps: { mode: "lite" } },
    { label: "legacy", rps: { mode: "legacy" } },
    { label: "window.RPS entirely undefined (a page that never loaded rps.js)", rps: "OMIT" }
  ];
  cases.forEach(function (c) {
    var order = [];
    var opener = makeOpener(order);
    var gsd = makeGetScreenDetails(order, { screens: [{ left: 0, top: 0 }, { left: 1920, top: 0 }] });
    var tab = makeTab({ opener: opener, rps: c.rps, getScreenDetails: gsd });

    var threw = false, w;
    try { w = tab.VW.windows.open("/torque.html", { name: "vw-tier-" + c.label.replace(/\W+/g, "_"), screen: true }); }
    catch (e) { threw = true; }

    check("tier gate (" + c.label + "): never throws", !threw);
    check("tier gate (" + c.label + "): window still opens normally", !!w);
    check("tier gate (" + c.label + "): getScreenDetails is never called (not modern tier)",
      gsd.callCount === 0);
  });

  // "premium" is a FLAG layered on top of an already-"modern" mode, never a mode value of its own
  // (rps.js's own applyMode comment / rps.py's VALID_MODES) -- confirms the exact-string-match
  // reasoning: a mode string that happens to be the word "premium" itself (not a real server value,
  // but checked here defensively) must NOT be treated as "modern".
  var orderP = [];
  var openerP = makeOpener(orderP);
  var gsdP = makeGetScreenDetails(orderP, { screens: [{ left: 0, top: 0 }, { left: 1920, top: 0 }] });
  var tabP = makeTab({ opener: openerP, rps: { mode: "premium" }, getScreenDetails: gsdP });
  var wP = tabP.VW.windows.open("/torque.html", { name: "vw-tier-premium-string", screen: true });
  check("a literal RPS.mode of \"premium\" (never real, but checked defensively) is NOT treated as modern",
    !!wP && gsdP.callCount === 0);
})();

/* ================================================================================================
   4) modern tier, API present, getScreenDetails() resolves with 2+ screens -> win.moveTo() is
      called with the OTHER screen's bounds, never currentScreen's own.
   ================================================================================================ */
(function (done) {
  var order = [];
  var opener = makeOpener(order);
  var current = { left: 0, top: 0, availLeft: 0, availTop: 0, availWidth: 1920, availHeight: 1080 };
  var other = { left: 1920, top: 0, availLeft: 1920, availTop: 40, availWidth: 1920, availHeight: 1040 };
  var gsd = makeGetScreenDetails(order, { screens: [current, other], current: current });
  var tab = makeTab({ opener: opener, rps: { mode: "modern" }, getScreenDetails: gsd });

  var w = tab.VW.windows.open("/torque.html", { name: "vw-2screens", screen: true });
  check("a real window handle is returned synchronously, before the promise ever resolves", !!w);

  afterAsync(function () {
    check("getScreenDetails() was called exactly once", gsd.callCount === 1);
    check("win.moveTo() was called exactly once", w.moveToCalls === 1);
    check("win.moveTo() was called with the OTHER screen's bounds (availLeft/availTop), not current's",
      w.movedTo && w.movedTo.x === other.availLeft && w.movedTo.y === other.availTop);
    check("win.moveTo() was NOT called with currentScreen's own bounds",
      !(w.movedTo && w.movedTo.x === current.availLeft && w.movedTo.y === current.availTop));
    done();
  });
})(function () { afterTest4(); });

/* ================================================================================================
   5) getScreenDetails() resolves with only ONE screen -> no move is attempted at all.
   ================================================================================================ */
function afterTest4() {
  (function (done) {
    var order = [];
    var opener = makeOpener(order);
    var only = { left: 0, top: 0, availLeft: 0, availTop: 0, availWidth: 1920, availHeight: 1080 };
    var gsd = makeGetScreenDetails(order, { screens: [only], current: only });
    var tab = makeTab({ opener: opener, rps: { mode: "modern" }, getScreenDetails: gsd });

    var w = tab.VW.windows.open("/torque.html", { name: "vw-1screen", screen: true });
    check("single-screen case still opens the window normally", !!w);

    afterAsync(function () {
      check("getScreenDetails() was called (the gate passed) despite only one screen existing",
        gsd.callCount === 1);
      check("win.moveTo() was NEVER called -- nothing to move to with only one screen",
        w.moveToCalls === 0);
      done();
    });
  })(function () { afterTest5(); });
}

/* ================================================================================================
   6) getScreenDetails() REJECTS (permission denied) -> caught silently: no throw at the call site,
      no unhandled rejection anywhere in the process, and the already-returned window is unaffected.
   ================================================================================================ */
function afterTest5() {
  (function (done) {
    var order = [];
    var opener = makeOpener(order);
    var gsd = makeGetScreenDetails(order, { reject: true });
    var tab = makeTab({ opener: opener, rps: { mode: "modern" }, getScreenDetails: gsd });

    var threw = false, w;
    try { w = tab.VW.windows.open("/torque.html", { name: "vw-rejected", screen: true }); }
    catch (e) { threw = true; }

    check("a getScreenDetails() rejection never throws at the windowsOpen() call site", !threw);
    check("the window handle is already real and returned synchronously, unaffected by the pending rejection",
      !!w);

    afterAsync(function () {
      check("win.moveTo() was never called after a rejected getScreenDetails()", w.moveToCalls === 0);
      check("the rejection produced NO unhandled promise rejection anywhere in the process",
        unhandledRejections.length === 0);
      done();
    });
  })(function () { afterTest6(); });
}

/* ================================================================================================
   7) getScreenDetails() itself throws SYNCHRONOUSLY (e.g. called outside an active user gesture,
      per spec) -> also caught silently, same guarantees as a rejection.
   ================================================================================================ */
function afterTest6() {
  var order = [];
  var opener = makeOpener(order);
  var gsd = makeGetScreenDetails(order, { throwSync: true });
  var tab = makeTab({ opener: opener, rps: { mode: "modern" }, getScreenDetails: gsd });

  var threw = false, w;
  try { w = tab.VW.windows.open("/torque.html", { name: "vw-throwsync", screen: true }); }
  catch (e) { threw = true; }

  check("getScreenDetails() throwing synchronously never escapes windowsOpen()", !threw);
  check("the window still opened normally despite the synchronous throw", !!w);

  afterAsync(function () { afterTest7(); });
}

/* ================================================================================================
   8) window.open() happens SYNCHRONOUSLY, strictly before getScreenDetails() -- proven by the
      ORDER of a shared call-order log, not just by the end state. Checked immediately after the
      open() call returns, with NO setTimeout wait: if getScreenDetails() were awaited/then()d
      before window.open() (the exact bug this PR's design exists to prevent), this would catch it
      even before any promise had a chance to resolve.
   ================================================================================================ */
function afterTest7() {
  var order = [];
  var opener = makeOpener(order);
  var gsd = makeGetScreenDetails(order,
    { screens: [{ left: 0, top: 0 }, { left: 1920, top: 0 }], current: { left: 0, top: 0 } });
  var tab = makeTab({ opener: opener, rps: { mode: "modern" }, getScreenDetails: gsd });

  tab.VW.windows.open("/torque.html", { name: "vw-order", screen: true });

  check("window.open() and getScreenDetails() were both called", order.length === 2);
  check("window.open() happened SYNCHRONOUSLY, strictly BEFORE getScreenDetails() -- the exact " +
    "ordering this PR's whole design exists to guarantee (a popup blocker sees a real user gesture)",
    order[0] === "window.open" && order[1] === "getScreenDetails");

  finish();
}

function finish() {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}
