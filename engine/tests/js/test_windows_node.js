/* THE VIEWER -- VW.windows real behavior test, run under plain Node (not a browser).

Invoked by engine/tests/test_shared_windows.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure, matching the project's usual test-file convention.

WHAT THIS PROVES, AND WHAT IT CANNOT -- stated up front, because VW.windows is harder to test
honestly than VW.channel was and it would be easy to oversell this file:

  Proven here, for real. Every assertion below runs the actual production VW.windows.open() /
  VW.windows.registry() code out of engine/ui/shared.js, loaded into a vm.createContext() sandbox
  (the same document/localStorage shimming approach test_channel_node.js already uses). The one
  thing replaced is window.open itself -- Node has no window and no window.open, so there is nothing
  real to call. The mock records every call it receives (url, name, argument count) and hands back a
  fake window handle, so the test can assert on what the production code actually DID: how many
  times it called window.open and with which arguments, what ended up in the registry, which toast
  text reached the DOM, and what it published on the VW.channel "windows" channel. The broadcast
  half is not mocked at all -- a second sandbox subscribes over Node's real global BroadcastChannel,
  exactly as in test_channel_node.js, so the published envelopes are delivered by a real
  BroadcastChannel implementation.

  NOT proven here, and not provable here. Whether a real browser genuinely reuses a window when the
  same name is passed twice. That is browser behavior, not this codebase's behavior: shared.js's
  entire reuse strategy is to hand the name to window.open and let the browser's own named-window
  table do the work. The mock below mirrors that table (a repeat name returns the same handle, a
  closed one is replaced) because that is the semantic the production code is written against, but a
  mock agreeing with the code it was written to exercise proves nothing about Chrome or Firefox.
  Confirming real reuse needs a human: open a pop-out twice in a real browser and confirm ONE window
  results. That manual check is called out in the PR, in the same honest framing the design spec
  itself uses for every other real-hardware-only behavior. Also not covered: real popup-blocker
  behavior, real focus/raise-to-front behavior, and whether a reused window on a second monitor
  actually comes forward -- all of them window-manager territory. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

/* A minimal DOM good enough for the real toast() in shared.js: it creates a div, gives it an id,
   appends it to body, then writes textContent onto it, reusing the same element on later calls via
   getElementById. Registering appended elements by id here means the toast text this test reads back
   is the text production toast() actually wrote into the document, not a value the test invented.

   textContent is a real accessor rather than a plain field so that every WRITE is logged, not just
   the latest value. That distinction is not decoration: an earlier version of this file asserted
   "a blocked open does not toast" by comparing the toast text before and after, and a deliberately
   broken shared.js that toasted on a blocked open still passed, because the text it wrote happened
   to equal the text already there. Counting writes catches that; comparing values cannot. */
function makeDoc() {
  var byId = {};
  var writes = [];
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
      set: function (v) { text = v; writes.push({ el: e, value: v }); }
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
    body: body, head: el("head"), documentElement: el("html"),
    /* Every value production toast() has written into the #vw-toast element, in order. */
    __toastWrites: function () {
      var out = [], i;
      for (i = 0; i < writes.length; i++) {
        if (writes[i].el.id === "vw-toast") out.push(writes[i].value);
      }
      return out;
    }
  };
}

/* The window.open mock. It records every call, and mirrors the browser's own named-window table --
   the same name returns the SAME handle, unless that window was closed, in which case a fresh one is
   made (which is what a real browser does too). See the header comment on why that mirroring is a
   convenience for writing assertions, not evidence about real browsers. */
function makeOpener() {
  var named = {};
  var api = {
    calls: [],
    blocked: false,     // flip to simulate a popup blocker (window.open returns null)
    thrower: false,     // flip to simulate a locked-down configuration (window.open throws)
    handles: [],
    open: function (url, name) {
      api.calls.push({ url: url, name: name, argc: arguments.length });
      if (api.thrower) throw new Error("simulated: window.open refused");
      if (api.blocked) return null;
      if (name && named[name] && named[name].closed !== true) {
        named[name].url = url;              // a real browser navigates the existing window
        named[name].focusCount++;
        return named[name];
      }
      var h = { closed: false, url: url, name: name || null, focusCount: 0 };
      h.focus = function () { h.focusCount++; };
      api.handles.push(h);
      if (name) named[name] = h;
      return h;
    }
  };
  return api;
}

function makeTab(opener) {
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
  if (opener) sandbox.window.open = opener.open;
  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
  return ctx;
}

function toastWrites(ctx) { return ctx.document.__toastWrites(); }
function toastText(ctx) {
  var w = toastWrites(ctx);
  return w.length ? w[w.length - 1] : null;
}

var failures = [];
var total = 0;
function check(name, cond) {
  total++;
  if (!cond) failures.push(name);
  console.log((cond ? "PASS " : "FAIL ") + name);
}

var opener = makeOpener();
var tab = makeTab(opener);          // the tab under test: its window.open is the mock above
var listener = makeTab(null);       // a second, independent tab, subscribed to the broadcast
var heard = [];
listener.VW.channel.subscribe("windows", function (data, meta) { heard.push({ data: data, meta: meta }); });

/* ---- shape ---- */
check("VW.windows exists", !!tab.VW && !!tab.VW.windows);
check("open/registry are both functions",
  typeof tab.VW.windows.open === "function" && typeof tab.VW.windows.registry === "function");
check("registry starts empty", tab.VW.windows.registry().length === 0);
check("registry() returns an array", Object.prototype.toString.call(tab.VW.windows.registry()) === "[object Array]");

/* ---- a first named open ---- */
var w1 = tab.VW.windows.open("/torque.html", { name: "vw-a" });
check("open() returns the handle window.open gave it", !!w1 && w1 === opener.handles[0]);
check("window.open called once", opener.calls.length === 1);
check("window.open received url AND name (the whole reuse mechanism)",
  opener.calls[0].url === "/torque.html" && opener.calls[0].name === "vw-a");
check("no window-features argument is passed (would force a chrome-less popup)", opener.calls[0].argc === 2);
var reg1 = tab.VW.windows.registry();
check("registry has exactly one entry", reg1.length === 1);
check("registry entry carries name and url",
  reg1.length === 1 && reg1[0].name === "vw-a" && reg1[0].url === "/torque.html");
check("registry entry now also carries the PR 6 layout fields (null here -- the mock window handle " +
  "this harness uses sets no screenX/screenY/outerWidth/outerHeight of its own; a real handle's " +
  "live bounds are exercised in engine/tests/js/test_windows_layout_node.js)",
  reg1.length === 1 &&
  Object.keys(reg1[0]).sort().join(",") === "name,outerHeight,outerWidth,screenX,screenY,url" &&
  reg1[0].screenX === null && reg1[0].screenY === null &&
  reg1[0].outerWidth === null && reg1[0].outerHeight === null);
var toastAfterOpen = toastText(tab);
check("exactly one toast was written to the DOM on open", toastWrites(tab).length === 1);
check("the open toast says a new window opened", /new window/i.test(toastAfterOpen || ""));
check("focus() was called on the opened window", opener.handles[0].focusCount === 1);

/* ---- the same name again: ONE registry entry, but window.open is still really called ---- */
var w2 = tab.VW.windows.open("/torque.html", { name: "vw-a" });
check("second open with the same name still calls window.open (the browser does the reuse)",
  opener.calls.length === 2 && opener.calls[1].name === "vw-a");
check("same name returned the same window handle", w2 === w1);
check("same name twice produces ONE registry entry, not two", tab.VW.windows.registry().length === 1);
var toastAfterReuse = toastText(tab);
check("a second toast was written on reuse too", toastWrites(tab).length === 2);
check("the reuse toast is distinguishable from the open toast", toastAfterReuse !== toastAfterOpen);
check("the reuse toast says the window was already open", /already open/i.test(toastAfterReuse || ""));

/* ---- a different name is a separate window ---- */
tab.VW.windows.open("/part.html", { name: "vw-b" });
var reg2 = tab.VW.windows.registry();
var names2 = reg2.map(function (e) { return e.name; }).sort().join(",");
check("a different name produces a separate registry entry", reg2.length === 2 && names2 === "vw-a,vw-b");

/* ---- same name, new url: the tracked url follows the navigation ---- */
tab.VW.windows.open("/part2.html", { name: "vw-b" });
var reg3 = tab.VW.windows.registry();
var vwb = reg3.filter(function (e) { return e.name === "vw-b"; })[0];
check("same name with a new url updates the tracked url, still one entry",
  reg3.length === 2 && vwb && vwb.url === "/part2.html");

/* ---- no name: opens, toasts, but never enters the registry ---- */
var beforeAnon = tab.VW.windows.registry().length;
var toastsBeforeAnon = toastWrites(tab).length;
var anonThrew = false, wAnon = null;
try { wAnon = tab.VW.windows.open("/anon.html"); } catch (e) { anonThrew = true; }
check("an unnamed open does not throw", !anonThrew);
check("an unnamed open still returns a window handle", !!wAnon);
check("an unnamed open passes only the url to window.open",
  opener.calls[opener.calls.length - 1].argc === 1 && opener.calls[opener.calls.length - 1].url === "/anon.html");
check("an unnamed open does not pollute the registry", tab.VW.windows.registry().length === beforeAnon);
check("an unnamed open still toasts (the click must visibly register)",
  toastWrites(tab).length === toastsBeforeAnon + 1 && /new window/i.test(toastText(tab) || ""));

/* ---- a popup blocker: null back from window.open ---- */
var toastsBeforeBlock = toastWrites(tab).length;
var regBeforeBlock = tab.VW.windows.registry().length;
var callsBeforeBlock = opener.calls.length;
opener.blocked = true;
var blockThrew = false, wBlocked;
try { wBlocked = tab.VW.windows.open("/blocked.html", { name: "vw-blocked" }); }
catch (e) { blockThrew = true; }
opener.blocked = false;
check("a blocked open does not throw", !blockThrew);
check("a blocked open returns null", wBlocked === null);
check("a blocked open is not added to the registry", tab.VW.windows.registry().length === regBeforeBlock);
check("a blocked open writes NO toast at all (nothing opened, so nothing may claim it did)",
  toastWrites(tab).length === toastsBeforeBlock);
check("the blocked attempt did reach window.open", opener.calls.length === callsBeforeBlock + 1);

/* ---- window.open throwing outright (locked-down configuration) ---- */
opener.thrower = true;
var throwEscaped = false, wThrew;
try { wThrew = tab.VW.windows.open("/throws.html", { name: "vw-throws" }); }
catch (e) { throwEscaped = true; }
opener.thrower = false;
check("a throwing window.open is caught, never propagated to the caller", !throwEscaped);
check("a throwing window.open yields null", wThrew === null);
check("a throwing window.open is not added to the registry",
  tab.VW.windows.registry().length === regBeforeBlock);
check("a throwing window.open writes no toast either", toastWrites(tab).length === toastsBeforeBlock);

/* ---- a window the user closed is pruned, and re-opening it is a fresh open, not a reuse ---- */
opener.handles[0].closed = true;                 // the user closed the "vw-a" pop-out
var regAfterClose = tab.VW.windows.registry();
check("a closed window is pruned from the registry",
  regAfterClose.length === 1 && regAfterClose[0].name === "vw-b");
var toastsBeforeReopen = toastWrites(tab).length;
tab.VW.windows.open("/torque.html", { name: "vw-a" });
check("re-opening a closed name toasts as a new open, not a reuse",
  toastWrites(tab).length === toastsBeforeReopen + 1 && /new window/i.test(toastText(tab) || ""));
check("re-opening a closed name is tracked again", tab.VW.windows.registry().length === 2);

/* ---- the returned registry is a copy: mutating it cannot corrupt internal state ---- */
var handedOut = tab.VW.windows.registry();
handedOut.length = 0;
handedOut.push({ name: "injected", url: "/nope" });
var reCheck = tab.VW.windows.registry();
check("mutating a returned registry array cannot corrupt the real registry",
  reCheck.length === 2 && reCheck.filter(function (e) { return e.name === "injected"; }).length === 0);
var handedOut2 = tab.VW.windows.registry();
handedOut2[0].url = "/tampered";
check("mutating a returned registry entry cannot corrupt the real registry",
  tab.VW.windows.registry().filter(function (e) { return e.url === "/tampered"; }).length === 0);

/* ---- the broadcast: delivered to a genuinely separate tab over a real BroadcastChannel ---- */
setTimeout(function () {
  var events = heard.map(function (m) { return m.data.event + ":" + String(m.data.name); }).join(" | ");
  check("every successful open broadcast on the windows channel, and only those (6 expected)",
    heard.length === 6);
  check("broadcast event sequence matches what actually happened",
    events === "open:vw-a | reuse:vw-a | open:vw-b | reuse:vw-b | open:null | open:vw-a");
  if (heard.length === 6) {
    check("broadcast carries the url", heard[0].data.url === "/torque.html");
    check("broadcast carries the tracked-window count", heard[0].data.count === 1 && heard[2].data.count === 2);
    check("an unnamed open broadcasts a null name", heard[4].data.name === null);
    check("broadcast rides the normal VW.channel envelope (seq present, in order)",
      heard[0].meta.seq === 1 && heard[5].meta.seq === 6);
    check("no broadcast was sent for the blocked or the throwing attempt",
      events.indexOf("vw-blocked") === -1 && events.indexOf("vw-throws") === -1);
  }

  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}, 80);
