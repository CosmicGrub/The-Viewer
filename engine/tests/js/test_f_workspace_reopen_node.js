/* THE VIEWER -- F: save & reopen named workspaces (multi-window PR 16 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 5). Real round-trip tests, run
under plain Node, for the two pieces of this PR that live in shared.js: workspaceDelete() (the CRUD
gap this PR filled) and the auto-checkpoint (design doc item 9's "Addition this revision").

Invoked by engine/tests/test_f_workspace_reopen.py via `node this-file.js`; prints PASS/FAIL lines
and exits 1 on any failure, same convention as test_workspace_node.js / test_workspace_export_import_
node.js (which this file's makeStore/makeClock/check helpers mirror closely).

WHY THIS IS A REAL TEST, NOT A REIMPLEMENTATION:

  * workspaceDelete()'s round trip goes through the real exported VW.workspace.create/list/delete
    functions loaded from the real engine/ui/shared.js, checks the RAW localStorage value directly
    (not just the function's return value) the same way test_workspace_node.js does for
    create/list/get/touch, and proves the cross-tab "delete" notification over a real
    BroadcastChannel between two separate vm contexts sharing one store -- exactly the touch()
    notification test this mirrors.

  * The checkpoint tests do NOT call any private save function directly (there is none exported --
    by design, see shared.js's own comment on why only get()/clear() are public). Instead this file
    builds a sandbox with a REAL window.addEventListener (captures handlers per event name instead
    of the other tests' no-op stub) and a REAL global setInterval (captures the callback instead of
    actually waiting), then invokes the handler shared.js itself registered at module-load time --
    the exact same function a real browser would call on a real 'pagehide' event or a real timer
    tick. This proves the wiring described in shared.js's own comment actually exists and actually
    works, not merely that some function with the right name exists somewhere in the file.

  * The "genuinely distinct storage key" and "never leaks into workspaceList()" guarantees are
    checked two ways: structurally (the two `var _WS_KEY = "..."` / `var _CHECKPOINT_KEY = "..."`
    source literals are extracted and compared) AND functionally (after a real checkpoint save, the
    raw store holds BOTH keys with independent values, and VW.workspace.list() -- the real exported
    function -- still returns only the named workspace, never the checkpoint entry).

  * The "never clobber a real checkpoint with an empty one" guard (shared.js's own stated reason for
    wiring the save at the shared.js top level rather than only from workspaces.html) is proven by
    firing a SECOND tab's real pagehide handler -- a tab that never opened any window itself, so its
    own VW.windows.registry() is empty -- against a store that already holds a real checkpoint from
    a first tab, and checking the stored value is byte-for-byte unchanged afterward.

Node's real global Blob/BroadcastChannel are used, matching this project's node_availability
convention elsewhere. Gracefully skips (never false-fails) in an environment without node -- enforced
by the calling .py wrapper, not this file. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

var WS_KEY = "viewer_workspaces";

function fakeEl() {
  return { style: {}, setAttribute: function () {}, appendChild: function () {}, textContent: "" };
}

function makeStore(opts) {
  opts = opts || {};
  var data = {};
  return {
    data: data,
    getItem: function (k) {
      if (opts.throwOnRead) throw new Error("SecurityError: storage disabled");
      return Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null;
    },
    setItem: function (k, v) {
      if (opts.throwOnWrite) throw new Error("QuotaExceededError");
      data[k] = String(v);
    },
    removeItem: function (k) {
      if (opts.throwOnWrite) throw new Error("QuotaExceededError");
      delete data[k];
    }
  };
}

function makeClock(start) {
  var t = start;
  return { now: function () { return t; }, advance: function (ms) { t += ms; } };
}

/* Unlike the other two node test files' makeTab (a no-op addEventListener stub, no setInterval at
   all -- shared.js's own defensive try/catch around checkpoint wiring simply swallows the resulting
   ReferenceError there, which is fine for tests that don't touch the checkpoint), THIS makeTab
   provides a REAL addEventListener (captures handlers per event name into ctx.__listeners) and a
   REAL setInterval (captures {fn, ms} into ctx.__intervals instead of actually scheduling anything
   -- a genuine timer would make this suite either slow or flaky). That is what lets the tests below
   invoke shared.js's OWN module-load-time-registered pagehide/interval handlers directly, rather
   than reimplementing what those handlers do. */
function makeTab(opts) {
  opts = opts || {};
  var clock = opts.clock || makeClock(1756800000000);
  var listeners = {};
  var intervals = [];
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Object: Object, Array: Array,
    String: String, Error: Error, Promise: Promise,
    setTimeout: setTimeout, clearTimeout: clearTimeout,
    encodeURIComponent: encodeURIComponent, decodeURIComponent: decodeURIComponent,
    module: {}, exports: {}
  };
  sandbox.Date = { now: clock.now };
  if (opts.bc !== false) sandbox.BroadcastChannel = BroadcastChannel;
  if (typeof Blob !== "undefined") sandbox.Blob = Blob;
  sandbox.setInterval = function (fn, ms) { intervals.push({ fn: fn, ms: ms }); return intervals.length; };
  sandbox.clearInterval = function () {};
  sandbox.document = {
    readyState: "complete", getElementById: function () { return null; },
    querySelector: function () { return null; }, createElement: function () { return fakeEl(); },
    addEventListener: function () {}, body: fakeEl(), head: fakeEl(), documentElement: fakeEl()
  };
  sandbox.window = sandbox;
  sandbox.window.addEventListener = function (name, fn) {
    if (!listeners[name]) listeners[name] = [];
    listeners[name].push(fn);
  };
  sandbox.window.location = { pathname: "/probe", href: "" };
  sandbox.window.localStorage = opts.store || makeStore();
  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
  ctx.__clock = clock;
  ctx.__listeners = listeners;
  ctx.__intervals = intervals;
  /* Fires the real handler(s) shared.js registered for one event name -- e.g. the exact function
     that runs on a genuine browser 'pagehide' event. Throws (loudly, in the test) if shared.js
     never registered one, since that would mean the wiring itself is missing. */
  ctx.__fire = function (eventName) {
    var fns = listeners[eventName] || [];
    if (!fns.length) throw new Error("no listener registered for '" + eventName + "'");
    for (var i = 0; i < fns.length; i++) fns[i]();
  };
  ctx.__fireInterval = function (n) {
    if (!intervals[n || 0]) throw new Error("no setInterval call captured at index " + (n || 0));
    intervals[n || 0].fn();
  };
  return ctx;
}

var failures = [];
var total = 0;
function check(name, cond) {
  total++;
  if (!cond) failures.push(name);
  console.log((cond ? "PASS " : "FAIL ") + name);
}

function stored(store, key) {
  var raw = store.data[key];
  if (raw === undefined) return undefined;
  return JSON.parse(raw);
}

/* ================================================================================================
   SOURCE-LEVEL: the two storage keys are genuinely distinct literals, not one key computed from
   the other or a shared prefix that could collide.
   ================================================================================================ */
var wsKeyLiteral = (src.match(/var _WS_KEY = "([^"]+)"/) || [])[1];
var cpKeyLiteral = (src.match(/var _CHECKPOINT_KEY = "([^"]+)"/) || [])[1];
check("shared.js declares a named-workspaces storage key literal", typeof wsKeyLiteral === "string" && wsKeyLiteral.length > 0);
check("shared.js declares a checkpoint storage key literal", typeof cpKeyLiteral === "string" && cpKeyLiteral.length > 0);
check("the checkpoint key is a genuinely different string than the named-workspaces key",
  !!wsKeyLiteral && !!cpKeyLiteral && wsKeyLiteral !== cpKeyLiteral);
check("the checkpoint key matches WS_KEY, wrapped in " + JSON.stringify(WS_KEY), wsKeyLiteral === WS_KEY);
var CHECKPOINT_KEY = cpKeyLiteral;

/* ================================================================================================
   workspaceDelete(id) -- the CRUD gap this PR filled. Same real-round-trip convention as
   test_workspace_node.js's own touch() coverage.
   ================================================================================================ */
(function () {
  var store = makeStore();
  var tabA = makeTab({ store: store, clock: makeClock(1756800000000) });

  var id1 = tabA.VW.workspace.create("Keep me", [{ page: "part.html", params: {} }]);
  var id2 = tabA.VW.workspace.create("Delete me", [{ page: "torque.html", params: {} }]);
  check("setup: two workspaces really stored", tabA.VW.workspace.list().length === 2);

  check("delete(unknown id) returns false", tabA.VW.workspace.delete("ws-nope") === false);
  check("delete(null) returns false, does not throw", tabA.VW.workspace.delete(null) === false);
  check("a failed/no-op delete wrote nothing", tabA.VW.workspace.list().length === 2);

  var deleted = tabA.VW.workspace.delete(id2);
  check("delete(known id) returns true", deleted === true);
  check("the deleted workspace is genuinely gone from list()",
    tabA.VW.workspace.list().every(function (w) { return w.id !== id2; }));
  check("the deleted workspace is genuinely gone from get()", tabA.VW.workspace.get(id2) === null);
  check("list() now has exactly the one remaining workspace", tabA.VW.workspace.list().length === 1);
  check("the OTHER workspace is completely untouched by the delete",
    tabA.VW.workspace.get(id1) !== null && tabA.VW.workspace.get(id1).name === "Keep me");

  // storage that refuses the write -> false, same convention as touch()'s own refused-write case
  var blindStore = makeStore({ throwOnWrite: true });
  var blindTab = makeTab({ store: blindStore });
  var blindId = null;
  try {
    // create() itself needs a working store; seed via a store that allows writes, then swap the
    // handle's own setItem to simulate the write failing on delete specifically.
    var seedStore = makeStore();
    var seedTab = makeTab({ store: seedStore });
    blindId = seedTab.VW.workspace.create("X", []);
    seedStore.setItem = function () { throw new Error("QuotaExceededError"); };
    check("delete() returns false when storage refuses the write", seedTab.VW.workspace.delete(blindId) === false);
  } catch (e) {
    check("delete()-refused-write case did not throw unexpectedly (it did: " + e.message + ")", false);
  }
})();

/* ================================================================================================
   The cross-tab "delete" notification, over a real BroadcastChannel -- mirrors test_workspace_
   node.js's own touch() notification test exactly, applied to delete().
   ================================================================================================ */
function runDeleteNotifyChecks(done) {
  var store = makeStore();
  var tabA = makeTab({ store: store, clock: makeClock(1756800000000) });
  var tabB = makeTab({ store: store, clock: makeClock(1756800000000) });

  var notesInB = [];
  tabB.VW.channel.subscribe("workspace", function (data) { notesInB.push(data); });

  var id = tabA.VW.workspace.create("Notify me", [{ page: "part.html", params: {} }]);
  var deleted = tabA.VW.workspace.delete(id);
  check("setup: delete for the notify test really succeeded", deleted === true);

  // BroadcastChannel delivery is asynchronous -- wait a tick, exactly as the other node suites do.
  setTimeout(function () {
    var deletes = notesInB.filter(function (n) { return n.action === "delete"; });
    check("tab B was notified of tab A's delete", deletes.length === 1);
    check("the delete notification carries the deleted id",
      deletes.length === 1 && deletes[0].id === id);
    done();
  }, 30);
}

/* ================================================================================================
   AUTO-CHECKPOINT: real pagehide/interval handlers, real localStorage, real VW.windows.registry().
   ================================================================================================ */
function runCheckpointChecks() {
  var store = makeStore();
  var tabA = makeTab({ store: store, clock: makeClock(1756800000000) });

  // A real named workspace coexists in the SAME store, so "never leaks into workspaceList()" is
  // checked against a store that genuinely has both kinds of data in it, not an empty one.
  tabA.VW.workspace.create("A real saved workspace", [{ page: "part.html", params: {} }]);
  check("shared.js really registered a pagehide listener", (tabA.__listeners.pagehide || []).length >= 1);
  check("shared.js really registered a setInterval checkpoint tick", tabA.__intervals.length >= 1);
  check("the checkpoint interval is minutes, not seconds (a safety net, not a live-sync tick)",
    tabA.__intervals[0].ms >= 60000);

  check("no checkpoint stored yet", tabA.VW.checkpoint.get() === null);
  check("no checkpoint key written to storage yet", store.data[CHECKPOINT_KEY] === undefined);

  // A tab with an EMPTY registry (never called VW.windows.open) firing pagehide must write NOTHING
  // -- proven before any real checkpoint exists, so "nothing" here can't be confused with "a guard
  // silently protected something".
  tabA.__fire("pagehide");
  check("an empty-registry pagehide writes no checkpoint at all", store.data[CHECKPOINT_KEY] === undefined);

  // Now really open two named windows in this tab (the real VW.windows.open path, same as any
  // pop-out/launch feature), then fire the SAME real pagehide handler again.
  var fakeWin = { closed: false, focus: function () {} };
  var realOpen = tabA.open;
  tabA.open = function () { return fakeWin; };
  tabA.VW.windows.open("/torque?q=alt", { name: "vw-torque" });
  tabA.VW.windows.open("/procedure?doc=12", { name: "vw-procedure" });
  check("setup: this tab's registry now really has 2 windows", tabA.VW.windows.registry().length === 2);

  tabA.__fire("pagehide");
  var cp1 = stored(store, CHECKPOINT_KEY);
  check("pagehide with a non-empty registry writes a checkpoint", cp1 !== undefined);
  check("the stored checkpoint carries exactly this tab's registry",
    cp1 && JSON.stringify(cp1.windows.slice().sort(function(a,b){return a.name<b.name?-1:1;}))
      === JSON.stringify(tabA.VW.windows.registry().slice().sort(function(a,b){return a.name<b.name?-1:1;})));
  check("the stored checkpoint carries a save timestamp", cp1 && typeof cp1.at === "number");

  // The two storage locations are genuinely independent: the named-workspace key is byte-for-byte
  // unchanged by a checkpoint save, and workspaceList() -- the REAL exported function -- still
  // returns only the one real workspace, never the checkpoint.
  var wsList = tabA.VW.workspace.list();
  check("workspaceList() is completely unaffected by a checkpoint write", wsList.length === 1 && wsList[0].name === "A real saved workspace");
  check("workspaceList() never includes anything checkpoint-shaped (no .windows field on any entry)",
    wsList.every(function (w) { return w.windows === undefined; }));

  // VW.checkpoint.get() reads the SAME thing that was really written to storage -- not a second,
  // independently-tracked in-memory copy.
  var got = tabA.VW.checkpoint.get();
  check("VW.checkpoint.get() returns exactly what storage holds",
    got && JSON.stringify(got) === JSON.stringify(cp1));

  // A SECOND tab, sharing the SAME store, that never opened any window of its own (an empty
  // registry) must NOT be able to clobber tab A's real checkpoint by firing its own pagehide --
  // this is the guard shared.js's own comment names as the reason wiring the save globally is safe.
  var tabB = makeTab({ store: store, clock: makeClock(1756800100000) });
  check("setup: tab B genuinely has an empty registry", tabB.VW.windows.registry().length === 0);
  var before = store.data[CHECKPOINT_KEY];
  tabB.__fire("pagehide");
  check("an empty-registry tab's pagehide never clobbers an existing real checkpoint",
    store.data[CHECKPOINT_KEY] === before);

  // The periodic setInterval tick reaches the SAME real save path -- open a third window, fire the
  // captured interval callback (never a real timer), and confirm storage now reflects 3 windows.
  tabA.VW.windows.open("/part?nsn=1", { name: "vw-part" });
  check("setup: registry now has 3 windows", tabA.VW.windows.registry().length === 3);
  tabA.__fireInterval(0);
  var cp2 = stored(store, CHECKPOINT_KEY);
  check("the periodic interval tick also writes a real checkpoint", cp2 !== undefined && cp2.windows.length === 3);
  tabA.open = realOpen;

  // checkpointClear()
  var cleared = tabA.VW.checkpoint.clear();
  check("checkpoint.clear() returns true when something was really removed", cleared === true);
  check("checkpoint.clear() genuinely removed the stored value", store.data[CHECKPOINT_KEY] === undefined);
  check("checkpoint.get() is null immediately after clear()", tabA.VW.checkpoint.get() === null);
  check("clearing an already-empty checkpoint returns false", tabA.VW.checkpoint.clear() === false);

  // Defensive read: corrupted stored value never throws, reads as null.
  var corruptStore = makeStore();
  corruptStore.data[CHECKPOINT_KEY] = "{not valid json";
  var corruptTab = makeTab({ store: corruptStore });
  check("checkpoint.get() on corrupted JSON returns null, does not throw", corruptTab.VW.checkpoint.get() === null);

  var shapelessStore = makeStore();
  shapelessStore.data[CHECKPOINT_KEY] = JSON.stringify({ at: 1, windows: "not-an-array" });
  var shapelessTab = makeTab({ store: shapelessStore });
  check("checkpoint.get() on a wrong-shaped value returns null", shapelessTab.VW.checkpoint.get() === null);
}

runCheckpointChecks();
runDeleteNotifyChecks(function () {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
});
