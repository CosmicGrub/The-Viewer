/* THE VIEWER -- VW.workspace.exportFileNative/importFileNative, real behavior test (PR 23 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). Run under plain Node, same
vm.createContext sandbox convention test_vw_locks_node.js (PR 20) and
test_workspace_export_import_node.js (PR 3) already established (Promise/setTimeout added to the
sandbox, async assertions chained via plain .then() callbacks -- never async/await -- ending in a
single finish() call). Node's real global Blob (Node 18+, same convention PR 3's own node test
already uses) backs the fallback-path assertions.

Invoked by engine/tests/test_vw_workspace_fsa.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js:
  - FALLBACK PATH (fileSystemAccess false): exportFileNative() performs the EXACT SAME
    Blob/URL.createObjectURL/<a download> pattern workspaces.html's own downloadFile() already
    uses -- proven by mocking URL.createObjectURL and confirming it is invoked with a real Blob
    whose text is exactly the JSON _wsExportPayload()/exportFile() already produce, a real
    <a> element is clicked, and the call resolves true.
  - NATIVE PATH, FRESH HANDLE (fileSystemAccess true, nothing remembered yet): showSaveFilePicker()
    is called exactly once with a JSON-typed filter and a suggested name derived from the
    workspace's own name; the mocked handle's createWritable()/write()/close() chain receives the
    exact same JSON payload; the call resolves true; the handle is remembered.
  - WRITE-BACK-IN-PLACE: a SECOND exportFileNative() call for the SAME id, same tab, reuses the
    remembered handle -- proven by a call-count spy on showSaveFilePicker staying at 1 across both
    calls, and the SAME handle object receiving the second write.
  - PERMISSION RE-VERIFICATION: the remembered handle's own queryPermission()/requestPermission()
    are called before every reuse attempt -- never assumed still-good. When they report the
    permission has been revoked/denied, the stale handle is dropped and exportFileNative() falls
    back to a FRESH showSaveFilePicker() call (call count advances to 2, the new handle receives
    the write, the old handle receives no further writes).
  - CANCEL IS NOT AN ERROR: showSaveFilePicker() rejecting with a real AbortError resolves
    exportFileNative() to false (never rejects); showOpenFilePicker() rejecting the same way
    resolves importFileNative() to null (never rejects). A DIFFERENT rejection (a genuine failure)
    still propagates as a real rejection in both directions -- proven separately, so "cancel never
    rejects" isn't accidentally "nothing ever rejects".
  - importFileNative() ROUTES THROUGH THE EXISTING _wsImportFromJson() -- never a second,
    independently-typed validation copy -- proven by feeding it a payload with a schemaVersion PR
    22's own _wsClassifyRecordSchema() genuinely refuses (newer than this build understands) and
    confirming the SAME "Workspace import failed: ..." specific-Error convention PR 22 already
    established, not a different/generic message a hand-rolled second check might produce.
  - importFileNative() SUCCESS remembers the handle keyed by the NEWLY CREATED id -- proven by a
    subsequent exportFileNative() call for that id reusing it (showSaveFilePicker never called)
    even though this id was never touched by an earlier exportFileNative() call at all.
  - importFileNative() REJECTS CLEARLY when fileSystemAccess is false -- never silently no-ops --
    proven by awaiting a real rejection with a specific message.
  - VW.channel / VW.workspace's original 10 documented members / VW.windows / VW.capabilities are
    untouched by this PR (runtime shape check -- the source-level "diff touches nothing else" check
    lives in the Python driver).

Gracefully skips (never false-fails) in an environment without node, same as the rest of this
codebase's node-dependent checks -- enforced by the calling .py wrapper, not this file. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

/* ---- fake DOM: enough for the fallback path's Blob/<a download> trigger, and enough for the
   native path's own (minimal) document access via shared.js's other, untouched code. ---- */
function makeAnchor() {
  var a = { style: {}, href: "", download: "", clicked: 0, parentNode: null,
    setAttribute: function () {}, click: function () { a.clicked++; } };
  return a;
}
function makeDoc() {
  var body = {};
  body.appendChild = function (el) { el.parentNode = body; };
  body.removeChild = function (el) { el.parentNode = null; };
  return {
    readyState: "complete",
    getElementById: function () { return null; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    createElement: function (tag) {
      return tag === "a" ? makeAnchor() : { style: {}, setAttribute: function () {}, appendChild: function () {}, textContent: "" };
    },
    addEventListener: function () {},
    body: body, head: { appendChild: function () {} }, documentElement: {}
  };
}

/* ---- fake FileSystemFileHandle: records every write, and lets a test script its own
   queryPermission()/requestPermission() responses (including changing them BETWEEN two calls, to
   simulate a revoked grant). ---- */
function makeFakeHandle(opts) {
  opts = opts || {};
  var handle = {
    _writes: [], _closedCount: 0, _queryCalls: 0, _requestCalls: 0,
    _queryState: opts.queryState !== undefined ? opts.queryState : "granted",
    _requestState: opts.requestState !== undefined ? opts.requestState : "granted",
    queryPermission: function () {
      handle._queryCalls++;
      return Promise.resolve(handle._queryState);
    },
    requestPermission: function () {
      handle._requestCalls++;
      return Promise.resolve(handle._requestState);
    },
    createWritable: function () {
      return Promise.resolve({
        write: function (text) { handle._writes.push(text); return Promise.resolve(); },
        close: function () { handle._closedCount++; return Promise.resolve(); }
      });
    },
    getFile: function () {
      return Promise.resolve({ text: function () { return Promise.resolve(opts.fileText || ""); } });
    }
  };
  return handle;
}

/* A spy-wrapped showSaveFilePicker/showOpenFilePicker: behavior is one of
   {handle: h} (resolve with that handle / [that handle]), {abort: true} (reject AbortError), or
   {error: e} (reject with e). .calls records every options object passed in. */
function makeSavePicker(behavior) {
  var calls = [];
  function fn(opts) {
    calls.push(opts);
    if (behavior.abort) { var e = new Error("The user aborted a request."); e.name = "AbortError"; return Promise.reject(e); }
    if (behavior.error) return Promise.reject(behavior.error);
    return Promise.resolve(behavior.handle);
  }
  fn.calls = calls;
  return fn;
}
function makeOpenPicker(behavior) {
  var calls = [];
  function fn(opts) {
    calls.push(opts);
    if (behavior.abort) { var e = new Error("The user aborted a request."); e.name = "AbortError"; return Promise.reject(e); }
    if (behavior.error) return Promise.reject(behavior.error);
    return Promise.resolve([behavior.handle]);
  }
  fn.calls = calls;
  return fn;
}

/* Builds one fresh sandbox/tab, loads the real shared.js into it, and returns the vm context.
   opts:
     rpsMode: "modern" (default here, unless explicitly overridden) -> window.RPS = {mode: ...}.
       Passing "lite"/"legacy" (or omitting showSaveFilePicker/showOpenFilePicker entirely) is how
       the fileSystemAccess-false scenarios are built, matching PR 19/20's own convention.
     showSaveFilePicker / showOpenFilePicker: functions (from makeSavePicker/makeOpenPicker above),
       or omitted entirely (raw API absent).
     urlCalls: an array this tab's URL.createObjectURL pushes every Blob it is given onto. */
function makeTab(opts) {
  opts = opts || {};
  var windowObj = {};
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date, Object: Object, Array: Array,
    String: String, Error: Error, Promise: Promise, isFinite: isFinite,
    setTimeout: setTimeout, clearTimeout: clearTimeout,
    module: {}, exports: {}
  };
  if (typeof Blob !== "undefined") sandbox.Blob = Blob;
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
  windowObj.RPS = { mode: opts.rpsMode || "modern" };
  if (opts.showSaveFilePicker) windowObj.showSaveFilePicker = opts.showSaveFilePicker;
  if (opts.showOpenFilePicker) windowObj.showOpenFilePicker = opts.showOpenFilePicker;

  var urlCalls = opts.urlCalls || [];
  sandbox.URL = {
    createObjectURL: function (blob) { urlCalls.push(blob); return "blob:mock-" + urlCalls.length; },
    revokeObjectURL: function () {}
  };

  sandbox.navigator = {};
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
   0) Basic shape sanity: both functions exist off VW.workspace, and _capabilities.fileSystemAccess
      genuinely gates true/false the way PR 19 already established (belt-and-suspenders -- the real
      gate itself is PR 19's own, untouched, tested in test_vw_capabilities.py).
   ================================================================================================ */
(function () {
  var tabOn = makeTab({ rpsMode: "modern", showSaveFilePicker: makeSavePicker({}), showOpenFilePicker: makeOpenPicker({}) });
  check("VW.workspace.exportFileNative is a function", typeof tabOn.window.VW.workspace.exportFileNative === "function");
  check("VW.workspace.importFileNative is a function", typeof tabOn.window.VW.workspace.importFileNative === "function");
  check("sanity: fileSystemAccess reads true (raw API present + tier modern)", tabOn.window.VW.capabilities.fileSystemAccess === true);

  var tabOff = makeTab({ rpsMode: "modern" });   // no showSaveFilePicker/showOpenFilePicker given
  check("sanity: fileSystemAccess reads false (raw API absent)", tabOff.window.VW.capabilities.fileSystemAccess === false);
})();

/* ================================================================================================
   1) FALLBACK PATH (fileSystemAccess false): the exact same Blob/URL.createObjectURL/<a download>
      pattern downloadFile() already uses -- a real Blob with the correct JSON, a real anchor
      click, and a true resolution.
   ================================================================================================ */
function runFallbackTests(next) {
  var urlCalls = [];
  var tab = makeTab({ rpsMode: "modern", urlCalls: urlCalls });   // no native pickers -> fileSystemAccess false
  var VW = tab.window.VW;
  var id = VW.workspace.create("Fallback WS", [{ page: "/torque", params: { q: "m4" } }], "manual");
  var expectedPayload = { name: "Fallback WS", items: [{ page: "/torque", params: { q: "m4" } }], schemaVersion: VW.workspace._schemaVersion };

  VW.workspace.exportFileNative(id).then(function (result) {
    check("fallback: resolves true once the download was triggered", result === true);
    check("fallback: URL.createObjectURL was called exactly once", urlCalls.length === 1);
    check("fallback: it was called with a real Blob", urlCalls[0] && typeof urlCalls[0].text === "function");
    return urlCalls[0].text().then(function (text) {
      check("fallback: the Blob's JSON matches _wsExportPayload()/exportFile()'s own shape exactly",
        text === JSON.stringify(expectedPayload));
      check("fallback: the Blob's content-type is application/json", urlCalls[0].type === "application/json");
      next();
    });
  }, function (e) {
    check("runFallbackTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   2) NATIVE PATH, fresh handle: showSaveFilePicker() called once with a JSON filter + a suggested
      name derived from the workspace's own name; the correct JSON is written via
      createWritable()/write()/close(); the call resolves true; the handle is remembered.
   ================================================================================================ */
function runNativeFreshHandleTests(next) {
  var handle = makeFakeHandle({});
  var picker = makeSavePicker({ handle: handle });
  var tab = makeTab({ rpsMode: "modern", showSaveFilePicker: picker });
  var VW = tab.window.VW;
  var id = VW.workspace.create("Shop Floor Torque Job", [{ page: "/torque", params: {} }], "manual");
  var expectedPayload = { name: "Shop Floor Torque Job", items: [{ page: "/torque", params: {} }], schemaVersion: VW.workspace._schemaVersion };

  check("sanity: no handle remembered yet for this id", VW.workspace._hasRememberedFileHandle(id) === false);

  VW.workspace.exportFileNative(id).then(function (result) {
    check("native fresh: resolves true", result === true);
    check("native fresh: showSaveFilePicker called exactly once", picker.calls.length === 1);
    check("native fresh: a suggested filename derived from the workspace's own name was passed",
      typeof picker.calls[0].suggestedName === "string" && picker.calls[0].suggestedName.indexOf("Shop-Floor-Torque-Job") === 0 &&
      picker.calls[0].suggestedName.slice(-5) === ".json");
    check("native fresh: a JSON type filter was passed",
      Array.isArray(picker.calls[0].types) && JSON.stringify(picker.calls[0].types).indexOf("application/json") !== -1);
    check("native fresh: exactly one write, matching _wsExportPayload()'s own shape exactly",
      handle._writes.length === 1 && handle._writes[0] === JSON.stringify(expectedPayload));
    check("native fresh: the writable stream was closed", handle._closedCount === 1);
    check("native fresh: the handle is now remembered for this id", VW.workspace._hasRememberedFileHandle(id) === true);
    next();
  }, function (e) {
    check("runNativeFreshHandleTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   3) WRITE-BACK-IN-PLACE: a second exportFileNative() call for the SAME id reuses the remembered
      handle WITHOUT calling showSaveFilePicker again (proven with a call-count spy).
   ================================================================================================ */
function runWriteBackInPlaceTests(next) {
  var handle = makeFakeHandle({});
  var picker = makeSavePicker({ handle: handle });
  var tab = makeTab({ rpsMode: "modern", showSaveFilePicker: picker });
  var VW = tab.window.VW;
  var id = VW.workspace.create("Reusable WS", [{ page: "/procedure", params: {} }], "manual");

  VW.workspace.exportFileNative(id).then(function (r1) {
    check("write-back: first call resolves true", r1 === true);
    check("write-back: first call used the picker (count=1)", picker.calls.length === 1);
    return VW.workspace.exportFileNative(id);
  }).then(function (r2) {
    check("write-back: second call for the SAME id resolves true", r2 === true);
    check("write-back: second call did NOT call showSaveFilePicker again (still count=1)", picker.calls.length === 1);
    check("write-back: the SAME handle received both writes", handle._writes.length === 2);
    check("write-back: the handle's own permission was re-checked before the second reuse (queryPermission called)",
      handle._queryCalls >= 1);
    next();
  }, function (e) {
    check("runWriteBackInPlaceTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   4) PERMISSION RE-VERIFICATION: a revoked/denied permission on a previously-granted handle is
      re-checked before reuse -- never assumed still-good. Confirms the stale handle is dropped and
      a FRESH showSaveFilePicker() call happens (never a silent failure, never a write to a handle
      that just failed its own permission check).
   ================================================================================================ */
function runRevokedPermissionTests(next) {
  var handle1 = makeFakeHandle({ queryState: "granted" });
  var handle2 = makeFakeHandle({ queryState: "granted" });
  var callNum = 0;
  function picker() {
    callNum++;
    picker.calls.push(arguments[0]);
    return Promise.resolve(callNum === 1 ? handle1 : handle2);
  }
  picker.calls = [];
  var tab = makeTab({ rpsMode: "modern", showSaveFilePicker: picker });
  var VW = tab.window.VW;
  var id = VW.workspace.create("Revocation WS", [{ page: "/torque", params: {} }], "manual");

  VW.workspace.exportFileNative(id).then(function (r1) {
    check("revocation: first call resolves true, handle1 obtained", r1 === true && handle1._writes.length === 1);
    // Simulate the grant being revoked between calls (the user or the browser withdrew it, and a
    // re-request still comes back denied -- e.g. the user explicitly denied the re-prompt).
    handle1._queryState = "denied";
    handle1._requestState = "denied";
    return VW.workspace.exportFileNative(id);
  }).then(function (r2) {
    check("revocation: second call still resolves true (fell back to a fresh picker, not a failure)", r2 === true);
    check("revocation: permission was genuinely re-checked on the stale handle before reuse",
      handle1._queryCalls >= 1);
    check("revocation: a FRESH showSaveFilePicker() call happened (count=2)", picker.calls.length === 2);
    check("revocation: the stale handle received NO further writes after being denied", handle1._writes.length === 1);
    check("revocation: the NEW handle received the write instead", handle2._writes.length === 1);
    check("revocation: the remembered handle for this id is now the NEW one",
      VW.workspace._hasRememberedFileHandle(id) === true);
    next();
  }, function (e) {
    check("runRevokedPermissionTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   5) CANCEL IS NOT AN ERROR, both directions: an AbortError from either native picker resolves
      (never rejects) to a clear non-error outcome. A DIFFERENT rejection still propagates as a
      real rejection in both directions, proving this isn't "nothing ever rejects".
   ================================================================================================ */
function runCancelTests(next) {
  // ---- export: cancel ----
  var tabA = makeTab({ rpsMode: "modern", showSaveFilePicker: makeSavePicker({ abort: true }) });
  var idA = tabA.window.VW.workspace.create("Cancel WS", [{ page: "/torque", params: {} }], "manual");
  tabA.window.VW.workspace.exportFileNative(idA).then(function (result) {
    check("cancel(export): a real AbortError resolves false, never rejects", result === false);
    check("cancel(export): no handle was remembered on a cancel",
      tabA.window.VW.workspace._hasRememberedFileHandle(idA) === false);

    // ---- export: a genuine (non-abort) failure still propagates as a real rejection ----
    var tabB = makeTab({ rpsMode: "modern", showSaveFilePicker: makeSavePicker({ error: new Error("disk full") }) });
    var idB = tabB.window.VW.workspace.create("Failure WS", [{ page: "/torque", params: {} }], "manual");
    return tabB.window.VW.workspace.exportFileNative(idB).then(
      function () { check("cancel(export): a genuine failure should have rejected, did not", false); },
      function (err) {
        check("cancel(export): a genuine (non-abort) failure still propagates as a real rejection",
          err instanceof Error && err.message === "disk full");
      }
    );
  }).then(function () {
    // ---- import: cancel ---- (fileSystemAccess itself is gated on showSaveFilePicker alone, per
    // PR 19's own untouched definition -- both native functions share that ONE flag, so a tab
    // exercising importFileNative() still needs a showSaveFilePicker stub present, even though
    // this sub-test never calls it, purely so the capability reads true in the first place.)
    var tabC = makeTab({ rpsMode: "modern", showSaveFilePicker: makeSavePicker({}), showOpenFilePicker: makeOpenPicker({ abort: true }) });
    return tabC.window.VW.workspace.importFileNative().then(function (result) {
      check("cancel(import): a real AbortError resolves null, never rejects", result === null);

      // ---- import: a genuine (non-abort) failure still propagates as a real rejection ----
      var tabD = makeTab({ rpsMode: "modern", showSaveFilePicker: makeSavePicker({}), showOpenFilePicker: makeOpenPicker({ error: new Error("device error") }) });
      return tabD.window.VW.workspace.importFileNative().then(
        function () { check("cancel(import): a genuine failure should have rejected, did not", false); },
        function (err) {
          check("cancel(import): a genuine (non-abort) failure still propagates as a real rejection",
            err instanceof Error && err.message === "device error");
        }
      );
    });
  }).then(next, function (e) {
    check("runCancelTests should not itself throw (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   6) importFileNative() ROUTES THROUGH THE EXISTING _wsImportFromJson(): a payload with a
      schemaVersion PR 22's own classifier genuinely refuses (newer than this build understands)
      produces the SAME "Workspace import failed: ..." specific-Error convention -- proof no
      second, independently-typed validation was written for the native path.
   ================================================================================================ */
function runSchemaRefusalRoutesThroughSharedValidationTests(next) {
  var futurePayload = { name: "From another shift", items: [{ page: "/torque", params: {} }], schemaVersion: 999 };
  var handle = makeFakeHandle({ fileText: JSON.stringify(futurePayload) });
  var tab = makeTab({
    rpsMode: "modern",
    showSaveFilePicker: makeSavePicker({}),   // present only so fileSystemAccess reads true; never called here
    showOpenFilePicker: makeOpenPicker({ handle: handle })
  });
  var VW = tab.window.VW;
  check("sanity: this build's schema classifier genuinely refuses schemaVersion 999",
    VW.workspace._classifySchemaVersion(futurePayload).ok === false);

  VW.workspace.importFileNative().then(
    function () { check("schema refusal: importFileNative should have rejected, did not", false); next(); },
    function (err) {
      check("schema refusal: rejects with a real Error", err instanceof Error);
      check("schema refusal: uses PR 3/PR 22's own specific-message convention",
        typeof err.message === "string" && err.message.indexOf("Workspace import failed:") === 0);
      check("schema refusal: names the SAME reason _wsClassifyRecordSchema() itself produces (not a " +
        "second, independently-typed comparison)",
        err.message.indexOf("newer than this app version understands") !== -1);
      next();
    }
  );
}

/* ================================================================================================
   7) IMPORT SUCCESS remembers the handle keyed by the NEWLY CREATED id -- proven by a subsequent
      exportFileNative() call for that id reusing it (showSaveFilePicker never called), completing
      the real open -> edit -> save-back loop the design doc describes.
   ================================================================================================ */
function runImportRemembersHandleTests(next) {
  var sharedPayload = { name: "Shared Team Workspace", items: [{ page: "/procedure", params: { id: "42" } }], schemaVersion: 1 };
  var openHandle = makeFakeHandle({ fileText: JSON.stringify(sharedPayload) });
  var savePicker = makeSavePicker({});   // should NEVER be called in this test
  var tab = makeTab({
    rpsMode: "modern",
    showOpenFilePicker: makeOpenPicker({ handle: openHandle }),
    showSaveFilePicker: savePicker
  });
  var VW = tab.window.VW;

  VW.workspace.importFileNative().then(function (id) {
    check("import: resolves to a real, truthy new id", typeof id === "string" && id.length > 0);
    var ws = VW.workspace.get(id);
    check("import: a genuine workspace record now exists via the EXISTING create() path",
      !!ws && ws.name === "Shared Team Workspace");
    check("import: the picked file's handle is remembered for the NEW id",
      VW.workspace._hasRememberedFileHandle(id) === true);

    return VW.workspace.exportFileNative(id).then(function (exportResult) {
      check("import->export loop: exportFileNative for the imported id resolves true", exportResult === true);
      check("import->export loop: showSaveFilePicker was NEVER called (the opened handle was reused)",
        savePicker.calls.length === 0);
      check("import->export loop: the write landed on the SAME handle importFileNative() opened",
        openHandle._writes.length === 1);
      var written = JSON.parse(openHandle._writes[0]);
      check("import->export loop: the write-back carries the SAME name/items round-tripped through create()",
        written.name === "Shared Team Workspace" &&
        JSON.stringify(written.items) === JSON.stringify(sharedPayload.items));
      next();
    });
  }, function (e) {
    check("runImportRemembersHandleTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   8) importFileNative() REJECTS CLEARLY when fileSystemAccess is false -- never silently no-ops.
   ================================================================================================ */
function runImportRejectsWhenCapabilityFalseTests(next) {
  var tab = makeTab({ rpsMode: "modern" });   // no showOpenFilePicker/showSaveFilePicker -> capability false
  check("sanity: fileSystemAccess is false on this tab", tab.window.VW.capabilities.fileSystemAccess === false);
  tab.window.VW.workspace.importFileNative().then(
    function () { check("capability-false: importFileNative() should have rejected, did not (silent no-op)", false); },
    function (err) {
      check("capability-false: rejects with a real, specific Error rather than silently no-opping",
        err instanceof Error && typeof err.message === "string" && err.message.length > 0);
    }
  ).then(next);
}

/* ================================================================================================
   9) Shape check: VW.channel / VW.workspace's original members / VW.windows / VW.capabilities are
      untouched by this PR.
   ================================================================================================ */
(function () {
  var tab = makeTab({ rpsMode: "modern" });
  var VW = tab.window.VW;
  check("VW.channel is untouched (publish/subscribe still present)",
    VW.channel && typeof VW.channel.publish === "function" && typeof VW.channel.subscribe === "function");
  check("VW.workspace's original 10 members are all still present",
    VW.workspace && typeof VW.workspace.create === "function" && typeof VW.workspace.list === "function" &&
    typeof VW.workspace.get === "function" && typeof VW.workspace.touch === "function" &&
    typeof VW.workspace.delete === "function" && typeof VW.workspace.exportUrl === "function" &&
    typeof VW.workspace.exportFile === "function" && typeof VW.workspace.importUrl === "function" &&
    typeof VW.workspace.importFile === "function" && typeof VW.workspace._schemaVersion === "number");
  check("VW.windows is untouched (open/registry/restoreLayout still present)",
    VW.windows && typeof VW.windows.open === "function" && typeof VW.windows.registry === "function");
  check("VW.capabilities is untouched (fileSystemAccess still present alongside the other 7 fields)",
    VW.capabilities && "fileSystemAccess" in VW.capabilities && "webLocks" in VW.capabilities &&
    "indexedDB" in VW.capabilities && "tier" in VW.capabilities);
})();

function finish() {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}

runFallbackTests(function () {
  runNativeFreshHandleTests(function () {
    runWriteBackInPlaceTests(function () {
      runRevokedPermissionTests(function () {
        runCancelTests(function () {
          runSchemaRefusalRoutesThroughSharedValidationTests(function () {
            runImportRemembersHandleTests(function () {
              runImportRejectsWhenCapabilityFalseTests(finish);
            });
          });
        });
      });
    });
  });
});

// END OF FILE
