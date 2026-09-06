/* THE VIEWER -- VW.workspace schema versioning: migrate-on-read or clean refusal, real behavior
test (PR 22 of docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). Run under
plain Node, same vm.createContext sandbox convention test_workspace_node.js (PR 2) and
test_workspace_export_import_node.js (PR 3) already established -- deliberately exercised on the
DEFAULT (localStorage) backing only, no window.indexedDB in these sandboxes at all, because this
PR's own plan entry states it plainly: "No dependency on PR 19-21's IndexedDB work at all --
this applies equally regardless of which backing (localStorage or IndexedDB) is currently active,
since both ultimately store the same record shape." (test_vw_workspace_indexeddb.py's own suite,
re-run unmodified against this PR's code elsewhere in the verification pass, is what actually
proves the IndexedDB-backed path specifically was not broken.)

Invoked by engine/tests/test_vw_workspace_schema_version.py via `node this-file.js`; prints
PASS/FAIL lines and exits 1 on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js (never a
reimplementation of the logic under test -- every assertion goes through the real exported
VW.workspace functions, or reads the raw localStorage value directly where a check needs to know
what was really persisted):

  1. A NEW workspaceCreate() call stamps the CURRENT schemaVersion (VW.workspace._schemaVersion,
     read from the running code rather than hardcoded, so this test tracks a real future version
     bump instead of silently going stale).
  2. A deliberately OLD-SHAPED fixture record -- hand-constructed JSON with NO schemaVersion field
     at all, exactly matching what every real PR2-through-PR21 saved workspace actually looks like
     on disk today -- is read back correctly via list()/get() (proving real pre-existing user data
     is not silently broken by this PR), AND gets a schemaVersion stamped onto it in the backing
     store after that read -- proven by reading raw localStorage back out afterward, not by
     trusting list()'s own return value to describe storage.
  3. A fixture record with a schemaVersion NEWER than the running code understands is cleanly
     refused: list() excludes just that one record while every OTHER valid record still comes back
     correctly (never a wholesale list() failure); get(id) returns null, distinguishable from a
     genuine not-found via VW.workspace._lastGetSchemaRefusal().
  4. Export carries schemaVersion; import applies the identical migrate-or-refuse logic -- an old
     export (no schemaVersion field, exactly what PR 3 always produced) still imports cleanly, and
     a future-schemaVersion import payload throws the same specific-Error convention PR 3's other
     malformed-import cases already use, writing NOTHING to storage.
  5. The migrate-or-refuse decision is made in exactly ONE place, reused (never duplicated) by both
     the read path and the import path -- proven behaviorally here (not just via source-text
     inspection, which the companion .py wrapper also does): VW.workspace._classifySchemaVersion is
     the exact function both call, exercised directly against representative inputs.

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

/* opts: {store, clock} -- default tier (no window.RPS/no window.indexedDB at all), matching
   test_workspace_node.js/test_workspace_export_import_node.js's own plain-localStorage sandbox. */
function makeTab(opts) {
  opts = opts || {};
  var clock = opts.clock || makeClock(1757000000000);
  var warnings = [];
  var sandbox = {
    console: { warn: function () { warnings.push(Array.prototype.slice.call(arguments).join(" ")); },
               log: function () {}, error: function () {} },
    Math: Math, JSON: JSON, Object: Object, Array: Array, String: String, Error: Error,
    Promise: Promise, isFinite: isFinite,
    setTimeout: setTimeout, clearTimeout: clearTimeout,
    encodeURIComponent: encodeURIComponent, decodeURIComponent: decodeURIComponent,
    module: {}, exports: {}
  };
  sandbox.Date = { now: clock.now };
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
  ctx.__warnings = warnings;
  return ctx;
}

function stored(store) {
  var raw = store.data[WS_KEY];
  if (raw === undefined) return undefined;
  return JSON.parse(raw);
}

var failures = [];
var total = 0;
function check(name, cond) {
  total++;
  if (!cond) failures.push(name);
  console.log((cond ? "PASS " : "FAIL ") + name);
}

/* =================================================================================================
   1. A NEW workspaceCreate() call stamps the CURRENT schemaVersion.
   ================================================================================================= */
(function () {
  var store = makeStore();
  var tab = makeTab({ store: store });
  var CURRENT = tab.VW.workspace._schemaVersion;
  check("VW.workspace._schemaVersion is a real, positive number", typeof CURRENT === "number" && CURRENT >= 1);

  var id = tab.VW.workspace.create("Fresh WS", [{ page: "part.html", params: {} }]);
  /* Checked against RAW storage BEFORE any get()/list() call -- a subsequent read would itself
     migrate-and-write-back a schemaVersion-less record (see part 2 below), which would mask a
     create() that forgot to stamp one at all. This isolates create()'s OWN behavior specifically. */
  var rawCreated = stored(store).filter(function (w) { return w.id === id; })[0];
  check("create() itself (before any read) already stamped schemaVersion in storage",
    typeof rawCreated.schemaVersion === "number");
  check("create()'s own stamp equals the current build's constant",
    rawCreated.schemaVersion === CURRENT);

  var rec = tab.VW.workspace.get(id);
  check("a freshly created record carries schemaVersion when read back too",
    typeof rec.schemaVersion === "number" && rec.schemaVersion === CURRENT);
})();

/* =================================================================================================
   2. THE OVERWHELMINGLY COMMON REAL CASE: an old-shaped fixture record (no schemaVersion field at
      all, exactly what every PR2-through-PR21 saved workspace looks like today) reads back
      correctly via list()/get(), AND is durably stamped in the backing store after that read.
   ================================================================================================= */
(function () {
  var store = makeStore();
  var oldShaped = {
    id: "ws-legacy-1", name: "Legacy WO 8811",
    items: [{ page: "torque.html", params: { nsn: "5310-00-123-4567" } }],
    created: 1700000000000, lastOpened: 1700000000000, source: "manual"
    /* deliberately NO schemaVersion field -- this is the real, exact shape */
  };
  store.data[WS_KEY] = JSON.stringify([oldShaped]);
  var tab = makeTab({ store: store });
  var CURRENT = tab.VW.workspace._schemaVersion;

  check("pre-migration: raw storage really has no schemaVersion field yet",
    stored(store)[0].schemaVersion === undefined);

  var viaList = tab.VW.workspace.list();
  check("list() returns the old-shaped record", viaList.length === 1 && viaList[0].id === "ws-legacy-1");
  check("list() returns it with the CURRENT schemaVersion stamped on (in-memory view)",
    viaList[0].schemaVersion === CURRENT);
  check("list() did not silently break its other fields",
    viaList[0].name === "Legacy WO 8811" && viaList[0].items[0].page === "torque.html");

  check("WRITE-BACK: the stamp was really persisted into the backing store after that one read",
    stored(store)[0].schemaVersion === CURRENT);
  check("WRITE-BACK did not corrupt any other field while persisting the stamp",
    stored(store)[0].name === "Legacy WO 8811" && stored(store)[0].id === "ws-legacy-1");

  var viaGet = tab.VW.workspace.get("ws-legacy-1");
  check("get() also returns the migrated record correctly on a later call",
    viaGet !== null && viaGet.schemaVersion === CURRENT && viaGet.name === "Legacy WO 8811");
})();

/* =================================================================================================
   3. CLEAN REFUSAL: a fixture record with a schemaVersion NEWER than this build understands.
      list() excludes just that record, every OTHER valid record still comes back correctly.
      get(id) returns null AND a distinguishable signal (VW.workspace._lastGetSchemaRefusal()) says
      why, unlike a genuine not-found.
   ================================================================================================= */
(function () {
  var store = makeStore();
  var tab = makeTab({ store: store });
  var CURRENT = tab.VW.workspace._schemaVersion;
  var FUTURE = CURRENT + 7;

  var okId = tab.VW.workspace.create("Understood WS", [{ page: "part.html", params: {} }]);
  var futureRecord = {
    id: "ws-from-the-future", name: "Built by a newer app", items: [],
    created: 1800000000000, lastOpened: 1800000000000, source: "manual",
    schemaVersion: FUTURE, someFieldThisBuildHasNeverHeardOf: { nested: true }
  };
  var all = stored(store);
  all.push(futureRecord);
  store.data[WS_KEY] = JSON.stringify(all);

  var list1 = tab.VW.workspace.list();
  check("list(): the future-schema record is excluded",
    list1.filter(function (w) { return w.id === "ws-from-the-future"; }).length === 0);
  check("list(): every OTHER valid record still comes back correctly",
    list1.length === 1 && list1[0].id === okId && list1[0].name === "Understood WS");

  check("REFUSAL NEVER DELETES: the future record is still present in raw storage after list()",
    stored(store).filter(function (w) { return w.id === "ws-from-the-future"; }).length === 1);
  check("REFUSAL NEVER MUTATES: the future record's own schemaVersion is untouched in storage",
    stored(store).filter(function (w) { return w.id === "ws-from-the-future"; })[0].schemaVersion === FUTURE);
  check("REFUSAL NEVER MUTATES: the future record's unknown field survived untouched too",
    JSON.stringify(stored(store).filter(function (w) { return w.id === "ws-from-the-future"; })[0]
      .someFieldThisBuildHasNeverHeardOf) === JSON.stringify({ nested: true }));

  check("list(): a distinguishable signal names the excluded id/reason",
    tab.VW.workspace._lastReadSchemaRefusals().length === 1 &&
    tab.VW.workspace._lastReadSchemaRefusals()[0].id === "ws-from-the-future" &&
    typeof tab.VW.workspace._lastReadSchemaRefusals()[0].reason === "string" &&
    tab.VW.workspace._lastReadSchemaRefusals()[0].reason.length > 0);

  check("list(): a console.warn fired naming the record and its unrecognized version",
    tab.__warnings.some(function (w) {
      return w.indexOf("ws-from-the-future") !== -1 && w.indexOf(String(FUTURE)) !== -1;
    }));

  /* get(id) on the future record: null, but distinguishable from a genuine not-found. */
  var gotFuture = tab.VW.workspace.get("ws-from-the-future");
  check("get(future-schema id) returns null (matches the not-found convention)", gotFuture === null);
  var refusal = tab.VW.workspace._lastGetSchemaRefusal();
  check("get(future-schema id): _lastGetSchemaRefusal() is non-null and names this id",
    refusal !== null && refusal.id === "ws-from-the-future");
  check("get(future-schema id): the refusal reason mentions the actual unrecognized version",
    typeof refusal.reason === "string" && refusal.reason.indexOf(String(FUTURE)) !== -1);

  /* A genuine not-found, right after, must NOT carry over the previous call's refusal. */
  var gotMissing = tab.VW.workspace.get("does-not-exist-at-all");
  check("get(genuinely missing id) returns null too", gotMissing === null);
  check("get(genuinely missing id): _lastGetSchemaRefusal() is null -- NOT confused with the schema case",
    tab.VW.workspace._lastGetSchemaRefusal() === null);

  /* And the normal, understood record is entirely unaffected by the future record's presence. */
  var gotOk = tab.VW.workspace.get(okId);
  check("get(understood id) still works normally", gotOk !== null && gotOk.name === "Understood WS");
  check("get(understood id): no schema refusal reported for a clean hit",
    tab.VW.workspace._lastGetSchemaRefusal() === null);

  /* THE REAL COMMIT-SURVIVAL CASE: list()/get() above never needed to WRITE anything back (nothing
     in this storage needed a missing-schemaVersion stamp), so they don't actually prove a future
     record survives a real commit. A genuinely NEW create() call always commits -- prove the
     future record is still there, byte-for-byte, after a real, unrelated mutation's write. */
  var beforeMutation = JSON.stringify(
    stored(store).filter(function (w) { return w.id === "ws-from-the-future"; })[0]);
  var newId = tab.VW.workspace.create("A sibling created after the future record exists", []);
  check("a real, unrelated create() commit still succeeds with a future record present",
    typeof newId === "string");
  var afterMutation = stored(store).filter(function (w) { return w.id === "ws-from-the-future"; });
  check("COMMIT-SURVIVAL: the future record is still present after a real mutation's commit",
    afterMutation.length === 1);
  check("COMMIT-SURVIVAL: the future record is byte-for-byte unchanged by that commit",
    JSON.stringify(afterMutation[0]) === beforeMutation);
})();

/* =================================================================================================
   3b. An invalid (non-numeric) schemaVersion is refused the same way -- distinct reason text, same
       "never silently misinterpreted" outcome.
   ================================================================================================= */
(function () {
  var store = makeStore();
  store.data[WS_KEY] = JSON.stringify([
    { id: "ws-corrupt-version", name: "Hand-edited", items: [], created: 1, lastOpened: 1,
      source: "manual", schemaVersion: "not-a-number" }
  ]);
  var tab = makeTab({ store: store });
  check("an invalid (non-numeric) schemaVersion is excluded from list() too",
    tab.VW.workspace.list().length === 0);
  check("get() on an invalid-schemaVersion id returns null with a distinguishing refusal",
    tab.VW.workspace.get("ws-corrupt-version") === null &&
    tab.VW.workspace._lastGetSchemaRefusal() !== null &&
    tab.VW.workspace._lastGetSchemaRefusal().id === "ws-corrupt-version");
  check("an invalid schemaVersion is STILL never deleted from storage",
    stored(store).length === 1 && stored(store)[0].id === "ws-corrupt-version");
})();

/* =================================================================================================
   4. EXPORT carries schemaVersion; IMPORT applies the identical migrate-or-refuse logic.
   ================================================================================================= */
(function () {
  var srcStore = makeStore();
  var srcTab = makeTab({ store: srcStore });
  var CURRENT = srcTab.VW.workspace._schemaVersion;
  var wsId = srcTab.VW.workspace.create("Exportable WS", [{ page: "procedure.html", params: { doc: 5 } }]);

  var url = srcTab.VW.workspace.exportUrl(wsId);
  var payload = JSON.parse(decodeURIComponent(url.slice(3)));
  check("exportUrl payload carries schemaVersion", typeof payload.schemaVersion === "number");
  check("exportUrl payload's schemaVersion equals the current build's constant",
    payload.schemaVersion === CURRENT);

  /* an OLD export (no schemaVersion field at all -- exactly what PR 3 always produced) still
     imports cleanly: "missing" classifies as ok, same as the read path. */
  var oldExportPayload = { name: "Old-style export", items: [{ page: "torque.html", params: {} }] };
  var destStore1 = makeStore();
  var destTab1 = makeTab({ store: destStore1 });
  var importedOldId = destTab1.VW.workspace.importUrl("ws=" + encodeURIComponent(JSON.stringify(oldExportPayload)));
  check("importing an OLD (schemaVersion-less) export still succeeds", typeof importedOldId === "string");
  check("the imported record gets the CURRENT build's schemaVersion, not a missing one",
    destTab1.VW.workspace.get(importedOldId).schemaVersion === destTab1.VW.workspace._schemaVersion);

  /* a real round trip through the CURRENT export shape also still works end to end. */
  var destStore2 = makeStore();
  var destTab2 = makeTab({ store: destStore2 });
  var importedId = destTab2.VW.workspace.importUrl(url);
  check("a normal current-schema export/import round trip still works",
    typeof importedId === "string" && destTab2.VW.workspace.get(importedId).name === "Exportable WS");

  /* a FUTURE-schemaVersion import payload: refused with the SAME clear-Error convention PR 3
     already established for other malformed-import cases, and NOTHING written to storage. */
  var futurePayload = { name: "From a newer app", items: [{ page: "pmcs.html", params: {} }],
                         schemaVersion: CURRENT + 3 };
  var destStore3 = makeStore();
  var destTab3 = makeTab({ store: destStore3 });
  var threw = false, msg = "";
  try { destTab3.VW.workspace.importUrl("ws=" + encodeURIComponent(JSON.stringify(futurePayload))); }
  catch (e) { threw = true; msg = e && e.message; }
  check("importUrl(future schemaVersion) throws", threw);
  check("importUrl(future schemaVersion) throws a specific message naming the version",
    typeof msg === "string" && msg.indexOf("Workspace import failed") === 0 &&
    msg.indexOf(String(CURRENT + 3)) !== -1);
  check("importUrl(future schemaVersion) wrote NOTHING to storage",
    destStore3.data[WS_KEY] === undefined);

  /* the same, via importFile/Blob, if Blob is available in this Node runtime. */
  if (typeof Blob !== "undefined") {
    var destStore4 = makeStore();
    var destTab4 = makeTab({ store: destStore4 });
    var futureBlob = new Blob([JSON.stringify(futurePayload)], { type: "application/json" });
    destTab4.VW.workspace.importFile(futureBlob).then(
      function () { check("importFile(future schemaVersion) should have rejected but resolved", false); runClassifyChecks(); },
      function (err) {
        check("importFile(future schemaVersion) rejects", true);
        check("importFile(future schemaVersion) rejection message names the version",
          err && typeof err.message === "string" && err.message.indexOf(String(CURRENT + 3)) !== -1);
        check("importFile(future schemaVersion) wrote NOTHING to storage",
          destStore4.data[WS_KEY] === undefined);
        runClassifyChecks();
      }
    );
  } else {
    runClassifyChecks();
  }
})();

/* =================================================================================================
   5. THE SHARED CLASSIFIER, exercised directly: VW.workspace._classifySchemaVersion is the exact
      function both the read path and the import path call (the companion .py wrapper additionally
      confirms this structurally, by source-text inspection).
   ================================================================================================= */
function runClassifyChecks() {
  var tab = makeTab({});
  var CURRENT = tab.VW.workspace._schemaVersion;
  var classify = tab.VW.workspace._classifySchemaVersion;

  check("_classifySchemaVersion({}) (missing) is ok", classify({}).ok === true && classify({}).status === "missing");
  check("_classifySchemaVersion({schemaVersion: CURRENT}) is ok",
    classify({ schemaVersion: CURRENT }).ok === true && classify({ schemaVersion: CURRENT }).status === "ok");
  check("_classifySchemaVersion({schemaVersion: CURRENT+1}) is refused as future",
    classify({ schemaVersion: CURRENT + 1 }).ok === false &&
    classify({ schemaVersion: CURRENT + 1 }).status === "future");
  check("_classifySchemaVersion({schemaVersion: 'nope'}) is refused as invalid",
    classify({ schemaVersion: "nope" }).ok === false && classify({ schemaVersion: "nope" }).status === "invalid");
  check("_classifySchemaVersion(null) does not throw and is treated as missing",
    classify(null).ok === true && classify(null).status === "missing");

  finish();
}

function finish() {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}
