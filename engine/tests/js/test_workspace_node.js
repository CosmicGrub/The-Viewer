/* THE VIEWER -- VW.workspace real CRUD + cross-tab notification test, run under plain Node.

Invoked by engine/tests/test_shared_workspace.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure, matching the project's usual test-file convention.

Why this is a real test rather than a reimplementation of the logic under test:

  * Every assertion goes through the actual exported VW.workspace functions loaded from the real
    engine/ui/shared.js. Nothing here reimplements id generation, item normalization, the record
    shape, or the storage layout -- where a check needs to know what was really persisted, it reads
    the raw localStorage key directly (store.data["viewer_workspaces"]) and parses it, rather than
    trusting the API's own return value to describe itself.

  * Two vm.createContext() sandboxes stand in for two browser tabs, exactly as
    test_channel_node.js does -- but here they deliberately SHARE one localStorage object, because
    that is precisely what two tabs on one origin have. That makes the design's central claim
    testable for real: a workspace created in tab A is genuinely readable through tab B's own
    VW.workspace.list(), with the VW.channel message serving only as the "something changed,
    repaint" hint. Both sandboxes are also handed Node's real global BroadcastChannel, so the
    notification really does cross contexts through a production implementation.

  * The sandbox's Date is a controllable clock (shared.js only ever calls Date.now()). Without it,
    "touch() updates lastOpened" is a vacuous check on a fast machine, since created and lastOpened
    would land in the same millisecond; with it, the update is observable as a real, exact change.

  * Node cannot fire a real `storage` event across two contexts (that IPC lives in the browser/OS,
    not in V8), so the BroadcastChannel-less fallback scenario captures whatever listener shared.js
    itself registers via window.addEventListener("storage", ...) and invokes it with the envelope
    the publishing tab really wrote to localStorage. Only the OS-level delivery hop is stood in
    for; everything either side of it is production code.
*/
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

var WS_KEY = "viewer_workspaces";
var CHANNEL_KEY = "viewer_channel_msg";

function fakeEl() {
  return { style: {}, setAttribute: function () {}, appendChild: function () {}, textContent: "" };
}

/* One localStorage, shared by however many tabs are pointed at it -- same-origin storage, modeled
   honestly. opts.throwOnRead / opts.throwOnWrite reproduce a private-browsing profile and a full
   quota respectively (both really do throw on plain access in a browser). */
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
    }
  };
}

function makeClock(start) {
  var t = start;
  return { now: function () { return t; }, advance: function (ms) { t += ms; } };
}

/* opts: {store, clock, bc (default true), random} */
function makeTab(opts) {
  opts = opts || {};
  var storageListeners = [];
  var clock = opts.clock || makeClock(1756800000000);
  var mathObj = Math;
  if (opts.random) {
    mathObj = { random: opts.random, round: Math.round, floor: Math.floor };
  }
  var sandbox = {
    console: console, Math: mathObj, JSON: JSON, Object: Object, Array: Array,
    String: String, Error: Error, setTimeout: setTimeout, clearTimeout: clearTimeout,
    module: {}, exports: {}
  };
  sandbox.Date = { now: clock.now };          // shared.js only ever calls Date.now()
  if (opts.bc !== false) sandbox.BroadcastChannel = BroadcastChannel;
  sandbox.document = {
    readyState: "complete", getElementById: function () { return null; },
    querySelector: function () { return null; }, createElement: function () { return fakeEl(); },
    addEventListener: function () {}, body: fakeEl(), head: fakeEl(), documentElement: fakeEl()
  };
  sandbox.window = sandbox;
  sandbox.window.addEventListener = function (type, fn) {
    if (type === "storage") storageListeners.push(fn);
  };
  sandbox.window.location = { pathname: "/probe", href: "" };
  sandbox.window.localStorage = opts.store || makeStore();
  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
  ctx.__storageListeners = storageListeners;
  ctx.__clock = clock;
  return ctx;
}

var failures = [];
var total = 0;
function check(name, cond) {
  total++;
  if (!cond) failures.push(name);
  console.log((cond ? "PASS " : "FAIL ") + name);
}

/* Reads what is REALLY in storage, without going through the API under test. */
function stored(store) {
  var raw = store.data[WS_KEY];
  if (raw === undefined) return undefined;
  return JSON.parse(raw);
}

/* ---- two tabs, one shared origin storage, real BroadcastChannel between them ---- */
var store = makeStore();
var clock = makeClock(1756800000000);
var tabA = makeTab({ store: store, clock: clock });
var tabB = makeTab({ store: store, clock: clock });

check("two tabs are genuinely independent contexts", tabA !== tabB);
check("VW.workspace present in both", !!(tabA.VW && tabA.VW.workspace) && !!(tabB.VW && tabB.VW.workspace));
check("two tabs really share one localStorage", tabA.window.localStorage === tabB.window.localStorage);

/* every notification either tab publishes, captured from the other side */
var notesInB = [];
tabB.VW.channel.subscribe("workspace", function (data, meta) {
  notesInB.push({ data: data, meta: meta });
});

/* ---- empty state ---- */
check("list() on empty storage returns an empty array",
  Object.prototype.toString.call(tabA.VW.workspace.list()) === "[object Array]" &&
  tabA.VW.workspace.list().length === 0);
check("get() on empty storage returns null", tabA.VW.workspace.get("nope") === null);
check("empty list() wrote nothing to storage", stored(store) === undefined);

/* ---- create ---- */
var id1 = tabA.VW.workspace.create("Work Order 4471", [
  { page: "procedure.html", params: { doc: 12, page: 340 } },
  { page: "torque.html", params: { nsn: "5310-00-123-4567" } }
]);
check("create() returns a string id", typeof id1 === "string" && id1.length > 3);

var rawAll = stored(store);
check("create() really persisted a JSON array under viewer_workspaces",
  Object.prototype.toString.call(rawAll) === "[object Array]" && rawAll.length === 1);

var rec = rawAll[0];
check("stored record carries exactly the spec's fields",
  rec && rec.id === id1 && rec.name === "Work Order 4471" &&
  Object.prototype.toString.call(rec.items) === "[object Array]" &&
  typeof rec.created === "number" && typeof rec.lastOpened === "number" &&
  rec.source === "manual");
check("stored record has no extra fields beyond the spec's six",
  rec && Object.keys(rec).sort().join(",") === "created,id,items,lastOpened,name,source");
check("created === lastOpened on a fresh workspace", rec.created === rec.lastOpened);
check("created uses the real clock", rec.created === 1756800000000);
check("items normalized to {page, params} with string param values",
  rec.items.length === 2 &&
  rec.items[0].page === "procedure.html" && rec.items[0].params.doc === "12" &&
  rec.items[0].params.page === "340" &&
  rec.items[1].page === "torque.html" && rec.items[1].params.nsn === "5310-00-123-4567");
check("item order preserved", rec.items[0].page === "procedure.html" && rec.items[1].page === "torque.html");

/* ---- get / list through the API, and from the OTHER tab ---- */
var got = tabA.VW.workspace.get(id1);
check("get(id) returns the record", got && got.id === id1 && got.name === "Work Order 4471");
check("get(unknown id) returns null", tabA.VW.workspace.get("ws-does-not-exist") === null);
check("get(null) returns null, does not throw", tabA.VW.workspace.get(null) === null);
check("tab B sees tab A's workspace through shared storage alone",
  tabB.VW.workspace.list().length === 1 && tabB.VW.workspace.get(id1) !== null);
check("tab B's copy is equal in content to tab A's",
  JSON.stringify(tabB.VW.workspace.get(id1)) === JSON.stringify(tabA.VW.workspace.get(id1)));

/* returned records are fresh parses -- a caller cannot corrupt storage by mutating one */
var mutable = tabA.VW.workspace.get(id1);
mutable.name = "CLOBBERED";
mutable.items.length = 0;
check("mutating a returned record does not corrupt storage",
  tabA.VW.workspace.get(id1).name === "Work Order 4471" &&
  tabA.VW.workspace.get(id1).items.length === 2);

/* ---- a second workspace: order, distinct ids ---- */
clock.advance(5000);
var id2 = tabA.VW.workspace.create("Solve It", [{ page: "troubleshoot.html", params: {} }]);
check("second create() returns a different id", typeof id2 === "string" && id2 !== id1);
check("list() returns both, in creation order (oldest first)",
  tabA.VW.workspace.list().length === 2 &&
  tabA.VW.workspace.list()[0].id === id1 && tabA.VW.workspace.list()[1].id === id2);

/* ---- item normalization edge cases ---- */
var id3 = tabA.VW.workspace.create("Messy", [
  null,
  "not-an-object",
  { params: { a: 1 } },                       // no page -> dropped
  { page: "", params: {} },                   // empty page -> dropped
  { page: "part.html" },                      // no params at all -> {}
  { page: "locate.html", params: { keep: "yes", drop: null, gone: undefined, fn: function () {} } }
]);
var messy = tabA.VW.workspace.get(id3);
check("unusable items dropped, usable ones kept", messy.items.length === 2);
check("an item with no params gets an empty params object",
  messy.items[0].page === "part.html" &&
  messy.items[0].params && Object.keys(messy.items[0].params).length === 0);
check("null/undefined/function param values dropped, real ones kept",
  messy.items[1].page === "locate.html" &&
  Object.keys(messy.items[1].params).join(",") === "keep" &&
  messy.items[1].params.keep === "yes");
check("create() with no items at all yields an empty items array",
  tabA.VW.workspace.get(tabA.VW.workspace.create("Bare")).items.length === 0);

/* ---- name and source handling ---- */
check("empty name falls back to a placeholder",
  tabA.VW.workspace.get(tabA.VW.workspace.create("", [])).name === "Untitled workspace");
check("null name falls back to a placeholder",
  tabA.VW.workspace.get(tabA.VW.workspace.create(null, [])).name === "Untitled workspace");
check("source defaults to manual",
  tabA.VW.workspace.get(tabA.VW.workspace.create("s1", [])).source === "manual");
check("source 'template' is honored",
  tabA.VW.workspace.get(tabA.VW.workspace.create("s2", [], "template")).source === "template");
check("an unrecognized source falls back to manual",
  tabA.VW.workspace.get(tabA.VW.workspace.create("s3", [], "hacked")).source === "manual");

/* ---- touch ---- */
var beforeTouch = tabA.VW.workspace.get(id1);
clock.advance(60000);
var touched = tabA.VW.workspace.touch(id1);
var afterTouch = tabA.VW.workspace.get(id1);
check("touch() returns true for a known id", touched === true);
check("touch() moves lastOpened to the current clock",
  afterTouch.lastOpened === 1756800065000 && afterTouch.lastOpened > beforeTouch.lastOpened);
check("touch() leaves created/name/items/source untouched",
  afterTouch.created === beforeTouch.created && afterTouch.name === beforeTouch.name &&
  afterTouch.source === beforeTouch.source &&
  JSON.stringify(afterTouch.items) === JSON.stringify(beforeTouch.items));
check("touch() does not disturb any other workspace",
  tabA.VW.workspace.get(id2).lastOpened === 1756800005000);
check("tab B sees the touched lastOpened through shared storage",
  tabB.VW.workspace.get(id1).lastOpened === 1756800065000);

var beforeMissTouch = store.data[WS_KEY];
check("touch(unknown id) returns false", tabA.VW.workspace.touch("ws-nope") === false);
check("touch(null) returns false, does not throw", tabA.VW.workspace.touch(null) === false);
check("a failed touch() wrote nothing at all", store.data[WS_KEY] === beforeMissTouch);

/* ---- id collision safety, proven rather than argued ---- */
var detStore = makeStore();
var detTab = makeTab({ store: detStore, clock: makeClock(1756800000000), random: function () { return 0.5; } });
var detA = detTab.VW.workspace.create("A", []);
var detB = detTab.VW.workspace.create("B", []);
check("ids stay unique even with a frozen clock AND a constant Math.random",
  typeof detA === "string" && typeof detB === "string" && detA !== detB);
check("both deterministic workspaces are really stored and retrievable",
  stored(detStore).length === 2 && detTab.VW.workspace.get(detA) !== null &&
  detTab.VW.workspace.get(detB) !== null);

/* ---- corrupt / hostile stored values ---- */
function corruptCheck(label, value, expectLen) {
  var s = makeStore();
  s.data[WS_KEY] = value;
  var t = makeTab({ store: s });
  var threw = false, len = -1;
  try { len = t.VW.workspace.list().length; } catch (e) { threw = true; }
  check("corrupt storage (" + label + "): list() never throws", !threw);
  check("corrupt storage (" + label + "): list() returns " + expectLen, len === expectLen);
  return { store: s, tab: t };
}
corruptCheck("not JSON", "{definitely not json", 0);
corruptCheck("a JSON object, not an array", '{"a":1}', 0);
corruptCheck("a JSON string", '"hello"', 0);
corruptCheck("JSON null", "null", 0);
var partial = corruptCheck("array with junk entries mixed in",
  '[null,3,"x",{"noid":1},{"id":"ws-real","name":"Real","items":[],"created":1,"lastOpened":1,"source":"manual"}]', 1);
check("corrupt storage: the one valid entry survives and is retrievable",
  partial.tab.VW.workspace.get("ws-real") !== null);
check("corrupt storage: a read did NOT rewrite the stored value",
  partial.store.data[WS_KEY].indexOf("noid") !== -1);
var afterWriteId = partial.tab.VW.workspace.create("New one", []);
check("corrupt storage: the next write drops the junk entries",
  stored(partial.store).length === 2 && partial.tab.VW.workspace.get(afterWriteId) !== null);

/* ---- storage refusing to cooperate ---- */
var roTab = makeTab({ store: makeStore({ throwOnWrite: true }) });
var roThrew = false, roResult;
try { roResult = roTab.VW.workspace.create("nope", [{ page: "part.html", params: {} }]); }
catch (e) { roThrew = true; }
check("create() never throws when storage refuses the write", !roThrew);
check("create() returns null when the write did not happen", roResult === null);

var blindTab = makeTab({ store: makeStore({ throwOnRead: true }) });
var blindThrew = false, blindLen = -1;
try { blindLen = blindTab.VW.workspace.list().length; } catch (e) { blindThrew = true; }
check("list() never throws when storage cannot even be read", !blindThrew);
check("list() returns an empty array when storage cannot be read", blindLen === 0);
check("get() returns null when storage cannot be read", blindTab.VW.workspace.get("x") === null);
check("touch() returns false when storage cannot be read", blindTab.VW.workspace.touch("x") === false);

/* BroadcastChannel delivery is asynchronous; everything below waits for it, exactly as
   test_channel_node.js does. */
setTimeout(function () {
  /* ---- the cross-tab notification, over a real BroadcastChannel ---- */
  var creates = [];
  var touches = [];
  for (var i = 0; i < notesInB.length; i++) {
    if (notesInB[i].data.action === "create") creates.push(notesInB[i]);
    if (notesInB[i].data.action === "touch") touches.push(notesInB[i]);
  }
  check("tab B was notified of tab A's creates", creates.length >= 1);
  check("tab B was notified of tab A's touch", touches.length === 1);
  check("the first create notification names the right workspace",
    creates.length >= 1 && creates[0].data.id === id1 && creates[0].data.name === "Work Order 4471");
  check("a create notification carries only {action,id,name,at}",
    creates.length >= 1 &&
    Object.keys(creates[0].data).sort().join(",") === "action,at,id,name");
  check("the touch notification carries the touched id and its new timestamp",
    touches.length === 1 && touches[0].data.id === id1 && touches[0].data.at === 1756800065000);
  check("notifications arrive with the channel's own seq metadata",
    creates.length >= 1 && typeof creates[0].meta.seq === "number" && creates[0].meta.gap === false);

  /* the whole point of the notification: the receiving tab repaints from ITS OWN storage read,
     and really does find what the other tab wrote. */
  var seenByRepaint = tabB.VW.workspace.get(creates[0].data.id);
  check("a notified tab can read the new workspace from its own list()",
    seenByRepaint !== null && seenByRepaint.name === "Work Order 4471");

  var notesBefore = notesInB.length;
  tabA.VW.workspace.list();
  tabA.VW.workspace.get(id1);
  tabA.VW.workspace.get("missing");
  tabA.VW.workspace.touch("missing");
  setTimeout(function () {
    check("read-only calls (and a failed touch) publish nothing", notesInB.length === notesBefore);

    /* ---- the same notification over the storage-event fallback transport ---- */
    var fbStore = makeStore();
    var fbA = makeTab({ store: fbStore, bc: false });
    var fbB = makeTab({ store: fbStore, bc: false });
    check("fallback: BroadcastChannel genuinely hidden from both tabs",
      typeof fbA.BroadcastChannel === "undefined" && typeof fbB.BroadcastChannel === "undefined");

    var fbNotes = [];
    fbB.VW.channel.subscribe("workspace", function (data) { fbNotes.push(data); });
    var fbId = fbA.VW.workspace.create("Fallback WS", [{ page: "pmcs.html", params: { v: "M1078" } }]);
    check("fallback: create() still really stored the workspace",
      typeof fbId === "string" && stored(fbStore).length === 1);

    var envJson = fbStore.data[CHANNEL_KEY];
    check("fallback: the notification was really written to the channel key",
      typeof envJson === "string" && envJson.indexOf("workspace") !== -1);
    for (var j = 0; j < fbB.__storageListeners.length; j++) {
      fbB.__storageListeners[j]({ key: CHANNEL_KEY, newValue: envJson });
    }
    check("fallback: the other tab received the workspace notification",
      fbNotes.length === 1 && fbNotes[0].action === "create" && fbNotes[0].id === fbId);
    check("fallback: that tab then reads the real workspace from shared storage",
      fbB.VW.workspace.get(fbId) !== null && fbB.VW.workspace.get(fbId).name === "Fallback WS");

    console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
    process.exit(failures.length === 0 ? 0 : 1);
  }, 40);
}, 80);
