/* THE VIEWER — circuitsim-worker.js : runs the MNA solve OFF the main thread.
   Loads the same circuitsim.js engine, owns the Circuit instance, and posts back a compact snapshot
   (node voltages + element currents + relay states) after each command. The page renders from the
   snapshot, so a complex circuit can't stutter the UI. Falls back to inline sim if Workers are absent. */
/* eslint-disable no-undef */
try { importScripts("/circuitsim.js"); } catch (e) {}

var ckt = null;

function snapshot(tag) {
  if (!ckt) { self.postMessage({ cmd: tag, v: {}, i: {}, st: {}, t: 0 }); return; }
  var v = {}, ci = {}, st = {}, k, j, el;
  for (k = 0; k <= ckt.N; k++) v[k] = ckt.v(k);
  for (j = 0; j < ckt.el.length; j++) {
    el = ckt.el[j];
    ci[el.name] = ckt.i(el.name);
    if (el.type === "RELAY") st[el.name] = { closed: !!el._closed };
  }
  self.postMessage({ cmd: tag, t: ckt.t, v: v, i: ci, st: st });
}

self.onmessage = function (e) {
  var m = e.data || {};
  try {
    if (m.cmd === "init") {
      ckt = (self.CircuitSim && m.elements) ? new self.CircuitSim.Circuit(m.elements) : null;
      snapshot("init");
    } else if (m.cmd === "dc") {
      if (ckt) ckt.dc();
      snapshot("dc");
    } else if (m.cmd === "step") {
      if (ckt) {
        var steps = m.steps || 1, dt = m.dt || 1e-4, i;
        for (i = 0; i < steps; i++) ckt.step(dt);
      }
      snapshot("step");
    } else if (m.cmd === "tune") {           // change a value live (name -> {value|freq|closed})
      if (ckt && m.name) {
        var t = ckt.el.find(function (x) { return x.name === m.name; });
        if (t) { if (m.value !== undefined) t.value = m.value; if (m.freq !== undefined) t.freq = m.freq; if (m.closed !== undefined) t.closed = m.closed; }
      }
    }
  } catch (err) {
    self.postMessage({ cmd: "error", error: String(err) });
  }
};
