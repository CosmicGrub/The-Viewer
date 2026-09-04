/* THE VIEWER -- VW.bench real accessor + live cross-tab notification test, run under plain Node.

Invoked by engine/tests/test_shared_bench.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure, matching the project's usual test-file convention.

Why this is a real test rather than a reimplementation of the logic under test:

  * Every assertion goes through the actual exported VW.bench functions loaded from the real
    engine/ui/shared.js. Nothing here reimplements the storage key, the 100-entry cap, the corrupt-
    value handling or the notification payload -- where a check needs to know what was really
    persisted it reads the raw localStorage key directly (store.data["viewer_bench"]) and parses it,
    rather than trusting the API's own return value to describe itself.

  * Two vm.createContext() sandboxes stand in for two browser tabs, exactly as
    test_channel_node.js and test_workspace_node.js do -- and, as in the latter, they deliberately
    SHARE one localStorage object, because that is precisely what two tabs on one origin have. That
    makes feature D's central claim testable for real: a bench written in tab A is genuinely
    readable through tab B's own VW.bench.get(), with the VW.channel message serving only as the
    "something changed, repaint" hint. Both sandboxes are also handed Node's real global
    BroadcastChannel, so the notification really does cross contexts through a production
    implementation.

  * The sandbox's Date is a controllable clock (shared.js only ever calls Date.now()), so the
    notification's `at` field is asserted as an exact value rather than merely "a number".

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

var BENCH_KEY = "viewer_bench";
var CHANNEL_KEY = "viewer_channel_msg";
var CAP = 100;                      // shared.js's own _BENCH_MAX, carried over from bench.html

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

/* opts: {store, clock, bc (default true)} */
function makeTab(opts) {
  opts = opts || {};
  var storageListeners = [];
  var clock = opts.clock || makeClock(1756800000000);
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Object: Object, Array: Array,
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
  sandbox.window.location = { pathname: "/bench", href: "" };
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
  var raw = store.data[BENCH_KEY];
  if (raw === undefined) return undefined;
  return JSON.parse(raw);
}

/* A realistic pinned row, exactly the shape palette.js's pinCurrent() writes. */
function pin(n) {
  return { url: "/dossier?q=part" + n, title: "Part " + n, q: "part" + n, ts: 1756800000000 + n };
}

/* ---- two tabs, one shared origin storage, real BroadcastChannel between them ---- */
var store = makeStore();
var clock = makeClock(1756800000000);
var tabA = makeTab({ store: store, clock: clock });
var tabB = makeTab({ store: store, clock: clock });

check("two tabs are genuinely independent contexts", tabA !== tabB);
check("VW.bench present in both tabs",
  !!(tabA.VW && tabA.VW.bench) && !!(tabB.VW && tabB.VW.bench));
check("VW.bench exposes exactly get and put",
  typeof tabA.VW.bench.get === "function" && typeof tabA.VW.bench.put === "function" &&
  Object.keys(tabA.VW.bench).sort().join(",") === "get,put");
check("promoting VW.bench did not disturb the existing VW exports",
  !!tabA.VW.channel && !!tabA.VW.workspace && !!tabA.VW.windows &&
  typeof tabA.VW.esc === "function" && typeof tabA.VW.toast === "function");
check("two tabs really share one localStorage", tabA.window.localStorage === tabB.window.localStorage);

/* every notification either tab publishes, captured from the other side */
var notesInB = [];
tabB.VW.channel.subscribe("bench", function (data, meta) {
  notesInB.push({ data: data, meta: meta });
});

/* ---- empty state ---- */
check("get() on empty storage returns an array",
  Object.prototype.toString.call(tabA.VW.bench.get()) === "[object Array]");
check("get() on empty storage returns an EMPTY array", tabA.VW.bench.get().length === 0);
check("a get() on empty storage wrote nothing", stored(store) === undefined);

/* ---- the basic round trip, and the stored shape ---- */
var three = [pin(1), pin(2), pin(3)];
var putOk = tabA.VW.bench.put(three);
check("put() returns true when the list was really stored", putOk === true);

var rawAll = stored(store);
check("put() really persisted a JSON array under viewer_bench",
  Object.prototype.toString.call(rawAll) === "[object Array]" && rawAll.length === 3);
check("the stored data shape is unchanged -- entries are stored verbatim",
  JSON.stringify(rawAll) === JSON.stringify(three));
check("a stored row keeps every field palette.js writes",
  rawAll[0].url === "/dossier?q=part1" && rawAll[0].title === "Part 1" &&
  rawAll[0].q === "part1" && rawAll[0].ts === 1756800000001);
check("get() reads back exactly what put() stored",
  JSON.stringify(tabA.VW.bench.get()) === JSON.stringify(three));
check("order is preserved (newest-first is the caller's business, not this accessor's)",
  tabA.VW.bench.get()[0].title === "Part 1" && tabA.VW.bench.get()[2].title === "Part 3");

/* returned lists are fresh parses -- a caller cannot corrupt storage by mutating one */
var mutable = tabA.VW.bench.get();
mutable.length = 0;
mutable.push({ url: "/CLOBBERED" });
check("mutating a returned list does not corrupt storage",
  tabA.VW.bench.get().length === 3 && tabA.VW.bench.get()[0].url === "/dossier?q=part1");

/* ---- the 100-entry cap, carried over unchanged from bench.html's own put() ---- */
var many = [];
for (var i = 1; i <= 150; i++) many.push(pin(i));
check("put() of 150 entries returns true", tabA.VW.bench.put(many) === true);
check("exactly " + CAP + " entries are really stored", stored(store).length === CAP);
check("the cap keeps the HEAD of the list (newest pins are unshifted to the front)",
  stored(store)[0].title === "Part 1" && stored(store)[CAP - 1].title === "Part " + CAP);
check("the oldest entries past the cap are the ones dropped",
  JSON.stringify(stored(store)).indexOf('"Part 101"') === -1);
check("get() after a capped write returns the capped list", tabA.VW.bench.get().length === CAP);

var exact = [];
for (var j = 1; j <= CAP; j++) exact.push(pin(j));
check("a list of exactly " + CAP + " is stored whole, nothing dropped",
  tabA.VW.bench.put(exact) === true && stored(store).length === CAP);
check("put([]) stores an empty bench and reports success",
  tabA.VW.bench.put([]) === true && stored(store).length === 0 && tabA.VW.bench.get().length === 0);

/* ---- a non-array argument writes nothing, exactly like the old page-local put() ---- */
tabA.VW.bench.put([pin(7)]);
var beforeBadPut = store.data[BENCH_KEY];
check("put(an object) returns false", tabA.VW.bench.put({ url: "/x" }) === false);
check("put(null) returns false", tabA.VW.bench.put(null) === false);
check("put(undefined) returns false", tabA.VW.bench.put(undefined) === false);
check("put(a string) returns false", tabA.VW.bench.put("not a list") === false);
check("put(a number) returns false", tabA.VW.bench.put(7) === false);
check("a rejected put() wrote nothing at all", store.data[BENCH_KEY] === beforeBadPut);
check("the real bench survived every rejected put()", tabA.VW.bench.get().length === 1);

/* ---- corrupt / hand-edited / hostile stored values ---- */
function corruptCheck(label, value, expectLen) {
  var s = makeStore();
  s.data[BENCH_KEY] = value;
  var t = makeTab({ store: s });
  var threw = false, len = -1;
  try { len = t.VW.bench.get().length; } catch (e) { threw = true; }
  check("corrupt storage (" + label + "): get() never throws", !threw);
  check("corrupt storage (" + label + "): get() returns " + expectLen, len === expectLen);
  return { store: s, tab: t };
}
corruptCheck("not JSON at all", "{definitely not json", 0);
corruptCheck("a JSON object, not an array", '{"url":"/x"}', 0);
corruptCheck("a JSON string", '"hello"', 0);
corruptCheck("JSON null", "null", 0);
corruptCheck("a JSON number", "42", 0);
corruptCheck("an empty string", "", 0);
/* Array-LIKE, not an array: the one corrupt shape that the per-entry object filter alone would let
   through, so this is what makes get()'s explicit "[object Array]" guard load-bearing rather than
   decorative. Confirmed by mutation: removing that guard is caught by this check and no other. */
corruptCheck("an array-like JSON object", '{"0":{"url":"/x"},"length":1}', 0);
var partial = corruptCheck("an array with junk entries mixed in",
  '[null,3,"x",{"url":"/dossier?q=real","title":"Real"}]', 1);
check("corrupt storage: the one usable row survives and is readable",
  (partial.tab.VW.bench.get()[0] || {}).url === "/dossier?q=real");
check("corrupt storage: a read did NOT rewrite the stored value",
  partial.store.data[BENCH_KEY].indexOf("null,3") !== -1);
partial.tab.VW.bench.put(partial.tab.VW.bench.get());
check("corrupt storage: the next put() clears the junk entries for good",
  stored(partial.store).length === 1 && stored(partial.store)[0].title === "Real");

/* ---- storage refusing to cooperate ---- */
var blindTab = makeTab({ store: makeStore({ throwOnRead: true }) });
var blindThrew = false, blindLen = -1;
try { blindLen = blindTab.VW.bench.get().length; } catch (e) { blindThrew = true; }
check("get() never throws when storage cannot even be read", !blindThrew);
check("get() returns an empty array when storage cannot be read", blindLen === 0);

var roStore = makeStore({ throwOnWrite: true });
var roTab = makeTab({ store: roStore });
var roThrew = false, roResult;
try { roResult = roTab.VW.bench.put([pin(1)]); } catch (e) { roThrew = true; }
check("put() never throws when storage refuses the write", !roThrew);
check("put() returns false when the write did not happen", roResult === false);
check("a refused write really stored nothing", roStore.data[BENCH_KEY] === undefined);

/* ---- cross-tab: shared storage alone already carries the data ---- */
var live = [pin(11), pin(12)];
tabA.VW.bench.put(live);
check("tab B sees tab A's bench through shared storage alone",
  JSON.stringify(tabB.VW.bench.get()) === JSON.stringify(live));

/* ---- last-write-wins, no merge (the design spec's explicit conflict rule) ---- */
tabA.VW.bench.put([pin(20), pin(21)]);
tabB.VW.bench.put([pin(30)]);
check("last-write-wins: the second tab's whole list is what is stored",
  stored(store).length === 1 && stored(store)[0].title === "Part 30");
check("last-write-wins: nothing from the losing write was merged in",
  JSON.stringify(stored(store)).indexOf("Part 20") === -1 &&
  JSON.stringify(stored(store)).indexOf("Part 21") === -1);
check("the losing tab now reads the winning list, not its own stale one",
  tabA.VW.bench.get().length === 1 && tabA.VW.bench.get()[0].title === "Part 30");

/* ---- the notification itself ---- */
/* a subscriber on a DIFFERENT channel must not be woken by a bench write */
var wsNotes = [];
tabB.VW.channel.subscribe("workspace", function (d) { wsNotes.push(d); });
/* The publishing tab's own subscriber must not be echoed to -- that is what keeps a tab from
   repainting twice for its own edit (once from its call site, once from its own notification).
   selfNotes cannot simply be asserted empty: tab B's earlier writes above were published before this
   subscription existed, but BroadcastChannel delivery is a macrotask, so those genuinely arrive here
   afterwards. So the write below is 5 entries long -- a count no other write in this test produces --
   and the assertion is that THAT payload specifically never comes back to its own publisher, while
   tab B does receive it. */
var selfNotes = [];
tabA.VW.channel.subscribe("bench", function (d) { selfNotes.push(d); });

clock.advance(9000);
tabA.VW.bench.put([pin(41), pin(42), pin(43), pin(44), pin(45)]);

/* A refused write must publish nothing. This tab's storage throws on every write, but its
   BroadcastChannel is the same global one tabB is listening on, so if put() published before
   checking the write, tabB would see it. The list is 7 long purely so its count is unique across
   every other write this test makes -- that is what makes its ABSENCE provable rather than assumed. */
var refusedTab = makeTab({ store: makeStore({ throwOnWrite: true }), clock: clock });
refusedTab.VW.bench.put([pin(90), pin(91), pin(92), pin(93), pin(94), pin(95), pin(96)]);
tabA.VW.bench.put("still not a list");

/* BroadcastChannel delivery is asynchronous; everything below waits for it, exactly as
   test_channel_node.js and test_workspace_node.js do. */
setTimeout(function () {
  var puts = [];
  for (var k = 0; k < notesInB.length; k++) {
    if (notesInB[k].data && notesInB[k].data.action === "put") puts.push(notesInB[k]);
  }
  check("every notification tab B received is a put notification", puts.length === notesInB.length);
  check("tab B was notified of tab A's writes", puts.length >= 1);

  /* Defaulted rather than indexed blind: when a mutation stops put() publishing at all, every
     assertion below should report a clean FAIL instead of the whole run dying on a TypeError and
     taking the remaining sections with it. (Found by deliberately breaking shared.js -- the first
     draft of this file crashed there.) */
  var last = puts.length ? puts[puts.length - 1] : { data: {}, meta: {} };
  check("the notification names the action", last.data.action === "put");
  check("the notification carries ONLY {action, at, count}",
    Object.keys(last.data).sort().join(",") === "action,at,count");
  check("the notification's count matches the list that was really stored", last.data.count === 5);
  check("at uses the real clock", last.data.at === 1756800009000);
  check("notifications arrive with the channel's own seq metadata",
    typeof last.meta.seq === "number" && last.meta.gap === false);

  var selfEcho = 0;
  for (var s = 0; s < selfNotes.length; s++) {
    if (selfNotes[s] && selfNotes[s].count === 5) selfEcho++;
  }
  check("the other tab really did receive that write", last.data.count === 5);
  check("the publishing tab is never echoed its own notification", selfEcho === 0);
  check("a bench write does not wake a subscriber on another channel", wsNotes.length === 0);
  check("a write storage refused published nothing (its unique count never appears)",
    JSON.stringify(puts).indexOf('"count":7') === -1);

  /* read-only calls publish nothing: nothing but get() between these two settle points */
  var notesBeforeReads = notesInB.length;
  tabA.VW.bench.get();
  tabA.VW.bench.get();
  tabB.VW.bench.get();

  setTimeout(function () {
    check("read-only get() calls publish nothing at all", notesInB.length === notesBeforeReads);

    /* the count really is the CAPPED count, proven against a 150-entry write */
    var capNotes = [];
    tabB.VW.channel.subscribe("bench", function (d) { capNotes.push(d); });
    tabA.VW.bench.put(many);

    setTimeout(function () {
      check("a capped write notifies the capped count, not the input length",
        capNotes.length === 1 && capNotes[0].count === CAP);

      /* the whole point of the notification: the receiving tab repaints from ITS OWN read, and
         really does find what the other tab wrote. */
      check("a notified tab reads the other tab's real bench from its own get()",
        tabB.VW.bench.get().length === CAP && tabB.VW.bench.get()[0].title === "Part 1");

      /* one more rejected put, settled below rather than checked on the same tick -- a publish
         would not have been delivered yet at this point, so checking here would pass vacuously */
      var beforeReject = capNotes.length;
      tabA.VW.bench.put({ nope: true });

      setTimeout(function () {
        check("a rejected put() publishes nothing", capNotes.length === beforeReject);

        /* ---- the same notification over the storage-event fallback transport ---- */
        var fbStore = makeStore();
        var fbA = makeTab({ store: fbStore, bc: false });
        var fbB = makeTab({ store: fbStore, bc: false });
        check("fallback: BroadcastChannel genuinely hidden from both tabs",
          typeof fbA.BroadcastChannel === "undefined" && typeof fbB.BroadcastChannel === "undefined");

        var fbNotes = [];
        fbB.VW.channel.subscribe("bench", function (data) { fbNotes.push(data); });
        var fbList = [pin(51), pin(52)];
        check("fallback: put() still really stored the bench",
          fbA.VW.bench.put(fbList) === true && stored(fbStore).length === 2);

        var envJson = fbStore.data[CHANNEL_KEY];
        check("fallback: the notification was really written to the channel key",
          typeof envJson === "string" && envJson.indexOf("bench") !== -1);
        for (var m = 0; m < fbB.__storageListeners.length; m++) {
          fbB.__storageListeners[m]({ key: CHANNEL_KEY, newValue: envJson });
        }
        check("fallback: the other tab received the bench notification",
          fbNotes.length === 1 && fbNotes[0].action === "put" && fbNotes[0].count === 2);
        check("fallback: that tab then reads the real bench from shared storage",
          JSON.stringify(fbB.VW.bench.get()) === JSON.stringify(fbList));

        console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
        process.exit(failures.length === 0 ? 0 : 1);
      }, 40);
    }, 40);
  }, 60);
}, 80);
