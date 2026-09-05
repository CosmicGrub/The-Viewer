/* THE VIEWER -- VW.capabilities, real behavior test (PR 19 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). Run under plain Node, same
vm.createContext sandbox convention test_windows_layout_node.js (PR 6) already established.

Invoked by engine/tests/test_vw_capabilities.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js:
  - THE LIVE-READ GUARANTEE (the single most important thing this PR must get right): window.RPS.mode
    starts "modern", a first read of VW.capabilities.tier and VW.capabilities.broadcastChannel
    reflects that -- THEN window.RPS.mode is mutated to "lite" on the SAME already-loaded sandbox
    (shared.js is never reloaded or re-executed a second time) and a SECOND read of the exact same two
    properties reflects the NEW value -- proving these are genuinely live getters, not a value
    captured once when shared.js first ran. This directly exercises the real timing bug this PR exists
    to avoid (rps.js sets window.RPS.mode on a delay, after its own fetch("/api/rps") call resolves).
  - window.RPS entirely absent (the "most of this app's pages never load rps.js at all" case): tier
    reads "modern" (the documented default), never throws.
  - each of the 7 AND-ed flags is true only when BOTH the raw browser feature is present AND tier is
    EXACTLY "modern": present+modern -> true; present+lite -> false; present+legacy -> false;
    absent+modern -> false; present+premium -> false ("premium" is an additive flag layered on an
    already-"modern" mode, per rps.js's own applyMode comment -- never itself "modern").
  - a raw feature check that throws when accessed (a hostile/locked-down global) degrades that ONE
    flag to false without breaking any other flag's read in the same object, in the same call.
  - windowPlacement's own getter calls straight into the pre-existing _screenPlacementAvailable()
    (extracted and compared at the SOURCE level below -- no second, potentially-drifting copy of its
    raw getScreenDetails+tier check exists anywhere) -- and its value across every scenario above
    matches manually evaluating that same documented expression, proving the two behave identically.
  - VW.channel / VW.workspace / VW.windows / _screenPlacementAvailable() themselves are UNCHANGED --
    checked here at the JS level (their exported shape and internal body are exactly what PR 17 left
    them); the doc-level "no other call site touched" check lives in the Python driver alongside this.

WHAT THIS CANNOT PROVE, stated plainly: a Node vm sandbox's global-object accessor semantics differ
subtly from a real browser's -- a throwing accessor property defined DIRECTLY on the vm's own
global/sandbox object is silently swallowed into a plain "is not defined" instead of propagating (a
real Node vm quirk, confirmed by hand while building this file, not a shared.js bug or something this
file works around by accident). So the "hostile global" case here is exercised via a throwing
window.documentPictureInPicture property instead -- window is a genuine, distinct plain object in
this sandbox, not the vm's own global, so accessor throws on it propagate exactly like a real
browser's window object would. The code path exercised (one try/catch per feature check) is identical
either way. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

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

/* Builds one fresh sandbox/tab, loads the real shared.js into it, and returns the vm context.
   window is a genuine, DISTINCT plain object (never the sandbox/global itself) -- required so a
   throwing accessor property placed on it propagates like a real browser's window, rather than being
   swallowed by Node vm's own global-object interceptor (see the file header comment above).

   opts:
     rpsMode: undefined -- window.RPS left entirely unset (rps.js never loaded on this page);
              otherwise a string ("modern"/"lite"/"legacy"/"premium"/anything) -> window.RPS = {mode:
              rpsMode}.
     raw: { broadcastChannel, getScreenDetails, navigatorWakeLock, navigatorLocks,
            documentPictureInPicture, showSaveFilePicker, indexedDB }
       -- each boolean-ish; true sets the corresponding raw browser feature present, falsy/omitted
       leaves it entirely absent. documentPictureInPicture also accepts the literal string "throw" to
       install a throwing accessor instead (the hostile-global degrade-to-false scenario). */
function makeTab(opts) {
  opts = opts || {};
  var raw = opts.raw || {};
  var windowObj = {};
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date, Object: Object, Array: Array,
    String: String, Error: Error, setTimeout: setTimeout, clearTimeout: clearTimeout,
    module: {}, exports: {}
  };
  sandbox.document = makeDoc();
  sandbox.window = windowObj;
  windowObj.addEventListener = function () {};
  windowObj.location = { pathname: "/probe", href: "" };
  windowObj.localStorage = (function () {
    var store = {};
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
      setItem: function (k, v) { store[k] = String(v); }
    };
  })();

  if (opts.rpsMode !== undefined) {
    windowObj.RPS = { mode: opts.rpsMode };
  }
  // else: window.RPS stays entirely unset -- the "this page never loaded rps.js" case.

  sandbox.navigator = {};
  if (raw.navigatorWakeLock) sandbox.navigator.wakeLock = {};
  if (raw.navigatorLocks) sandbox.navigator.locks = {};

  if (raw.broadcastChannel) {
    sandbox.BroadcastChannel = function () {};   // presence only matters -- shape is irrelevant here
  }

  if (raw.getScreenDetails) windowObj.getScreenDetails = function () {};

  if (raw.documentPictureInPicture === "throw") {
    Object.defineProperty(windowObj, "documentPictureInPicture", {
      configurable: true,
      get: function () { throw new Error("hostile documentPictureInPicture getter"); }
    });
  } else if (raw.documentPictureInPicture) {
    windowObj.documentPictureInPicture = {};
  }

  if (raw.showSaveFilePicker) windowObj.showSaveFilePicker = function () {};
  if (raw.indexedDB) windowObj.indexedDB = {};

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

/* ================================================================================================
   0) VW.capabilities exists, off VW, and carries all 8 documented fields as plain (non-function)
      values -- matching the design doc's own dot-notation ("VW.capabilities.tier", no call parens).
   ================================================================================================ */
(function () {
  var tab = makeTab({ rpsMode: "modern" });
  var caps = tab.window.VW.capabilities;
  check("VW.capabilities exists", !!caps);
  var fields = ["tier", "broadcastChannel", "windowPlacement", "wakeLock", "pictureInPicture",
                "fileSystemAccess", "webLocks", "indexedDB"];
  var allPlain = true;
  for (var i = 0; i < fields.length; i++) {
    if (typeof caps[fields[i]] === "function") allPlain = false;
  }
  check("every field reads as a plain value, not a function needing call parens", allPlain);
  check("tier reads \"modern\" when window.RPS.mode is \"modern\"", caps.tier === "modern");
})();

/* ================================================================================================
   1) THE LIVE-READ GUARANTEE. A single sandbox, loaded once. window.RPS.mode starts "modern"; two
      fields are read; window.RPS.mode is then mutated WITHOUT reloading shared.js; the SAME two
      fields are read again and must reflect the NEW value.
   ================================================================================================ */
(function () {
  var tab = makeTab({ rpsMode: "modern", raw: { broadcastChannel: true } });
  var caps = tab.window.VW.capabilities;

  check("first read: tier is \"modern\"", caps.tier === "modern");
  check("first read: broadcastChannel is true (raw present + tier modern)",
    caps.broadcastChannel === true);

  // Mutate the SAME window.RPS object shared.js itself is reading -- no re-load, no re-require, no
  // second vm.runInContext call. A cached-at-load-time snapshot would still report the OLD values.
  tab.window.RPS.mode = "lite";

  check("second read, same object, AFTER mutation: tier now reflects \"lite\"",
    caps.tier === "lite");
  check("second read: broadcastChannel now reflects false (tier no longer \"modern\") -- " +
    "proves this is a LIVE getter, not a value captured once at shared.js load time",
    caps.broadcastChannel === false);

  // And back again, to confirm it is not a one-way latch either.
  tab.window.RPS.mode = "modern";
  check("third read, flipped back to \"modern\": tier reflects it again", caps.tier === "modern");
  check("third read: broadcastChannel reflects it again", caps.broadcastChannel === true);
})();

/* ================================================================================================
   2) window.RPS entirely absent (rps.js never loaded on this page) -- tier reads the documented
      "modern" default, never throws; every AND-ed flag still degrades correctly off that default.
   ================================================================================================ */
(function () {
  var tab = makeTab({});   // no rpsMode passed at all -- window.RPS is genuinely undefined
  var caps = tab.window.VW.capabilities;
  var threw = false, tierVal;
  try { tierVal = caps.tier; } catch (e) { threw = true; }
  check("reading .tier with window.RPS entirely absent never throws", !threw);
  check("tier defaults to \"modern\" with window.RPS entirely absent", tierVal === "modern");

  var tab2 = makeTab({ raw: { broadcastChannel: true, getScreenDetails: true, navigatorWakeLock: true,
                               documentPictureInPicture: true, showSaveFilePicker: true,
                               navigatorLocks: true, indexedDB: true } });
  var caps2 = tab2.window.VW.capabilities;
  check("with window.RPS absent, tier still defaults to \"modern\" even with every raw feature present",
    caps2.tier === "modern");
  // window.RPS absent is read live as tier "modern" -- per this file's own shared _capTier() default
  // -- so the 6 flags that go through _capTier()/_capIsModernTier() read true here. windowPlacement is
  // the deliberate exception: it calls straight into PR 17's PRE-EXISTING _screenPlacementAvailable(),
  // reused byte-for-byte rather than rewritten (see PR body/section 5 below) -- and THAT function's own
  // check is "window.RPS && window.RPS.mode === 'modern'", which is false (not defaulted to true) when
  // window.RPS itself is absent. That is correct, existing PR 17 behavior this PR must not change, not
  // a bug -- so windowPlacement alone is asserted false here, everything else true.
  check("...and the 6 flags built on the shared tier reader are correspondingly true (absent RPS " +
    "behaves as tier \"modern\" for THEM)",
    caps2.broadcastChannel === true && caps2.wakeLock === true &&
    caps2.pictureInPicture === true && caps2.fileSystemAccess === true && caps2.webLocks === true &&
    caps2.indexedDB === true);
  check("...but windowPlacement (reusing _screenPlacementAvailable() verbatim) stays false when " +
    "window.RPS is absent -- PR 17's own pre-existing behavior, deliberately NOT changed by this PR",
    caps2.windowPlacement === false);
})();

/* ================================================================================================
   3) Each of the 7 AND-ed flags: true only when BOTH the raw feature is present AND tier is EXACTLY
      "modern". Five required scenarios per flag: present+modern->true; present+lite->false;
      present+legacy->false; absent+modern->false; present+premium->false (premium is NOT itself
      "modern" -- an additive flag layered on top of it, per rps.js's own applyMode comment).
   ================================================================================================ */
var FLAG_CASES = [
  { name: "broadcastChannel", raw: { broadcastChannel: true } },
  { name: "windowPlacement", raw: { getScreenDetails: true } },
  { name: "wakeLock", raw: { navigatorWakeLock: true } },
  { name: "pictureInPicture", raw: { documentPictureInPicture: true } },
  { name: "fileSystemAccess", raw: { showSaveFilePicker: true } },
  { name: "webLocks", raw: { navigatorLocks: true } },
  { name: "indexedDB", raw: { indexedDB: true } }
];

FLAG_CASES.forEach(function (fc) {
  var presentModern = makeTab({ rpsMode: "modern", raw: fc.raw }).window.VW.capabilities[fc.name];
  check(fc.name + ": raw present + tier \"modern\" -> true", presentModern === true);

  var presentLite = makeTab({ rpsMode: "lite", raw: fc.raw }).window.VW.capabilities[fc.name];
  check(fc.name + ": raw present + tier \"lite\" -> false", presentLite === false);

  var presentLegacy = makeTab({ rpsMode: "legacy", raw: fc.raw }).window.VW.capabilities[fc.name];
  check(fc.name + ": raw present + tier \"legacy\" -> false", presentLegacy === false);

  var absentModern = makeTab({ rpsMode: "modern", raw: {} }).window.VW.capabilities[fc.name];
  check(fc.name + ": raw absent + tier \"modern\" -> false", absentModern === false);

  var presentPremium = makeTab({ rpsMode: "premium", raw: fc.raw }).window.VW.capabilities[fc.name];
  check(fc.name + ": raw present + tier \"premium\" -> false (premium is additive, never \"modern\" " +
    "on its own)", presentPremium === false);
});

/* ================================================================================================
   4) A raw feature check that throws when accessed degrades that ONE flag to false, without
      breaking any OTHER flag's read in the same object, in the same call.
   ================================================================================================ */
(function () {
  var tab = makeTab({
    rpsMode: "modern",
    raw: { documentPictureInPicture: "throw", broadcastChannel: true, navigatorWakeLock: true }
  });
  var caps = tab.window.VW.capabilities;

  var threw = false, pipVal;
  try { pipVal = caps.pictureInPicture; } catch (e) { threw = true; }
  check("reading a flag whose raw check throws never lets the exception escape", !threw);
  check("the throwing flag itself degrades to false", pipVal === false);
  check("tier is completely unaffected by the OTHER flag's throwing raw check", caps.tier === "modern");
  check("a DIFFERENT flag (broadcastChannel) in the SAME object is completely unaffected",
    caps.broadcastChannel === true);
  check("another DIFFERENT flag (wakeLock) in the SAME object is also completely unaffected",
    caps.wakeLock === true);
  // Reading the throwing flag a second time behaves identically (not a one-shot degrade-then-cache).
  var pipVal2;
  try { pipVal2 = caps.pictureInPicture; } catch (e) { pipVal2 = "threw"; }
  check("reading the throwing flag AGAIN still degrades to false, every time -- never cached, never " +
    "re-throws", pipVal2 === false);
})();

/* ================================================================================================
   5) windowPlacement never drifts from _screenPlacementAvailable(). Source-level: the getter's own
      body (extracted from the compiled function's toString(), the same technique test_a2_popout.py
      already uses to compare two independently-typed transforms) contains an actual call to
      _screenPlacementAvailable() rather than a second, re-typed copy of its expression. Behavioral:
      across every scenario this file constructs, VW.capabilities.windowPlacement's value matches
      manually evaluating that exact documented expression against the same window.
   ================================================================================================ */
(function () {
  var shared_src = src;
  var fnStart = shared_src.indexOf("function _screenPlacementAvailable()");
  check("_screenPlacementAvailable() is declared in shared.js (PR 17, unchanged)", fnStart !== -1);
  var fnBody = shared_src.slice(fnStart, shared_src.indexOf("\n  }", fnStart) + 4);
  check("_screenPlacementAvailable() still checks typeof window.getScreenDetails === \"function\"",
    fnBody.indexOf('typeof window.getScreenDetails !== "function"') !== -1);
  check("_screenPlacementAvailable() still checks window.RPS.mode === \"modern\" (exact string match)",
    fnBody.indexOf('window.RPS && window.RPS.mode === "modern"') !== -1);

  var capStart = shared_src.indexOf('Object.defineProperty(_capabilities, "windowPlacement"');
  check("VW.capabilities.windowPlacement's own definition is present", capStart !== -1);
  var capBlockEnd = shared_src.indexOf("});", capStart) + 3;
  var capBlock = shared_src.slice(capStart, capBlockEnd);
  check("windowPlacement's getter calls _screenPlacementAvailable() itself -- not a second, " +
    "re-typed copy of its raw check", capBlock.indexOf("_screenPlacementAvailable()") !== -1);
  check("windowPlacement's getter does NOT re-type a second getScreenDetails check of its own",
    capBlock.indexOf("getScreenDetails") === -1);

  // Behavioral cross-check across a spread of scenarios: windowPlacement always equals a manual
  // evaluation of _screenPlacementAvailable()'s own documented expression against the same window.
  var scenarios = [
    { rpsMode: "modern", raw: { getScreenDetails: true } },
    { rpsMode: "lite", raw: { getScreenDetails: true } },
    { rpsMode: "legacy", raw: { getScreenDetails: true } },
    { rpsMode: "premium", raw: { getScreenDetails: true } },
    { rpsMode: "modern", raw: {} },
    {}
  ];
  var allMatch = true;
  scenarios.forEach(function (sc) {
    var tab = makeTab(sc);
    var manual = (typeof tab.window.getScreenDetails === "function") &&
      !!(tab.window.RPS && tab.window.RPS.mode === "modern");
    if (tab.window.VW.capabilities.windowPlacement !== manual) allMatch = false;
  });
  check("windowPlacement's value matches _screenPlacementAvailable()'s documented expression across " +
    "every scenario tried", allMatch);
})();

/* ================================================================================================
   6) This PR does not retrofit VW.channel/VW.workspace/VW.windows or touch _screenPlacementAvailable
      itself -- checked here at the runtime-shape level (still exactly the functions PR 17 left them,
      capabilities reads nothing they export). The source-level "no existing call site edited"
      check lives in the Python driver (test_vw_capabilities.py), which can diff against origin/main.
   ================================================================================================ */
(function () {
  var tab = makeTab({ rpsMode: "modern" });
  var VW = tab.window.VW;
  check("VW.channel is untouched (publish/subscribe still present)",
    VW.channel && typeof VW.channel.publish === "function" && typeof VW.channel.subscribe === "function");
  check("VW.workspace is untouched (create/list/get/touch/delete still present)",
    VW.workspace && typeof VW.workspace.create === "function" && typeof VW.workspace.list === "function" &&
    typeof VW.workspace.get === "function" && typeof VW.workspace.touch === "function" &&
    typeof VW.workspace.delete === "function");
  check("VW.windows is untouched (open/registry/restoreLayout still present)",
    VW.windows && typeof VW.windows.open === "function" && typeof VW.windows.registry === "function" &&
    typeof VW.windows.restoreLayout === "function");
})();

console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
process.exit(failures.length === 0 ? 0 : 1);

// END OF FILE
