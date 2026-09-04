/* THE VIEWER -- VW.workspace export/import real round-trip test, run under plain Node.

Invoked by engine/tests/test_workspace_export_import.py via `node this-file.js`; prints PASS/FAIL
lines and exits 1 on any failure, matching test_workspace_node.js's own convention (which this file
mirrors closely -- same makeStore/makeTab/makeClock/check helpers, same vm.createContext-per-tab
approach).

Why this is a real test rather than a reimplementation of the logic under test:

  * Every assertion goes through the actual exported VW.workspace.exportUrl/exportFile/importUrl/
    importFile functions loaded from the real engine/ui/shared.js. Nothing here reimplements the
    query-string encoding, the JSON shape, or the shape-validation rules -- where a check needs to
    know what was really persisted, it reads the raw localStorage key directly, exactly as
    test_workspace_node.js does for create()/list()/get()/touch().

  * exportUrl->importUrl and exportFile->importFile round-trips use TWO SEPARATE localStorage
    stores (unlike test_workspace_node.js's two tabs sharing one store) -- one per "browser" --
    because the whole point of export/import is portability to a browser that does NOT already
    share storage. A round trip that only worked because both sides secretly read the same
    underlying store would not actually prove anything about exportUrl/exportFile's payload.

  * The malformed-import cases assert not just that the call throws/rejects with a specific
    message, but that the destination store's `viewer_workspaces` key is byte-for-byte unchanged
    afterward (or still completely absent) -- "validated before being written" is a claim about
    storage, not just about the return value, so it is checked against storage directly.

  * The "never trust an incoming id" cases craft a payload with a spoofed id-shaped field and
    assert the returned id is neither that spoofed value nor equal between two separate imports of
    the exact same payload -- proving a fresh id is minted every time, not merely once.

Node's real global Blob (Node 18+, matching this project's node_availability convention elsewhere)
is used for the exportFile/importFile path so that leg is exercised against a production Blob
implementation, not a stand-in.

Gracefully skips (never false-fails) in an environment without node, same as the rest of this
codebase's node-dependent checks -- enforced by the calling .py wrapper, not this file. */
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
    }
  };
}

function makeClock(start) {
  var t = start;
  return { now: function () { return t; }, advance: function (ms) { t += ms; } };
}

/* opts: {store, clock, bc (default true)} */
function makeTab(opts) {
  opts = opts || {};
  var clock = opts.clock || makeClock(1756800000000);
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
  sandbox.document = {
    readyState: "complete", getElementById: function () { return null; },
    querySelector: function () { return null; }, createElement: function () { return fakeEl(); },
    addEventListener: function () {}, body: fakeEl(), head: fakeEl(), documentElement: fakeEl()
  };
  sandbox.window = sandbox;
  sandbox.window.addEventListener = function () {};
  sandbox.window.location = { pathname: "/probe", href: "" };
  sandbox.window.localStorage = opts.store || makeStore();
  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
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

function stored(store) {
  var raw = store.data[WS_KEY];
  if (raw === undefined) return undefined;
  return JSON.parse(raw);
}

/* ============================================================================================
   exportUrl(id) / exportFile(id) -- not-found convention and payload shape
   ============================================================================================ */
var srcStore = makeStore();
var srcTab = makeTab({ store: srcStore, clock: makeClock(1756800000000) });

check("exportUrl(unknown id) returns null", srcTab.VW.workspace.exportUrl("nope") === null);
check("exportFile(unknown id) returns null", srcTab.VW.workspace.exportFile("nope") === null);

var origId = srcTab.VW.workspace.create("Work Order 9001", [
  { page: "procedure.html", params: { doc: 12, page: 340 } },
  { page: "torque.html", params: { nsn: "5310-00-123-4567" } }
], "template");
var origRecord = srcTab.VW.workspace.get(origId);

var url1 = srcTab.VW.workspace.exportUrl(origId);
check("exportUrl returns a string starting with ws=", typeof url1 === "string" && url1.indexOf("ws=") === 0);
check("exportUrl output does not leak the internal id", url1.indexOf(origId) === -1);
check("exportUrl output does not leak created/lastOpened timestamps",
  url1.indexOf(String(origRecord.created)) === -1);

var decodedPayload1 = JSON.parse(decodeURIComponent(url1.slice(3)));
check("exportUrl payload carries exactly {name, items}",
  Object.keys(decodedPayload1).sort().join(",") === "items,name");
check("exportUrl payload name matches the source workspace", decodedPayload1.name === "Work Order 9001");
check("exportUrl payload items match the source workspace",
  JSON.stringify(decodedPayload1.items) === JSON.stringify(origRecord.items));

var blob1 = srcTab.VW.workspace.exportFile(origId);
check("exportFile returns a real Blob", blob1 instanceof Blob);
check("exportFile Blob has type application/json", blob1.type === "application/json");

/* ============================================================================================
   exportUrl -> importUrl round trip, across TWO SEPARATE stores (two different browsers)
   ============================================================================================ */
var destStoreA = makeStore();
var destClockA = makeClock(1756900000000);          // a different "now" than the source browser
var destTabA = makeTab({ store: destStoreA, clock: destClockA });

var newIdFromUrl = destTabA.VW.workspace.importUrl(url1);
check("importUrl returns a string id", typeof newIdFromUrl === "string" && newIdFromUrl.length > 3);
check("importUrl mints a DIFFERENT id than the source workspace's own id", newIdFromUrl !== origId);

var importedFromUrl = destTabA.VW.workspace.get(newIdFromUrl);
check("imported (url) workspace has the same name as the source", importedFromUrl.name === "Work Order 9001");
check("imported (url) workspace has the same items as the source",
  JSON.stringify(importedFromUrl.items) === JSON.stringify(origRecord.items));
check("imported (url) workspace source is 'manual' regardless of the original's source",
  importedFromUrl.source === "manual");
check("imported (url) workspace gets a FRESH created timestamp (the dest browser's own clock)",
  importedFromUrl.created === 1756900000000 && importedFromUrl.created !== origRecord.created);

check("importUrl accepts a leading '?' fragment too (e.g. location.search)",
  typeof destTabA.VW.workspace.importUrl("?" + url1) === "string");

var destStoreB = makeStore();
var destTabB = makeTab({ store: destStoreB, clock: makeClock(1756900500000) });
var idWithSurroundingParams = destTabB.VW.workspace.importUrl("a=1&" + url1 + "&b=2");
check("importUrl finds ws= among other query params",
  typeof idWithSurroundingParams === "string" &&
  destTabB.VW.workspace.get(idWithSurroundingParams).name === "Work Order 9001");

/* ============================================================================================
   exportFile -> importFile round trip, across two more separate stores, real Blob both ways
   ============================================================================================ */
var destStoreC = makeStore();
var destTabC = makeTab({ store: destStoreC, clock: makeClock(1756901000000) });

destTabC.VW.workspace.importFile(blob1).then(function (newIdFromFile) {
  check("importFile resolves to a string id", typeof newIdFromFile === "string" && newIdFromFile.length > 3);
  check("importFile mints a DIFFERENT id than the source workspace's own id", newIdFromFile !== origId);
  check("importFile mints a DIFFERENT id than importUrl's own import of the same workspace",
    newIdFromFile !== newIdFromUrl);

  var importedFromFile = destTabC.VW.workspace.get(newIdFromFile);
  check("imported (file) workspace has the same name as the source", importedFromFile.name === "Work Order 9001");
  check("imported (file) workspace has the same items as the source",
    JSON.stringify(importedFromFile.items) === JSON.stringify(origRecord.items));
  check("imported (file) workspace source is 'manual'", importedFromFile.source === "manual");

  runMalformedImportChecks();
}, function (err) {
  check("importFile round trip did not reject (it did: " + (err && err.message) + ")", false);
  runMalformedImportChecks();
});

/* ============================================================================================
   Malformed / tampered imports: clean rejection, and NOTHING written to storage
   ============================================================================================ */
function runMalformedImportChecks() {
  /* ---- importUrl: garbage, wrong shape, missing page, no ws key ---- */
  var badStore1 = makeStore();
  var badTab1 = makeTab({ store: badStore1 });
  var before1 = badTab1.VW.workspace.list().length;
  var threw1 = false, msg1 = "";
  try { badTab1.VW.workspace.importUrl("ws=" + encodeURIComponent("{not valid json")); }
  catch (e) { threw1 = true; msg1 = e && e.message; }
  check("importUrl(garbage JSON) throws", threw1);
  check("importUrl(garbage JSON) throws a specific, non-generic message",
    typeof msg1 === "string" && msg1.length > 10 && msg1.indexOf("JSON") !== -1);
  check("importUrl(garbage JSON) wrote NOTHING to storage",
    badTab1.VW.workspace.list().length === before1 && badStore1.data[WS_KEY] === undefined);

  var badStore2 = makeStore();
  var badTab2 = makeTab({ store: badStore2 });
  var threw2 = false, msg2 = "";
  try {
    badTab2.VW.workspace.importUrl("ws=" + encodeURIComponent(JSON.stringify(["array", "not", "object"])));
  } catch (e) { threw2 = true; msg2 = e && e.message; }
  check("importUrl(valid JSON, wrong top-level shape -- an array) throws", threw2);
  check("importUrl(wrong shape) message is specific",
    typeof msg2 === "string" && msg2.toLowerCase().indexOf("object") !== -1);
  check("importUrl(wrong shape) wrote NOTHING to storage", badStore2.data[WS_KEY] === undefined);

  var badStore3 = makeStore();
  var badTab3 = makeTab({ store: badStore3 });
  var threw3 = false, msg3 = "";
  try {
    badTab3.VW.workspace.importUrl("ws=" + encodeURIComponent(JSON.stringify({ name: "X" })));
  } catch (e) { threw3 = true; msg3 = e && e.message; }
  check("importUrl(object missing items) throws", threw3);
  check("importUrl(object missing items) wrote NOTHING to storage", badStore3.data[WS_KEY] === undefined);

  var badStore4 = makeStore();
  var badTab4 = makeTab({ store: badStore4 });
  var threw4 = false, msg4 = "";
  try {
    badTab4.VW.workspace.importUrl("ws=" + encodeURIComponent(
      JSON.stringify({ name: "X", items: [{ params: { a: "1" } }] })));
  } catch (e) { threw4 = true; msg4 = e && e.message; }
  check("importUrl(item missing page) throws", threw4);
  check("importUrl(item missing page) message mentions the specific problem",
    typeof msg4 === "string" && msg4.toLowerCase().indexOf("page") !== -1);
  check("importUrl(item missing page) wrote NOTHING to storage", badStore4.data[WS_KEY] === undefined);

  var badStore5 = makeStore();
  var badTab5 = makeTab({ store: badStore5 });
  var threw5 = false;
  try { badTab5.VW.workspace.importUrl("foo=bar&baz=qux"); }
  catch (e) { threw5 = true; }
  check("importUrl(no ws= present at all) throws", threw5);
  check("importUrl(no ws=) wrote NOTHING to storage", badStore5.data[WS_KEY] === undefined);

  /* a store that already has a real workspace: prove a rejected import leaves EXISTING data
     untouched too, not just "still empty". */
  var mixedStore = makeStore();
  var mixedTab = makeTab({ store: mixedStore });
  mixedTab.VW.workspace.create("Keep me", [{ page: "part.html", params: {} }]);
  var beforeMixed = mixedStore.data[WS_KEY];
  var mixedThrew = false;
  try { mixedTab.VW.workspace.importUrl("ws=garbage-not-json"); } catch (e) { mixedThrew = true; }
  check("a rejected import throws even with an existing workspace present", mixedThrew);
  check("a rejected import leaves an EXISTING workspace's storage byte-for-byte unchanged",
    mixedStore.data[WS_KEY] === beforeMixed);

  /* ---- importFile: same shape rules, over the Blob/Promise path ---- */
  var fileBadStore1 = makeStore();
  var fileBadTab1 = makeTab({ store: fileBadStore1 });
  var badBlob1 = new Blob(["not json at all"], { type: "application/json" });

  var fileBadStore2 = makeStore();
  var fileBadTab2 = makeTab({ store: fileBadStore2 });
  var badBlob2 = new Blob([JSON.stringify({ name: "Y", items: [{ page: "" }] })], { type: "application/json" });

  var fileBadStore3 = makeStore();
  var fileBadTab3 = makeTab({ store: fileBadStore3 });

  fileBadTab1.VW.workspace.importFile(badBlob1).then(
    function () { check("importFile(garbage text) should have rejected but resolved", false); },
    function (err) {
      check("importFile(garbage text) rejects", true);
      check("importFile(garbage text) rejection has a specific message",
        err && typeof err.message === "string" && err.message.indexOf("JSON") !== -1);
      check("importFile(garbage text) wrote NOTHING to storage", fileBadStore1.data[WS_KEY] === undefined);
    }
  ).then(function () {
    return fileBadTab2.VW.workspace.importFile(badBlob2).then(
      function () { check("importFile(empty page) should have rejected but resolved", false); },
      function (err) {
        check("importFile(empty page) rejects", true);
        check("importFile(empty page) message mentions the specific problem",
          err && typeof err.message === "string" && err.message.toLowerCase().indexOf("page") !== -1);
        check("importFile(empty page) wrote NOTHING to storage", fileBadStore2.data[WS_KEY] === undefined);
      }
    );
  }).then(function () {
    return fileBadTab3.VW.workspace.importFile(null).then(
      function () { check("importFile(null) should have rejected but resolved", false); },
      function (err) {
        check("importFile(null blob) rejects", true);
        check("importFile(null blob) wrote NOTHING to storage", fileBadStore3.data[WS_KEY] === undefined);
      }
    );
  }).then(runNeverTrustIdChecks, function (e) {
    check("malformed importFile checks ran without an unexpected throw (they did: " +
      (e && e.message) + ")", false);
    runNeverTrustIdChecks();
  });
}

/* ============================================================================================
   "never trust an incoming id" -- a payload that smuggles in an id-shaped field
   ============================================================================================ */
function runNeverTrustIdChecks() {
  var spoofedId = "ws-SPOOFED-DO-NOT-USE";
  var spoofedPayload = { id: spoofedId, name: "Sneaky import", items: [{ page: "pmcs.html", params: {} }] };
  var spoofedQs = "ws=" + encodeURIComponent(JSON.stringify(spoofedPayload));

  var idStore1 = makeStore();
  var idTab1 = makeTab({ store: idStore1 });
  var got1 = idTab1.VW.workspace.importUrl(spoofedQs);
  check("importUrl with a spoofed id field still returns a string id", typeof got1 === "string");
  check("importUrl NEVER reuses an id-shaped field present in the payload", got1 !== spoofedId);

  var idTab2 = makeTab({ store: idStore1 });         // same store, second import of the SAME payload
  var got2 = idTab2.VW.workspace.importUrl(spoofedQs);
  check("a second import of the identical payload mints yet another fresh id (not spoofedId either)",
    got2 !== spoofedId && got2 !== got1);
  check("both spoofed-id imports are really stored as separate workspaces",
    idTab1.VW.workspace.list().length === 2);

  var idStore3 = makeStore();
  var idTab3 = makeTab({ store: idStore3 });
  var spoofedBlob = new Blob([JSON.stringify(spoofedPayload)], { type: "application/json" });
  idTab3.VW.workspace.importFile(spoofedBlob).then(function (got3) {
    check("importFile with a spoofed id field still resolves to a string id", typeof got3 === "string");
    check("importFile NEVER reuses an id-shaped field present in the payload", got3 !== spoofedId);
    finish();
  }, function (err) {
    check("importFile spoofed-id case should not have rejected (it did: " + (err && err.message) + ")", false);
    finish();
  });
}

function finish() {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}
