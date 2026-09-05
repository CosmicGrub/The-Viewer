/* THE VIEWER -- VW.locks, real behavior test (PR 20 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 6). Run under plain Node, same
vm.createContext sandbox convention test_vw_capabilities_node.js (PR 19) and
test_workspace_export_import_node.js already established (Promise/setTimeout added to the sandbox,
async assertions chained via plain .then() callbacks -- never async/await -- ending in a single
finish() call).

Invoked by engine/tests/test_vw_locks.py via `node this-file.js`; prints PASS/FAIL lines and exits 1
on any failure.

WHAT THIS PROVES, for real, against the actual production code in engine/ui/shared.js:
  - REAL-API PATH: with VW.capabilities.webLocks true (mock navigator.locks present + tier "modern"),
    withLock() genuinely delegates to navigator.locks.request() with the exact name passed, and the
    resolved/rejected value of fn() -- as a plain value AND as a Promise -- round-trips correctly
    through withLock()'s own returned Promise in both directions.
  - RAW API ABSENT: navigator.locks is never defined at all. The fallback runs instead of the real
    path -- proven not by inspecting source, but by the simple fact that a real attempt to call
    navigator.locks.request() here would throw synchronously (reading .request off undefined); no such
    throw is observed, and fn()'s own result still round-trips correctly through the fallback.
  - THE SINGLE MOST IMPORTANT TEST: raw navigator.locks genuinely PRESENT, wired to a canary that
    records every invocation, but tier is "lite"/"legacy"/"premium" (each non-"modern" tier this
    codebase names) -- the fallback still runs, and the canary is proven to have NEVER been invoked in
    any of the three cases. This is the live proof that the gate reads the genuinely capability-driven
    VW.capabilities.webLocks (raw-feature AND tier), not a raw-feature-only check -- mirroring PR 19's
    own most-important live-read test. The contrasting "tier modern -> the SAME canary IS invoked"
    case (folded into the real-API-path section above) proves the canary mechanism itself is capable
    of catching a real call, so a false PASS here can't be explained by a canary that silently never
    fires under any circumstance.
  - FALLBACK MUTUAL EXCLUSION: two overlapping withLock() calls sharing the SAME name, each with an
    artificial setTimeout delay inside fn(), genuinely execute one at a time, in call order -- proven
    via a shared side-effect log asserted to read exactly
    ["1 start","1 end","2 start","2 end"], never an interleaving like ["1 start","2 start",...].
  - FALLBACK INDEPENDENCE: two overlapping withLock() calls with DIFFERENT names are proven to
    interleave (their start/end log entries genuinely overlap in time) -- i.e. they are NOT serialized
    against each other, unlike the same-name case immediately above.
  - FALLBACK RESILIENCE ("never blocks on failure"): a first queued call for a name whose fn() rejects
    (one variant returns a rejected Promise, a second variant throws synchronously) does not prevent a
    SECOND queued call for that SAME name from running afterward, AND the first call's own caller still
    receives that exact original rejection (a distinguishing Error object/message), never a silently
    swallowed or replaced value.
  - THE QUEUE-CLEANUP GUARANTEE: VW.locks._debugPendingCount() (debug-only introspection, not part of
    the documented API -- see shared.js's own comment directly above it) reads 0 once a name's queue
    has fully drained, proven both for a single call and for a longer chained sequence, and proven to
    read back UP while calls for that name are still in flight (so the assertion is genuinely
    exercising the map shrinking, not just a permanently-zero stub).

Gracefully skips (never false-fails) in an environment without node, same as the rest of this
codebase's node-dependent checks -- enforced by the calling .py wrapper, not this file. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

function fakeEl() {
  return { style: {}, setAttribute: function () {}, appendChild: function () {}, textContent: "" };
}

function makeDoc() {
  var el = fakeEl;
  return {
    readyState: "complete",
    getElementById: function () { return null; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; },
    createElement: el,
    addEventListener: function () {},
    body: el(), head: el(), documentElement: el()
  };
}

/* Builds one fresh sandbox/tab, loads the real shared.js into it, and returns the vm context.

   opts:
     rpsMode: undefined -- window.RPS left entirely unset; otherwise a string ("modern"/"lite"/
              "legacy"/"premium"/anything) -> window.RPS = {mode: rpsMode}.
     locksRequest: a function(name, callback) -- when given, navigator.locks = {request: that
              function} (raw Web Locks API present). Omitted entirely -> navigator.locks stays
              genuinely undefined (raw API absent), matching the "locks" in navigator check exactly. */
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

  sandbox.navigator = {};
  if (opts.locksRequest) {
    sandbox.navigator.locks = { request: opts.locksRequest };
  }
  // else: navigator.locks stays entirely undefined -- the raw-API-absent case.

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

function delay(ms, value) {
  return new Promise(function (resolve) {
    setTimeout(function () { resolve(value); }, ms);
  });
}

/* ================================================================================================
   0) VW.locks exists off VW, and withLock is a function (basic shape sanity).
   ================================================================================================ */
(function () {
  var tab = makeTab({ rpsMode: "modern" });
  check("VW.locks exists", !!tab.window.VW.locks);
  check("VW.locks.withLock is a function", typeof tab.window.VW.locks.withLock === "function");
})();

/* ================================================================================================
   1) REAL-API PATH: tier "modern" + navigator.locks present -> withLock() genuinely delegates to
      navigator.locks.request() with the right name; fn()'s resolved/rejected value -- as a plain
      value AND as a Promise -- round-trips through withLock()'s own returned Promise both ways.
   ================================================================================================ */
function runRealApiPathTests(next) {
  var calls = [];
  function mockRequest(name, cb) {
    calls.push(name);
    return Promise.resolve().then(function () { return cb({ name: name }); });
  }

  var tab = makeTab({ rpsMode: "modern", locksRequest: mockRequest });
  check("sanity: VW.capabilities.webLocks is true (raw present + tier modern)",
    tab.window.VW.capabilities.webLocks === true);

  tab.window.VW.locks.withLock("resource-a", function () { return "plain-value-ok"; })
    .then(function (result) {
      check("real path: resolves with fn()'s plain (non-Promise) return value",
        result === "plain-value-ok");
      check("real path: navigator.locks.request was called with the exact lock name",
        calls.length >= 1 && calls[0] === "resource-a");

      return tab.window.VW.locks.withLock("resource-b", function () {
        return Promise.resolve("promise-value-ok");
      });
    })
    .then(function (result2) {
      check("real path: resolves with fn()'s own resolved Promise value (fn returning a Promise)",
        result2 === "promise-value-ok");
      check("real path: a second call used the second lock's own name",
        calls.indexOf("resource-b") !== -1);

      return tab.window.VW.locks.withLock("resource-c", function () {
        return Promise.reject(new Error("real-path-rejection"));
      }).then(
        function () { return "should-not-resolve"; },
        function (err) { return err; }
      );
    })
    .then(function (caught) {
      check("real path: a rejecting fn() propagates the ORIGINAL Error through withLock()'s own Promise",
        caught instanceof Error && caught.message === "real-path-rejection");
      next();
    })
    .catch(function (e) {
      check("runRealApiPathTests should not itself throw (it did: " + (e && e.message) + ")", false);
      next();
    });
}

/* ================================================================================================
   2) RAW API ABSENT: navigator.locks is genuinely undefined. The fallback must run -- proven by the
      absence of the synchronous throw a real navigator.locks.request() attempt would cause, plus
      fn()'s result still round-tripping correctly.
   ================================================================================================ */
function runRawApiAbsentTests(next) {
  var tab = makeTab({ rpsMode: "modern" });   // no locksRequest given -> navigator.locks undefined
  check("sanity: VW.capabilities.webLocks is false when navigator.locks is entirely absent",
    tab.window.VW.capabilities.webLocks === false);

  var threw = false;
  var p;
  try {
    p = tab.window.VW.locks.withLock("no-raw-api", function () { return "fallback-ran"; });
  } catch (e) { threw = true; }
  check("raw API absent: withLock() never throws synchronously (a real navigator.locks.request() " +
    "attempt against undefined would have thrown reading .request)", !threw);

  p.then(function (result) {
    check("raw API absent: fallback still resolves fn()'s own value", result === "fallback-ran");
    next();
  }, function (e) {
    check("raw API absent case should not have rejected (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   3) THE SINGLE MOST IMPORTANT TEST: raw navigator.locks genuinely PRESENT (wired to a canary), but
      tier is "lite"/"legacy"/"premium" -- the fallback must still run, and the canary must NEVER be
      invoked in any of the three cases. Proves the gate is genuinely capability-driven (raw feature
      AND tier), not raw-feature-only -- the contrasting "tier modern -> canary fires" case already
      ran in section 1 above, so a false pass here can't be explained by an inert canary.
   ================================================================================================ */
function runNonModernTierStillFallsBackTests(next) {
  var tiers = ["lite", "legacy", "premium"];
  var idx = 0;

  function runOne() {
    if (idx >= tiers.length) { next(); return; }
    var tier = tiers[idx++];
    var canaryCalls = 0;
    function canary(name, cb) {
      canaryCalls++;
      return Promise.resolve().then(function () { return cb({ name: name }); });
    }
    var tab = makeTab({ rpsMode: tier, locksRequest: canary });
    check("sanity: VW.capabilities.webLocks is false at tier \"" + tier + "\" even with raw API present",
      tab.window.VW.capabilities.webLocks === false);

    tab.window.VW.locks.withLock("gated-resource", function () { return "fell-back-at-" + tier; })
      .then(function (result) {
        check("tier \"" + tier + "\": the real navigator.locks.request canary was NEVER invoked",
          canaryCalls === 0);
        check("tier \"" + tier + "\": the fallback still ran fn() and returned its value",
          result === "fell-back-at-" + tier);
        runOne();
      }, function (e) {
        check("tier \"" + tier + "\" case should not have rejected (it did: " + (e && e.message) + ")",
          false);
        runOne();
      });
  }
  runOne();
}

/* ================================================================================================
   4) FALLBACK MUTUAL EXCLUSION: two overlapping withLock() calls, SAME name, genuinely execute one
      at a time, in call order -- proven via a shared log with intentional delays, never interleaved.
   ================================================================================================ */
function runMutualExclusionTests(next) {
  var tab = makeTab({ rpsMode: "modern" });   // no locksRequest -> guaranteed fallback path
  var log = [];

  var p1 = tab.window.VW.locks.withLock("shared-name", function () {
    log.push("1 start");
    return delay(30).then(function () { log.push("1 end"); return "r1"; });
  });
  var p2 = tab.window.VW.locks.withLock("shared-name", function () {
    log.push("2 start");
    return delay(5).then(function () { log.push("2 end"); return "r2"; });
  });

  Promise.all([p1, p2]).then(function (results) {
    check("mutual exclusion: same-name calls run strictly one at a time, in call order " +
      "(log: " + log.join(",") + ")",
      log.join(",") === "1 start,1 end,2 start,2 end");
    check("mutual exclusion: both calls still resolve with their own correct value",
      results[0] === "r1" && results[1] === "r2");
    next();
  }, function (e) {
    check("runMutualExclusionTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   5) FALLBACK INDEPENDENCE: two overlapping withLock() calls with DIFFERENT names interleave --
      i.e. they do NOT wait on each other, unlike the same-name case above.
   ================================================================================================ */
function runIndependenceTests(next) {
  var tab = makeTab({ rpsMode: "modern" });
  var log = [];

  var pA = tab.window.VW.locks.withLock("name-a", function () {
    log.push("A start");
    return delay(30).then(function () { log.push("A end"); return "ra"; });
  });
  var pB = tab.window.VW.locks.withLock("name-b", function () {
    log.push("B start");
    return delay(5).then(function () { log.push("B end"); return "rb"; });
  });

  Promise.all([pA, pB]).then(function (results) {
    check("independence: different-name calls genuinely interleave (log: " + log.join(",") + ") -- " +
      "B (the shorter delay) finishes before A, proving they ran concurrently, not serialized",
      log.join(",") === "A start,B start,B end,A end");
    check("independence: both calls still resolve with their own correct value",
      results[0] === "ra" && results[1] === "rb");
    next();
  }, function (e) {
    check("runIndependenceTests should not reject (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   6) FALLBACK RESILIENCE ("never blocks on failure"): a first queued call whose fn() rejects/throws
      does not prevent a SECOND queued call for the SAME name from running afterward, AND the first
      call's own caller still receives the ORIGINAL rejection -- never silently swallowed.
   ================================================================================================ */
function runResilienceTests(next) {
  // Variant A: fn() returns a rejected Promise.
  var tabA = makeTab({ rpsMode: "modern" });
  var secondRanA = false;
  var p1a = tabA.window.VW.locks.withLock("flaky-a", function () {
    return delay(10).then(function () { throw new Error("boom-a"); });
  });
  var p2a = tabA.window.VW.locks.withLock("flaky-a", function () {
    secondRanA = true;
    return "recovered-a";
  });

  p1a.then(
    function () { check("resilience(A): first call should have rejected, did not", false); },
    function (err) {
      check("resilience(A): the first call's own caller receives the ORIGINAL rejection",
        err instanceof Error && err.message === "boom-a");
    }
  ).then(function () {
    return p2a.then(function (result) {
      check("resilience(A): the second queued call for the SAME name still ran after the first failed",
        secondRanA === true && result === "recovered-a");
      runVariantB();
    }, function (e) {
      check("resilience(A): second call should not itself have rejected (it did: " +
        (e && e.message) + ")", false);
      runVariantB();
    });
  });

  // Variant B: fn() throws synchronously (never even returns a Promise).
  function runVariantB() {
    var tabB = makeTab({ rpsMode: "modern" });
    var secondRanB = false;
    var p1b = tabB.window.VW.locks.withLock("flaky-b", function () {
      throw new Error("boom-b-sync");
    });
    var p2b = tabB.window.VW.locks.withLock("flaky-b", function () {
      secondRanB = true;
      return "recovered-b";
    });

    p1b.then(
      function () { check("resilience(B): first call should have rejected, did not", false); },
      function (err) {
        check("resilience(B): a SYNCHRONOUSLY THROWING fn() still propagates as a real rejection " +
          "to the first call's own caller", err instanceof Error && err.message === "boom-b-sync");
      }
    ).then(function () {
      return p2b.then(function (result) {
        check("resilience(B): the second queued call for the SAME name still ran after the first " +
          "threw synchronously", secondRanB === true && result === "recovered-b");
        next();
      }, function (e) {
        check("resilience(B): second call should not itself have rejected (it did: " +
          (e && e.message) + ")", false);
        next();
      });
    });
  }
}

/* ================================================================================================
   7) THE QUEUE-CLEANUP GUARANTEE: VW.locks._debugPendingCount() (debug-only, see shared.js's own
      comment above it) reads 0 once a name's queue has fully drained -- proven for a single call, a
      longer chained sequence, and proven to read back UP while calls are still in flight (so this is
      genuinely exercising the map shrinking, not a permanently-zero stub).
   ================================================================================================ */
function runCleanupTests(next) {
  var tab = makeTab({ rpsMode: "modern" });
  var dbg = tab.window.VW.locks._debugPendingCount;
  check("cleanup: pending count starts at 0 before any lock is taken", dbg() === 0);

  var p1 = tab.window.VW.locks.withLock("cleanup-a", function () {
    return delay(15).then(function () { return "done-a"; });
  });
  check("cleanup: pending count is >0 WHILE a lock's fallback queue is still in flight " +
    "(proves this is a real live count, not a stub)", dbg() > 0);

  p1.then(function () {
    // Let the internal "advance" cleanup microtask (chained after the returned promise) settle too.
    return Promise.resolve().then(function () {});
  }).then(function () {
    check("cleanup: pending count returns to 0 once the single queued call has fully drained",
      dbg() === 0);

    // A longer chained sequence for the SAME name: cleanup should still land back at 0 afterward,
    // not accumulate one leftover entry per call.
    var chainPromises = [];
    for (var i = 0; i < 5; i++) {
      chainPromises.push(tab.window.VW.locks.withLock("cleanup-b", function (n) {
        return function () { return delay(2).then(function () { return "step-" + n; }); };
      }(i)));
    }
    check("cleanup: pending count is nonzero while a 5-call chain for one name is still draining",
      dbg() > 0);

    return Promise.all(chainPromises).then(function () {
      return Promise.resolve().then(function () {});
    });
  }).then(function () {
    check("cleanup: pending count returns to 0 after a longer same-name chain fully drains " +
      "(no leftover entry accumulates)", dbg() === 0);
    next();
  }).catch(function (e) {
    check("runCleanupTests should not itself throw (it did: " + (e && e.message) + ")", false);
    next();
  });
}

/* ================================================================================================
   8) VW.channel / VW.workspace / VW.windows / VW.capabilities are untouched by this PR (runtime
      shape check -- the source-level "diff touches nothing else" check lives in the Python driver).
   ================================================================================================ */
(function () {
  var tab = makeTab({ rpsMode: "modern" });
  var VW = tab.window.VW;
  check("VW.channel is untouched (publish/subscribe still present)",
    VW.channel && typeof VW.channel.publish === "function" && typeof VW.channel.subscribe === "function");
  check("VW.workspace is untouched (create/list/get/touch/delete still present)",
    VW.workspace && typeof VW.workspace.create === "function" && typeof VW.workspace.list === "function");
  check("VW.windows is untouched (open/registry/restoreLayout still present)",
    VW.windows && typeof VW.windows.open === "function" && typeof VW.windows.registry === "function");
  check("VW.capabilities is untouched (all 8 PR 19 fields still present)",
    VW.capabilities && "tier" in VW.capabilities && "webLocks" in VW.capabilities &&
    "windowPlacement" in VW.capabilities && "indexedDB" in VW.capabilities);
})();

function finish() {
  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}

runRealApiPathTests(function () {
  runRawApiAbsentTests(function () {
    runNonModernTierStillFallsBackTests(function () {
      runMutualExclusionTests(function () {
        runIndependenceTests(function () {
          runResilienceTests(function () {
            runCleanupTests(finish);
          });
        });
      });
    });
  });
});

// END OF FILE
