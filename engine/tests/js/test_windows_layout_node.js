/* THE VIEWER -- VW.windows layout capture + restore, real behavior test (PR 6 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 2). Run under plain Node, same
dual-sandbox convention test_windows_node.js (PR 5) already established.

Invoked by engine/tests/test_windows_layout.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js:
  - windowsRegistry() reads screenX/screenY/outerWidth/outerHeight LIVE off the tracked window
    handle at call time, not a value captured once at open-time and cached: the SAME handle's
    properties are mutated between two registry() calls and the second call reflects the new values.
  - a window handle whose bounds properties throw on access degrades ONLY the unreadable field(s) to
    null, and ONLY for that one window -- a second, healthy, tracked window's entry is completely
    unaffected in the SAME registry() call.
  - windowsOpen() with an implausible bounds hint (left far beyond any reasonable multi-monitor span
    for this screen) never throws, still opens the window, and simply never threads a features
    argument into window.open() at all -- the mock sees the same 1/2-argument call shape PR 5's own
    test already asserts for the no-hint case.
  - windowsOpen() with a sane bounds hint on a genuinely NEW named open DOES thread a real
    "left=..,top=..,width=..,height=.." features string into window.open()'s third argument.
  - windowsOpen() reusing an already-tracked name NEVER threads a features argument, even when a
    caller passes bounds hints on the reusing call -- reuse never attempts to reposition.
  - an unreadable/throwing window.screen (or one with a non-positive availWidth/availHeight) drops
    every hint gracefully -- never throws, still opens normally.
  - restoreLayout(entries) calls through windowsOpen() -- the SAME open/reuse/toast/broadcast path,
    not a second copy of it (proven by the SAME broadcast envelope shape and count landing on a
    genuinely separate listener tab) -- once per well-formed entry, translating screenX/screenY/
    outerWidth/outerHeight into windowsOpen()'s own left/top/width/height opts; a malformed entry
    (missing name or url) is skipped, never thrown over, and does not abort the rest of the batch;
    the returned array carries one result per INPUT entry, same order, {name, url, ok, reused}.

WHAT THIS CANNOT PROVE, stated plainly: whether a real browser actually honors window.open()'s
position/size features on a genuinely new window, and whether it genuinely ignores them on a reuse
(both named as real, honest, browser-territory limitations in shared.js's own comment and in the PR
body) -- there is no window.open in Node to be right or wrong about either. Also not provable here:
the "monitor unplugged since the position was saved" fallback actually LOOKING right without a real
second monitor, beyond the data-shape guarantee that a stale hint is dropped rather than used. */
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

/* The window.open mock -- records url/name/features/argc on every call, mirrors the browser's own
   named-window table (same name -> same handle unless closed), same convention as PR 5's own mock,
   extended to also record whatever the THIRD (features) argument was. */
function makeOpener() {
  var named = {};
  var api = {
    calls: [],
    blocked: false,
    thrower: false,
    handles: [],
    open: function (url, name, features) {
      api.calls.push({ url: url, name: name, features: features, argc: arguments.length });
      if (api.thrower) throw new Error("simulated: window.open refused");
      if (api.blocked) return null;
      if (name && named[name] && named[name].closed !== true) {
        named[name].url = url;
        return named[name];
      }
      var h = { closed: false, url: url, name: name || null };
      h.focus = function () {};
      api.handles.push(h);
      if (name) named[name] = h;
      return h;
    }
  };
  return api;
}

/* screen: undefined -> a normal 1920x1080 default; null -> no window.screen property at all
   (tests the "screen unreadable" fallback); an object -> used verbatim (a throwing getter, a
   non-positive availWidth, etc.). */
function makeTab(opener, screen) {
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date, Object: Object, Array: Array,
    String: String, Error: Error, setTimeout: setTimeout, clearTimeout: clearTimeout,
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
  if (screen === undefined) {
    sandbox.window.screen = { availWidth: 1920, availHeight: 1080 };
  } else if (screen !== null) {
    sandbox.window.screen = screen;
  }
  if (opener) sandbox.window.open = opener.open;
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
   1) registry() reads bounds LIVE, not cached at open-time.
   ================================================================================================ */
(function () {
  var opener = makeOpener();
  var tab = makeTab(opener);
  var w = tab.VW.windows.open("/torque.html", { name: "vw-live" });
  w.screenX = 100; w.screenY = 50; w.outerWidth = 900; w.outerHeight = 700;

  var reg1 = tab.VW.windows.registry();
  check("registry() reflects the live handle's bounds on the first read",
    reg1.length === 1 && reg1[0].screenX === 100 && reg1[0].screenY === 50 &&
    reg1[0].outerWidth === 900 && reg1[0].outerHeight === 700);

  // Mutate the SAME handle (a technician moved/resized the window after opening it) and read again
  // -- a cached-at-open-time implementation would still report the OLD values here.
  w.screenX = 640; w.screenY = 10; w.outerWidth = 1024; w.outerHeight = 768;
  var reg2 = tab.VW.windows.registry();
  check("registry() reflects a CHANGED live value on a second read (not cached at open-time)",
    reg2.length === 1 && reg2[0].screenX === 640 && reg2[0].screenY === 10 &&
    reg2[0].outerWidth === 1024 && reg2[0].outerHeight === 768);
})();

/* ================================================================================================
   2) a throwing/unreadable bounds property degrades ONLY that field, ONLY for that one window --
      a second, healthy window's entry in the SAME registry() call is completely unaffected.
   ================================================================================================ */
(function () {
  var opener = makeOpener();
  var tab = makeTab(opener);
  var broken = tab.VW.windows.open("/part.html", { name: "vw-broken" });
  var healthy = tab.VW.windows.open("/procedure.html", { name: "vw-healthy" });

  // screenX throws; screenY/outerWidth/outerHeight read fine -- proves per-FIELD independence.
  Object.defineProperty(broken, "screenX", { get: function () { throw new Error("torn down"); } });
  broken.screenY = 20; broken.outerWidth = 500; broken.outerHeight = 400;
  healthy.screenX = 1; healthy.screenY = 2; healthy.outerWidth = 3; healthy.outerHeight = 4;

  var reg = tab.VW.windows.registry();
  var brokenEntry = reg.filter(function (e) { return e.name === "vw-broken"; })[0];
  var healthyEntry = reg.filter(function (e) { return e.name === "vw-healthy"; })[0];

  check("registry() call did not throw despite one window's throwing property", reg.length === 2);
  check("the throwing field alone degrades to null",
    brokenEntry && brokenEntry.screenX === null);
  check("the OTHER three fields on the SAME broken window still read live, unaffected",
    brokenEntry && brokenEntry.screenY === 20 && brokenEntry.outerWidth === 500 &&
    brokenEntry.outerHeight === 400);
  check("a DIFFERENT window's entry in the same call is completely unaffected",
    healthyEntry && healthyEntry.screenX === 1 && healthyEntry.screenY === 2 &&
    healthyEntry.outerWidth === 3 && healthyEntry.outerHeight === 4);

  // A window whose handle itself throws on EVERY property access (fully torn down, closed !== true
  // so _winPrune() did not already remove it) degrades ALL FOUR fields to null, still without
  // taking down the registry() call for anyone else.
  var opener2 = makeOpener();
  var tab2 = makeTab(opener2);
  var tornA = tab2.VW.windows.open("/x.html", { name: "vw-torn" });
  var okB = tab2.VW.windows.open("/y.html", { name: "vw-ok" });
  ["screenX", "screenY", "outerWidth", "outerHeight"].forEach(function (p) {
    Object.defineProperty(tornA, p, { get: function () { throw new Error("torn"); } });
  });
  okB.screenX = 9; okB.screenY = 9; okB.outerWidth = 9; okB.outerHeight = 9;
  var reg3 = tab2.VW.windows.registry();
  var tornEntry = reg3.filter(function (e) { return e.name === "vw-torn"; })[0];
  var okEntry = reg3.filter(function (e) { return e.name === "vw-ok"; })[0];
  check("a fully-throwing handle degrades all four fields to null without an exception escaping",
    reg3.length === 2 && tornEntry && tornEntry.screenX === null && tornEntry.screenY === null &&
    tornEntry.outerWidth === null && tornEntry.outerHeight === null);
  check("...and the OTHER tracked window is still fully reported",
    okEntry && okEntry.screenX === 9 && okEntry.outerWidth === 9);
})();

/* ================================================================================================
   3) windowsOpen() bounds hints: sane hint on a NEW open threads a real features string; an
      implausible hint is dropped gracefully (never throws, still opens, no features argument).
   ================================================================================================ */
(function () {
  var opener = makeOpener();
  var tab = makeTab(opener);   // 1920x1080 default screen

  // -- a SANE hint on a genuinely new named open.
  var w1 = tab.VW.windows.open("/a.html", { name: "vw-sane", left: 100, top: 50, width: 800, height: 600 });
  check("a sane bounds hint still returns a real window handle", !!w1);
  check("a sane bounds hint threads a real features string into window.open()'s 3rd argument",
    opener.calls[0].argc === 3 && opener.calls[0].features === "left=100,top=50,width=800,height=600");

  // -- an IMPLAUSIBLE hint (left far beyond any reasonable multi-monitor span for a 1920-wide
  //    screen: even this file's own generous 4x ceiling tops out at 7680) -- the "monitor unplugged
  //    since the position was saved" case named in the design doc.
  var thrown = false, w2;
  try {
    w2 = tab.VW.windows.open("/b.html", { name: "vw-implausible", left: 999999, top: 50, width: 800, height: 600 });
  } catch (e) { thrown = true; }
  check("an implausible bounds hint never throws", !thrown);
  check("an implausible bounds hint still opens the window normally", !!w2);
  check("an implausible bounds hint is dropped ENTIRELY -- no features argument reaches window.open()",
    opener.calls[1].argc === 2 && opener.calls[1].features === undefined);

  // -- a wildly negative top, same fallback.
  var w3 = tab.VW.windows.open("/c.html", { name: "vw-negative", left: 100, top: -999999 });
  check("a wildly negative top is also dropped, still opens with no features argument",
    !!w3 && opener.calls[2].argc === 2);

  // -- ONLY width/height offered, both sane: features carries only those two keys.
  var w4 = tab.VW.windows.open("/d.html", { name: "vw-sizeonly", width: 400, height: 300 });
  check("a partial (size-only) sane hint still threads just those keys",
    !!w4 && opener.calls[3].argc === 3 && opener.calls[3].features === "width=400,height=300");

  // -- no hint fields at all: byte-for-byte the same call shape PR 5's own test already asserts.
  var w5 = tab.VW.windows.open("/e.html", { name: "vw-nohint" });
  check("no hint at all keeps the plain 2-argument window.open() call (unchanged from PR 5)",
    !!w5 && opener.calls[4].argc === 2 && opener.calls[4].features === undefined);
})();

/* ================================================================================================
   4) reuse NEVER threads bounds, even when the reusing call itself passes hints.
   ================================================================================================ */
(function () {
  var opener = makeOpener();
  var tab = makeTab(opener);
  tab.VW.windows.open("/torque.html", { name: "vw-reuse", left: 10, top: 10, width: 640, height: 480 });
  check("the FIRST open of a reused name does thread a features string",
    opener.calls[0].argc === 3);

  var reusedWin = tab.VW.windows.open("/torque.html",
    { name: "vw-reuse", left: 999, top: 999, width: 1000, height: 1000 });
  check("re-opening the SAME name with bounds still returns the SAME handle (a real reuse)",
    !!reusedWin);
  check("a reuse NEVER threads bounds -- window.open() sees the plain 2-argument call, hints ignored",
    opener.calls[1].argc === 2 && opener.calls[1].features === undefined);
})();

/* ================================================================================================
   5) window.screen itself unreadable, or reporting a non-positive availWidth/availHeight: every
      hint is dropped, gracefully, never a throw.
   ================================================================================================ */
(function () {
  // -- window.screen entirely absent.
  var openerNoScreen = makeOpener();
  var tabNoScreen = makeTab(openerNoScreen, null);
  var thrown1 = false, wNoScreen;
  try {
    wNoScreen = tabNoScreen.VW.windows.open("/f.html", { name: "vw-noscreen", left: 10, top: 10 });
  } catch (e) { thrown1 = true; }
  check("a missing window.screen never throws", !thrown1);
  check("a missing window.screen still opens, with hints dropped",
    !!wNoScreen && openerNoScreen.calls[0].argc === 2);

  // -- window.screen present but availWidth/availHeight are zero/non-numeric.
  var openerBadScreen = makeOpener();
  var tabBadScreen = makeTab(openerBadScreen, { availWidth: 0, availHeight: 1080 });
  var wBadScreen = tabBadScreen.VW.windows.open("/g.html", { name: "vw-badscreen", left: 10 });
  check("a zero availWidth drops every hint, still opens normally",
    !!wBadScreen && openerBadScreen.calls[0].argc === 2);

  // -- window.screen itself throws on access.
  var openerThrowScreen = makeOpener();
  var tabThrowScreen = makeTab(openerThrowScreen);
  Object.defineProperty(tabThrowScreen.window, "screen", {
    get: function () { throw new Error("no screen here"); }
  });
  var thrown2 = false, wThrowScreen;
  try {
    wThrowScreen = tabThrowScreen.VW.windows.open("/h.html", { name: "vw-throwscreen", left: 10, top: 10 });
  } catch (e) { thrown2 = true; }
  check("a throwing window.screen accessor never throws out of windowsOpen()", !thrown2);
  check("a throwing window.screen still opens normally, hints dropped",
    !!wThrowScreen && openerThrowScreen.calls[0].argc === 2);
})();

/* ================================================================================================
   6) restoreLayout(entries): calls through windowsOpen() -- the SAME path, proven by the SAME
      broadcast shape landing on a genuinely separate tab -- skips malformed entries without
      aborting the batch, and returns one result per INPUT entry in order.
   ================================================================================================ */
(function (done) {
  var opener = makeOpener();
  var tab = makeTab(opener);
  var listener = makeTab(null);
  var heard = [];
  listener.VW.channel.subscribe("windows", function (data, meta) { heard.push({ data: data, meta: meta }); });

  check("restoreLayout is a function on VW.windows", typeof tab.VW.windows.restoreLayout === "function");
  check("restoreLayout on a non-array input returns an empty array, never throws",
    (function () {
      try { return JSON.stringify(tab.VW.windows.restoreLayout(null)) === "[]" &&
        JSON.stringify(tab.VW.windows.restoreLayout("not an array")) === "[]" &&
        JSON.stringify(tab.VW.windows.restoreLayout(undefined)) === "[]";
      } catch (e) { return false; }
    })());

  var entries = [
    { name: "vw-r1", url: "/r1.html", screenX: 10, screenY: 20, outerWidth: 640, outerHeight: 480 },
    { name: "", url: "/bad-noname.html" },                 // malformed: empty name
    { url: "/bad-nameless.html" },                          // malformed: no name field at all
    { name: "vw-r-nourl" },                                  // malformed: no url
    { name: "vw-r2", url: "/r2.html" }                      // well-formed, no bounds at all
  ];

  var results;
  var threw = false;
  try { results = tab.VW.windows.restoreLayout(entries); }
  catch (e) { threw = true; }

  check("restoreLayout does not throw over a batch with malformed entries mixed in", !threw);
  check("restoreLayout returns exactly one result per INPUT entry, same order", results && results.length === 5);
  check("a malformed entry (empty name) is reported ok:false, never thrown over",
    results && results[1].ok === false);
  check("a malformed entry (missing name) is reported ok:false",
    results && results[2].ok === false);
  check("a malformed entry (missing url) is reported ok:false",
    results && results[3].ok === false);
  check("the two well-formed entries are reported ok:true",
    results && results[0].ok === true && results[4].ok === true);
  check("a well-formed entry's result carries its own name/url back",
    results && results[0].name === "vw-r1" && results[0].url === "/r1.html");

  // Exactly 2 real window.open() calls happened -- the 3 malformed entries never reached windowsOpen
  // at all, let alone window.open().
  check("only the 2 well-formed entries actually reached window.open()", opener.calls.length === 2);
  check("the bounds-carrying entry threaded a real features string, translated screenX/screenY/" +
    "outerWidth/outerHeight into windowsOpen()'s left/top/width/height opts",
    opener.calls[0].url === "/r1.html" &&
    opener.calls[0].features === "left=10,top=20,width=640,height=480");
  check("the entry with no bounds fields opened with the plain 2-argument call, no features",
    opener.calls[1].url === "/r2.html" && opener.calls[1].argc === 2);

  // Neither well-formed entry's name was already tracked -- both are fresh opens, not reuses.
  check("neither restored entry was a reuse (both names were new to this tab)",
    results[0].reused === false && results[4].reused === false);

  // A SECOND restoreLayout call for the SAME name IS a real reuse, reported as such, and (per the
  // reuse rule proven above) does not thread its bounds a second time.
  var results2 = tab.VW.windows.restoreLayout(
    [{ name: "vw-r1", url: "/r1.html", screenX: 999, screenY: 999, outerWidth: 999, outerHeight: 999 }]);
  check("restoring an already-open entry a second time is reported reused:true",
    results2 && results2.length === 1 && results2[0].ok === true && results2[0].reused === true);
  check("...and, matching the reuse rule, its bounds were NOT threaded a second time",
    opener.calls[2].argc === 2 && opener.calls[2].features === undefined);

  // THE SAME PATH, NOT A SECOND COPY: the broadcast channel saw exactly the events windowsOpen()
  // itself would have produced for these 3 real opens (2 fresh opens + 1 reuse) -- same envelope
  // shape, same event/name/url/count fields. A hand-rolled, parallel "restore" implementation that
  // bypassed windowsOpen() would not produce this.
  setTimeout(function () {
    var events = heard.map(function (m) { return m.data.event + ":" + String(m.data.name); }).join(" | ");
    check("restoreLayout's real opens broadcast on the SAME 'windows' channel windowsOpen() uses, " +
      "in the same shape (proving it calls THROUGH windowsOpen(), not a parallel copy)",
      heard.length === 3 && events === "open:vw-r1 | open:vw-r2 | reuse:vw-r1");
    if (heard.length === 3) {
      check("the reuse broadcast's count reflects the registry size windowsOpen() itself computed",
        heard[2].data.count === 2);
    }
    done();
  }, 80);
})(function () {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
});

// END OF FILE
