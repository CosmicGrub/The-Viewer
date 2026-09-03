/* THE VIEWER -- VW.channel real cross-tab logic test, run under plain Node (not a browser).

Invoked by engine/tests/test_shared_channel.py via `node this-file.js`; prints PASS/FAIL lines and
exits 1 on any failure, matching the project's usual test-file convention.

Why this is a genuinely real test, not a reimplementation of the logic under test: two independent
vm.createContext() sandboxes stand in for two separate browser tabs -- each gets its own window/
document/localStorage, so requiring shared.js into each gives fully independent closure state
(_channelTabId, _channelSeq, _channelLastSeen, _channelSubs), exactly like two real tabs share
nothing but the browser's BroadcastChannel registry. Both sandboxes are handed the SAME
BroadcastChannel constructor reference (Node has a real global BroadcastChannel implementation),
so a channel opened in one sandbox and a same-named channel opened in the other really do talk to
each other through Node's own implementation -- this is production code exercising a production
BroadcastChannel, not a mock standing in for one.

The one thing Node can't do is fire a real `storage` event across two contexts (that IPC lives in
the browser/OS, not in V8) -- so the storage-event fallback path is tested by capturing whatever
listener shared.js itself registers via window.addEventListener("storage", ...) and invoking it
directly with the same envelope shape a real storage event would carry. Everything the listener
actually does with that envelope (parse, version-check, gap-detect, dispatch to subscribers) is the
real code, unmocked -- only the OS-level delivery mechanism is stood in for. */
var vm = require("vm");
var fs = require("fs");
var path = require("path");

var SHARED = path.join(__dirname, "..", "..", "ui", "shared.js");
var src = fs.readFileSync(SHARED, "utf8");

function fakeEl() {
  return { style: {}, setAttribute: function () {}, appendChild: function () {}, textContent: "" };
}

/* withBC=false hides BroadcastChannel entirely, forcing shared.js's own feature-detection down the
   storage-event fallback path -- the same branch a real RPS/legacy browser without BroadcastChannel
   would take. */
function makeTab(withBC) {
  var storageListeners = [];
  var sandbox = {
    console: console, Math: Math, JSON: JSON, Date: Date, Object: Object, Array: Array,
    String: String, Error: Error, setTimeout: setTimeout, clearTimeout: clearTimeout,
    module: {}, exports: {}
  };
  if (withBC) sandbox.BroadcastChannel = BroadcastChannel;
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
  sandbox.window.localStorage = (function () {
    var store = {};
    return {
      getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
      setItem: function (k, v) { store[k] = String(v); }
    };
  })();
  var ctx = vm.createContext(sandbox);
  vm.runInContext(src, ctx, { filename: "shared.js" });
  ctx.__storageListeners = storageListeners;
  return ctx;
}

var failures = [];
var total = 0;
function check(name, cond) {
  total++;
  if (!cond) failures.push(name);
  console.log((cond ? "PASS " : "FAIL ") + name);
}

/* ---- BroadcastChannel path: real cross-tab delivery, in order, no self-echo ---- */
var tabA = makeTab(true);
var tabB = makeTab(true);
check("two tabs are genuinely independent contexts", tabA !== tabB);
check("VW present in both", !!tabA.VW && !!tabB.VW);

var received = [];
tabB.VW.channel.subscribe("probe", function (data, meta) { received.push({ data: data, meta: meta }); });
tabA.VW.channel.publish("probe", { n: 1 });
tabA.VW.channel.publish("probe", { n: 2 });

var selfFired = false;
tabA.VW.channel.subscribe("self-check", function () { selfFired = true; });
tabA.VW.channel.publish("self-check", { x: 1 });

setTimeout(function () {
  check("BroadcastChannel: both messages delivered", received.length === 2);
  if (received.length === 2) {
    check("BroadcastChannel: payloads correct and in order", received[0].data.n === 1 && received[1].data.n === 2);
    check("BroadcastChannel: seq correct and in order", received[0].meta.seq === 1 && received[1].meta.seq === 2);
    check("BroadcastChannel: no false gap flagged", !received[0].meta.gap && !received[1].meta.gap);
  }
  check("BroadcastChannel: never echoes back to its own publisher", !selfFired);

  /* ---- storage-event fallback path ---- */
  var fbA = makeTab(false);
  var fbB = makeTab(false);
  check("fallback: BroadcastChannel genuinely hidden", typeof fbA.BroadcastChannel === "undefined");

  var fbReceived = [];
  fbB.VW.channel.subscribe("fb-probe", function (data, meta) { fbReceived.push({ data: data, meta: meta }); });

  fbA.VW.channel.publish("fb-probe", { n: 1 });
  var envJson1 = fbA.window.localStorage.getItem("viewer_channel_msg");
  for (var i = 0; i < fbB.__storageListeners.length; i++) {
    fbB.__storageListeners[i]({ key: "viewer_channel_msg", newValue: envJson1 });
  }
  check("fallback: message delivered via the storage-event path", fbReceived.length === 1 && fbReceived[0].data.n === 1);
  check("fallback: seq=1, no gap on the first message", fbReceived.length === 1 && fbReceived[0].meta.seq === 1 && fbReceived[0].meta.gap === false);

  /* two rapid writes to the same key, only the LATEST ever delivered to fbB -- simulates the real
     browser coalescing behavior a storage event's newValue is subject to. */
  fbA.VW.channel.publish("fb-probe", { n: 2 });
  fbA.VW.channel.publish("fb-probe", { n: 3 });
  var envJson3 = fbA.window.localStorage.getItem("viewer_channel_msg");
  for (var j = 0; j < fbB.__storageListeners.length; j++) {
    fbB.__storageListeners[j]({ key: "viewer_channel_msg", newValue: envJson3 });
  }
  check("fallback: gap correctly flagged when a message was skipped",
    fbReceived.length === 2 && fbReceived[1].meta.seq === 3 && fbReceived[1].meta.gap === true);

  /* version mismatch: silently ignored, never delivered, never throws */
  var verReceived = [];
  fbB.VW.channel.subscribe("ver-probe", function (data) { verReceived.push(data); });
  var badEnvelope = JSON.stringify({ v: 999, name: "ver-probe", tabId: "fake", seq: 1, data: { x: 1 } });
  var threwOnBadVersion = false;
  try {
    for (var k = 0; k < fbB.__storageListeners.length; k++) {
      fbB.__storageListeners[k]({ key: "viewer_channel_msg", newValue: badEnvelope });
    }
  } catch (e) { threwOnBadVersion = true; }
  check("version mismatch: never throws", !threwOnBadVersion);
  check("version mismatch: message silently not delivered", verReceived.length === 0);

  /* oversized payload: throws a clear, immediate error on the fallback path, before ever writing */
  var big = { blob: new Array(210000).join("x") };
  var threwOnOversize = false, threwMessage = "";
  try { fbA.VW.channel.publish("fb-probe", big); }
  catch (e) { threwOnOversize = true; threwMessage = e.message || String(e); }
  check("oversized payload: publish() throws", threwOnOversize);
  check("oversized payload: error message is descriptive", /too large/i.test(threwMessage));

  /* malformed JSON in a storage event: never crashes the listener */
  var malformedThrew = false;
  try {
    for (var m = 0; m < fbB.__storageListeners.length; m++) {
      fbB.__storageListeners[m]({ key: "viewer_channel_msg", newValue: "{not valid json" });
    }
  } catch (e) { malformedThrew = true; }
  check("malformed storage payload: never throws", !malformedThrew);

  console.log("\n" + (total - failures.length) + " passed, " + failures.length + " failed");
  process.exit(failures.length === 0 ? 0 : 1);
}, 80);
