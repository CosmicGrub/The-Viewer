/* THE VIEWER -- VW.workspace IndexedDB storage migration, real behavior test (PR 21 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). Run under plain Node, same
vm.createContext sandbox convention test_workspace_node.js (PR 2) and test_vw_locks_node.js (PR 20)
already established.

Invoked by engine/tests/test_vw_workspace_indexeddb.py via `node this-file.js`; prints PASS/FAIL
lines and exits 1 on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js (never a
reimplementation of the logic under test -- every assertion goes through the real exported
VW.workspace functions):

  - THE BOOTSTRAP GUARANTEE: with localStorage pre-seeded (simulating a real technician's existing
    PR2/PR3/PR16 data) and the mock IndexedDB's open() DELIBERATELY DEFERRED (a real setTimeout delay,
    proving nothing here is a happy-path coincidence), the VERY FIRST call this sandbox ever makes --
    workspaceList() -- returns that seeded data correctly, synchronously, before the deferred open
    could possibly have fired.
  - THE ONE-TIME MIGRATION: once that deferred IndexedDB open/read resolves and finds the mock
    database empty, the localStorage-sourced bootstrap data is written into it -- proven by reading
    the mock's own durable store afterward, not by asserting a spy was merely called. localStorage's
    own key is confirmed left untouched (not cleared) afterward.
  - CACHE REPLACEMENT: when the mock IndexedDB already holds DIFFERENT records at open time (a prior
    session's own migration), the synchronous bootstrap still serves the localStorage-sourced data
    for that very first call (nothing about the bootstrap guarantee above is weakened), but once the
    async reconcile resolves, the cache is replaced wholesale with IndexedDB's own data -- proven by a
    subsequent call actually returning the IndexedDB-sourced records instead.
  - MUTATIONS: create/touch/delete on the cache-backed path return their normal synchronous result
    (an id / true / true) instantly, AND the mutated array is really persisted into the mock
    IndexedDB's durable store once the async write-through resolves -- both halves proven, not just
    the synchronous one.
  - LITE/LEGACY TIER, OR NO RAW API: workspace functions behave 100% identically to before this PR --
    localStorage read AND written on every call, and indexedDB.open() is never invoked at all, proven
    via the mock's own call counter (not a source-text guess) -- checked both for the raw API missing
    entirely and for the raw API PRESENT but tier non-"modern" (the live-capability-gate proof, same
    style PR 19/20's own suites already use).
  - FAILURE RESILIENCE: indexedDB.open() throwing synchronously, and separately every operation
    erroring out, never throws into or breaks a synchronous caller -- the in-memory cache keeps
    working (create/list/get/touch/delete all keep succeeding) regardless of the persistence layer's
    health.
  - THE ONE-TIME FAILURE TOAST (this file's own R13 "fail loud enough to be seen" discipline, applied
    deliberately here to a REPEATED failure streak only, never a single transient one): once the
    running failure streak crosses the threshold, exactly one toast fires, is never fired again by
    further failures, and did not fire while the streak was still below threshold.
  - THE LARGE-PAYLOAD CASE (the entire point of this migration): a workspace payload sized well past
    a realistic localStorage quota succeeds on the IndexedDB-backed path -- both the synchronous
    return AND the durable mock write are proven -- while the exact same payload against a
    quota-constrained localStorage-only path (the pre-PR-21 behavior, reproduced here via a
    quota-throwing mock store) fails exactly as the old code would have.

Gracefully skips (never false-fails) in an environment without node, same as the rest of this
codebase's node-dependent checks -- enforced by the calling .py wrapper, not this file. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

var WS_KEY = "viewer_workspaces";
var WS_IDB_ROW_KEY = "viewer_workspaces";

/* ---------------------------------------------------------------------------------------------
   localStorage mock -- same shape test_workspace_node.js already established, plus an optional
   quotaBytes ceiling so the "old path would have thrown" half of the large-payload case is a real,
   reproduced QuotaExceededError, not merely asserted in prose.
   --------------------------------------------------------------------------------------------- */
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
      var s = String(v);
      if (typeof opts.quotaBytes === "number" && s.length > opts.quotaBytes) {
        throw new Error("QuotaExceededError: the quota has been exceeded");
      }
      data[k] = s;
    }
  };
}

/* ---------------------------------------------------------------------------------------------
   Mock IndexedDB. Models ONE browser-profile database ("durable" survives across separate open()
   calls the same way a real one would) with a single "kv" object store holding one row, matching
   shared.js's own _WS_IDB_STORE/_WS_IDB_ROW_KEY shape exactly. Every request is genuinely
   asynchronous (setTimeout, even at delay 0 -- Node's event loop never fires it synchronously),
   and every handler is invoked strictly through the callback properties shared.js itself assigns
   (onsuccess/onerror/onupgradeneeded/oncomplete/onabort/onblocked), never called back directly --
   so a bug that forgot to wire one of those up would show up here as a hang, not a false pass.

   opts:
     seed: {viewer_workspaces: [...]}  -- pre-existing durable content (a "prior session already
           migrated" scenario). Omitted -> the mock starts with an empty, freshly-created database.
     openDelayMs: artificial delay before open() resolves (proves the bootstrap sync guarantee is
           not a coincidence of Node's own event-loop speed).
     openThrows / openErrors / openBlocked: failure injection for the open() step.
     readErrors / writeErrors: failure injection for get()/put() respectively.
   --------------------------------------------------------------------------------------------- */
function makeMockIndexedDB(opts) {
  opts = opts || {};
  var durable = {};
  var storeCreated = false;
  if (opts.seed) {
    storeCreated = true;
    for (var k in opts.seed) {
      if (Object.prototype.hasOwnProperty.call(opts.seed, k)) durable[k] = opts.seed[k];
    }
  }
  var openCallCount = 0;
  var putCalls = [];
  var dbHandle = null;

  function makeDbHandle() {
    return {
      objectStoreNames: { contains: function () { return storeCreated; } },
      createObjectStore: function () { storeCreated = true; return {}; },
      transaction: function () {
        var tx = {};
        var ops = [];
        var forcedError = false;
        var store = {
          get: function (key) {
            var req = {};
            ops.push(function () {
              if (opts.readErrors) { forcedError = true; if (req.onerror) req.onerror({}); return; }
              req.result = durable[key];
              if (req.onsuccess) req.onsuccess({});
            });
            return req;
          },
          put: function (value, key) {
            putCalls.push({ key: key, value: value });
            if (opts.writeErrors) { forcedError = true; }
            else { durable[key] = value; }
            return {};
          }
        };
        tx.objectStore = function () { return store; };
        setTimeout(function () {
          for (var i = 0; i < ops.length; i++) ops[i]();
          if (forcedError) {
            if (tx.onerror) tx.onerror({});
            else if (tx.onabort) tx.onabort({});
          } else if (tx.oncomplete) {
            tx.oncomplete({});
          }
        }, 0);
        return tx;
      }
    };
  }

  var indexedDBObj = {
    open: function () {
      openCallCount++;
      var req = {};
      if (opts.openThrows) { throw new Error("mock indexedDB.open threw"); }
      var delay = typeof opts.openDelayMs === "number" ? opts.openDelayMs : 0;
      setTimeout(function () {
        if (opts.openErrors) { if (req.onerror) req.onerror({}); return; }
        if (opts.openBlocked) { if (req.onblocked) req.onblocked({}); return; }
        var freshDb = !storeCreated;
        if (!dbHandle) dbHandle = makeDbHandle();
        req.result = dbHandle;
        if (freshDb && req.onupgradeneeded) req.onupgradeneeded({});
        if (req.onsuccess) req.onsuccess({});
      }, delay);
      return req;
    }
  };

  return {
    indexedDB: indexedDBObj,
    durable: durable,
    putCalls: putCalls,
    openCallCount: function () { return openCallCount; }
  };
}

/* ---------------------------------------------------------------------------------------------
   Sandbox plumbing -- document/window shape mirrors test_vw_locks_node.js's makeDoc()/makeTab(),
   extended with a captured #vw-toast element so the one-time failure toast is inspectable, and
   opts.store/opts.idb/opts.rpsMode to drive the scenario under test.
   --------------------------------------------------------------------------------------------- */
function fakeEl() {
  return { style: {}, setAttribute: function () {}, appendChild: function () {}, textContent: "", className: "" };
}

function makeDoc() {
  var toastEl = null;
  var toastSetCount = 0;   // real invocation counter -- see below for why text equality alone
                            // cannot prove "fired exactly once" (toast()'s message is identical
                            // every time it fires, so comparing text after the fact cannot tell a
                            // single firing apart from several identical re-firings).
  var doc = {
    readyState: "complete",
    getElementById: function (id) { return id === "vw-toast" ? toastEl : null; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    createElement: function () { return fakeEl(); },
    addEventListener: function () {},
    head: fakeEl(), documentElement: fakeEl()
  };
  doc.body = {
    appendChild: function (el) {
      /* toast() assigns el.id = "vw-toast" BEFORE appendChild, then sets el.textContent
         immediately after (on this same first call) -- so this is the one moment to retrofit a
         counting setter onto textContent, before that first assignment happens, catching every
         call (this one included) from here on. Only the toast element is ever instrumented this
         way -- unrelated elements (the footer nav pill, the stale-version banner) stay plain. */
      if (el && el.id === "vw-toast" && !toastEl) {
        toastEl = el;
        var text = el.textContent || "";
        Object.defineProperty(el, "textContent", {
          get: function () { return text; },
          set: function (v) { text = v; toastSetCount++; }
        });
      }
    }
  };
  doc.__toastText = function () { return toastEl ? toastEl.textContent : null; };
  doc.__toastFireCount = function () { return toastSetCount; };
  return doc;
}

/* opts: {store, idb, rpsMode} -- rpsMode omitted -> window.RPS left entirely unset (defaults to
   the "modern" tier, matching _capTier()'s own documented default). idb omitted -> window.indexedDB
   stays genuinely undefined (the raw-API-absent case). */
function makeTab(opts) {
  opts = opts || {};
  var windowObj = {};
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date, Object: Object, Array: Array,
    String: String, Error: Error, Promise: Promise,
    setTimeout: setTimeout, clearTimeout: clearTimeout,
    module: {}, exports: {}
  };
  sandbox.document = makeDoc();
  sandbox.window = windowObj;
  windowObj.addEventListener = function () {};
  windowObj.location = { pathname: "/probe", href: "" };
  windowObj.localStorage = opts.store || makeStore();

  if (opts.rpsMode !== undefined) windowObj.RPS = { mode: opts.rpsMode };
  if (opts.idb) windowObj.indexedDB = opts.idb.indexedDB;
  // else: window.indexedDB stays entirely undefined.

  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
  ctx.__toastText = sandbox.document.__toastText;
  ctx.__toastFireCount = sandbox.document.__toastFireCount;
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

/* =================================================================================================
   1. LITE/LEGACY TIER (or the raw API simply absent): 100% unchanged behavior, IndexedDB never
      touched at all -- proven via the mock's own call counter, both with the raw API missing
      entirely and with it PRESENT but gated off by tier.
   ================================================================================================= */
(function () {
  var store = makeStore();
  var tab = makeTab({ store: store, rpsMode: "legacy" });   // no idb at all
  var id = tab.window.VW.workspace.create("Legacy WS", [{ page: "part.html", params: {} }]);
  check("legacy tier: create() still returns a string id", typeof id === "string");
  check("legacy tier: create() really wrote straight to localStorage",
    stored(store) !== undefined && stored(store).length === 1);
  check("legacy tier: list() reads it back", tab.window.VW.workspace.list().length === 1);
  check("legacy tier: touch()/delete() still work",
    tab.window.VW.workspace.touch(id) === true && tab.window.VW.workspace.delete(id) === true);
})();

(function () {
  var store = makeStore();
  var idb = makeMockIndexedDB();               // raw API PRESENT this time
  var tab = makeTab({ store: store, idb: idb, rpsMode: "lite" });   // but tier is non-modern
  tab.window.VW.workspace.create("Lite WS", [{ page: "part.html", params: {} }]);
  tab.window.VW.workspace.list();
  tab.window.VW.workspace.touch("nope");
  check("lite tier with raw indexedDB present: indexedDB.open() is NEVER called",
    idb.openCallCount() === 0);
  check("lite tier with raw indexedDB present: localStorage still really holds the write",
    stored(store) !== undefined && stored(store).length === 1);
})();

(function () {
  var store = makeStore();
  var idb = makeMockIndexedDB();
  var tab = makeTab({ store: store, idb: idb, rpsMode: "premium" });   // additive flag, not "modern"
  tab.window.VW.workspace.create("Premium-tier WS", []);
  check("premium tier (not exactly 'modern'): indexedDB.open() is still never called",
    idb.openCallCount() === 0);
})();

/* =================================================================================================
   2. THE BOOTSTRAP GUARANTEE: seeded localStorage + a DEFERRED mock open() -- the very first call
      (workspaceList()) must return the seeded data synchronously, before the deferred open could
      possibly have resolved.
   ================================================================================================= */
var bootstrapStore = makeStore();
bootstrapStore.data[WS_KEY] = JSON.stringify([
  { id: "ws-seed-1", name: "Seeded WO 1234", items: [{ page: "torque.html", params: {} }],
    created: 1000, lastOpened: 1000, source: "manual" }
]);
var bootstrapIdb = makeMockIndexedDB({ openDelayMs: 250 });   // deliberately slow
var bootstrapTab = makeTab({ store: bootstrapStore, idb: bootstrapIdb });   // default tier: modern

var bootstrapFirstCall = bootstrapTab.window.VW.workspace.list();
check("bootstrap: the very first call is already synchronously correct",
  bootstrapFirstCall.length === 1 && bootstrapFirstCall[0].id === "ws-seed-1" &&
  bootstrapFirstCall[0].name === "Seeded WO 1234");
check("bootstrap: this happened BEFORE the deliberately-slow mock open() could have resolved",
  bootstrapIdb.durable[WS_IDB_ROW_KEY] === undefined);
check("bootstrap: indexedDB.open() was nonetheless kicked off immediately (fire-and-forget)",
  bootstrapIdb.openCallCount() === 1);

setTimeout(function () {
  /* ===============================================================================================
     3. THE ONE-TIME MIGRATION: once the deferred open/read resolves and finds the mock database
        empty, the localStorage-sourced bootstrap cache is written into it -- and localStorage's own
        key is left untouched (never cleared) afterward.
     =============================================================================================== */
  check("migration: the seeded data was really written into the mock IndexedDB store",
    Array.isArray(bootstrapIdb.durable[WS_IDB_ROW_KEY]) &&
    bootstrapIdb.durable[WS_IDB_ROW_KEY].length === 1 &&
    bootstrapIdb.durable[WS_IDB_ROW_KEY][0].id === "ws-seed-1");
  check("migration: localStorage's own key is left untouched, not cleared",
    stored(bootstrapStore) !== undefined && stored(bootstrapStore).length === 1);
  check("migration: a call AFTER reconcile still returns the (now durably-backed) data correctly",
    bootstrapTab.window.VW.workspace.list().length === 1 &&
    bootstrapTab.window.VW.workspace.get("ws-seed-1") !== null);

  /* ===============================================================================================
     4. CACHE REPLACEMENT: the mock IndexedDB already holds DIFFERENT records at open time (a prior
        session's own migration). The synchronous bootstrap still serves localStorage's data for the
        very first call; once reconcile resolves, the cache is replaced wholesale.
     =============================================================================================== */
  var replaceStore = makeStore();
  replaceStore.data[WS_KEY] = JSON.stringify([
    { id: "ws-stale-local", name: "Stale localStorage copy", items: [], created: 1, lastOpened: 1, source: "manual" }
  ]);
  var replaceIdb = makeMockIndexedDB({
    openDelayMs: 40,
    seed: { viewer_workspaces: [
      { id: "ws-durable-1", name: "Durable IDB copy", items: [], created: 2, lastOpened: 2, source: "manual" }
    ] }
  });
  var replaceTab = makeTab({ store: replaceStore, idb: replaceIdb });

  var replaceFirstCall = replaceTab.window.VW.workspace.list();
  check("cache replacement: the first call still serves the localStorage-sourced bootstrap",
    replaceFirstCall.length === 1 && replaceFirstCall[0].id === "ws-stale-local");

  setTimeout(function () {
    var replaceAfter = replaceTab.window.VW.workspace.list();
    check("cache replacement: a later call reflects the now-authoritative IndexedDB data instead",
      replaceAfter.length === 1 && replaceAfter[0].id === "ws-durable-1");
    check("cache replacement: the stale localStorage-only record is gone from what list() returns",
      replaceAfter.filter(function (w) { return w.id === "ws-stale-local"; }).length === 0);
    check("cache replacement: localStorage itself was never rewritten by this reconcile",
      stored(replaceStore).length === 1 && stored(replaceStore)[0].id === "ws-stale-local");

    /* =============================================================================================
       5. MUTATIONS on the cache-backed path: instant synchronous result AND a real, eventually-
          durable write-through.
       ============================================================================================= */
    var mutStore = makeStore();
    var mutIdb = makeMockIndexedDB();
    var mutTab = makeTab({ store: mutStore, idb: mutIdb });
    var mutId = mutTab.window.VW.workspace.create("Cache-path WS", [{ page: "procedure.html", params: { doc: 7 } }]);
    check("mutation: create() on the cache path returns a string id synchronously",
      typeof mutId === "string");
    check("mutation: list()/get() immediately reflect it, before any write-through has resolved",
      mutTab.window.VW.workspace.list().length === 1 && mutTab.window.VW.workspace.get(mutId) !== null);
    check("mutation: localStorage was NOT written to on the cache-backed path",
      stored(mutStore) === undefined);

    setTimeout(function () {
      check("mutation: create() was durably persisted into the mock IndexedDB store",
        Array.isArray(mutIdb.durable[WS_IDB_ROW_KEY]) && mutIdb.durable[WS_IDB_ROW_KEY].length === 1 &&
        mutIdb.durable[WS_IDB_ROW_KEY][0].id === mutId);

      var touched = mutTab.window.VW.workspace.touch(mutId);
      check("mutation: touch() returns true synchronously", touched === true);

      setTimeout(function () {
        check("mutation: touch() write-through landed in the mock store too",
          mutIdb.durable[WS_IDB_ROW_KEY][0].id === mutId &&
          typeof mutIdb.durable[WS_IDB_ROW_KEY][0].lastOpened === "number");

        var deleted = mutTab.window.VW.workspace.delete(mutId);
        check("mutation: delete() returns true synchronously", deleted === true);
        check("mutation: list() reflects the deletion immediately", mutTab.window.VW.workspace.list().length === 0);

        setTimeout(function () {
          check("mutation: delete() write-through emptied the mock store's row too",
            Array.isArray(mutIdb.durable[WS_IDB_ROW_KEY]) && mutIdb.durable[WS_IDB_ROW_KEY].length === 0);

          runFailureAndPayloadTests();
        }, 20);
      }, 20);
    }, 20);
  }, 80);
}, 320);

/* =================================================================================================
   6/7. FAILURE RESILIENCE + THE ONE-TIME TOAST, and THE LARGE-PAYLOAD CASE. Run last (chained off
   the setTimeout tower above) so they never race the earlier scenarios' own timers.
   ================================================================================================= */
function runFailureAndPayloadTests() {
  /* ---- indexedDB.open() throws synchronously: never breaks a synchronous caller. ---- */
  var throwIdb = { indexedDB: { open: function () { throw new Error("boom"); } } };
  var throwStore = makeStore();
  var throwTab = makeTab({ store: throwStore, idb: throwIdb });
  var throwThrew = false, throwId = null;
  try { throwId = throwTab.window.VW.workspace.create("Still works", [{ page: "part.html", params: {} }]); }
  catch (e) { throwThrew = true; }
  check("failure: a synchronously-throwing indexedDB.open() never propagates into the caller",
    !throwThrew);
  check("failure: create() still succeeds via the in-memory cache regardless",
    typeof throwId === "string" && throwTab.window.VW.workspace.get(throwId) !== null);
  check("failure: list()/touch()/delete() all still work normally afterward",
    throwTab.window.VW.workspace.list().length === 1 &&
    throwTab.window.VW.workspace.touch(throwId) === true &&
    throwTab.window.VW.workspace.delete(throwId) === true);

  /* ---- every operation erroring out: same guarantee, via the async error paths this time. ---- */
  var erroringIdb = makeMockIndexedDB({ openErrors: true });
  var erroringStore = makeStore();
  var erroringTab = makeTab({ store: erroringStore, idb: erroringIdb });

  /* The FIRST call on a fresh tab queues TWO independent failed open() attempts -- one from
     _wsEnsureCache()'s own bootstrap reconcile, one from this same create()'s write-through --
     both real, both counted, since they really are two separate IndexedDB operations that both
     failed. Every call after that queues exactly one (reconcile only ever runs once per page). The
     sequencing below waits out each call's own async fallout before making the next one, so the
     streak's exact count (2, then 3, then 4) is asserted against reality rather than guessed. */
  var erroringId = erroringTab.window.VW.workspace.create("Also still works", []);
  check("failure: create() succeeds synchronously even though every IDB open will error",
    typeof erroringId === "string");
  check("toast: silent before this call's own async failures have even resolved yet",
    erroringTab.__toastText() === null);

  setTimeout(function () {
    check("toast: still silent after the first call's 2 queued failures (streak 2, threshold 3)",
      erroringTab.__toastText() === null);

    erroringTab.window.VW.workspace.create("second call -- pushes the streak to 3", []);
    setTimeout(function () {
      check("toast: fires once the streak reaches the threshold",
        typeof erroringTab.__toastText() === "string" &&
        erroringTab.__toastText().indexOf("lost if this tab is closed") !== -1);

      check("toast: really fired exactly once so far (a real invocation count, not just text)",
        erroringTab.__toastFireCount() === 1);

      erroringTab.window.VW.workspace.create("third call -- streak keeps growing", []);
      setTimeout(function () {
        check("toast: fires exactly once, never re-fired by further failures (invocation count still 1)",
          erroringTab.__toastFireCount() === 1);

        runLargePayloadTests();
      }, 20);
    }, 20);
  }, 20);
}

/* =================================================================================================
   8. THE LARGE-PAYLOAD CASE -- the entire point of the migration. A payload sized comfortably past
   a realistic localStorage quota succeeds, durably, on the IndexedDB-backed path, while the exact
   same payload against a quota-constrained localStorage-only path fails exactly as the pre-PR-21
   code would have.
   ================================================================================================= */
function runLargePayloadTests() {
  var QUOTA_BYTES = 5 * 1024 * 1024;             // ~5MB, a realistic localStorage ceiling
  var bigBlob = new Array(8 * 1024 * 1024).join("x");   // ~8MB, well past that ceiling
  var bigItems = [{ page: "procedure.html", params: { blob: bigBlob } }];

  /* ---- the OLD path: localStorage-only, quota-constrained -- reproduces the pre-PR-21 failure
     mode concretely (a real thrown QuotaExceededError inside _wsWrite, caught, reported as null),
     not merely asserted in prose. ---- */
  var oldStore = makeStore({ quotaBytes: QUOTA_BYTES });
  var oldTab = makeTab({ store: oldStore, rpsMode: "legacy" });   // no idb at all -- the old path
  var oldThrew = false, oldResult;
  try { oldResult = oldTab.window.VW.workspace.create("Too big for localStorage", bigItems); }
  catch (e) { oldThrew = true; }
  check("large payload, OLD path: create() never itself throws (storage failure is reported, not thrown)",
    !oldThrew);
  check("large payload, OLD path: create() returns null -- the quota really was exceeded",
    oldResult === null);
  check("large payload, OLD path: nothing was left half-written in localStorage",
    oldStore.data[WS_KEY] === undefined);

  /* ---- the NEW path: IndexedDB-backed, no such ceiling -- succeeds both synchronously and,
     eventually, durably. ---- */
  var newIdb = makeMockIndexedDB();
  var newStore = makeStore({ quotaBytes: QUOTA_BYTES });   // same tiny quota -- must never be hit
  var newTab = makeTab({ store: newStore, idb: newIdb });
  var newThrew = false, newId;
  try { newId = newTab.window.VW.workspace.create("Fits via IndexedDB", bigItems); }
  catch (e) { newThrew = true; }
  check("large payload, NEW path: create() never throws", !newThrew);
  check("large payload, NEW path: create() succeeds synchronously with a real id",
    typeof newId === "string");
  check("large payload, NEW path: the full-size blob is immediately readable back from the cache",
    newTab.window.VW.workspace.get(newId) !== null &&
    newTab.window.VW.workspace.get(newId).items[0].params.blob.length === bigBlob.length);
  check("large payload, NEW path: localStorage's own (tiny) quota was never even touched",
    newStore.data[WS_KEY] === undefined);

  setTimeout(function () {
    check("large payload, NEW path: the full-size record was really persisted into IndexedDB",
      Array.isArray(newIdb.durable[WS_IDB_ROW_KEY]) && newIdb.durable[WS_IDB_ROW_KEY].length === 1 &&
      newIdb.durable[WS_IDB_ROW_KEY][0].items[0].params.blob.length === bigBlob.length);

    finish();
  }, 30);
}

function finish() {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}
