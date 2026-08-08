"""handover.py -- SHIFT-HANDOVER digest (roadmap Vol.2 #83). At the end of a shift the next crew needs a
single, honest picture: what's awaiting sign-off, what field notes were added, what cross-manual conflicts
are unresolved, and what services are coming due. This composes those into one digest -- so nothing falls
through the crack between shifts.

build_digest() is pure and unit-testable; the route feeds it from signoff / fieldnotes / conflicts / the
readiness data. Read-only."""

from __future__ import annotations
import time


def build_digest(pending_reviews=None, recent_notes=None, open_conflicts=None, due_services=None, since_hours=24):
    """Compose the handover digest. All inputs are lists of plain dicts (best-effort; any may be empty):
      pending_reviews : signoff queue items {kind,key,value,by,ts}
      recent_notes    : field notes {subject,text,by,ts}
      open_conflicts  : cross-manual conflicts {type,unit,severity,values}
      due_services    : {subject, value, unit, basis}
    -> a structured digest + a plain-text summary + a priority flag."""
    now = int(time.time())
    cutoff = now - since_hours * 3600

    def recent(items, key="ts"):
        return [i for i in (items or []) if (i.get(key) or now) >= cutoff]

    reviews = list(pending_reviews or [])
    notes = recent(recent_notes)
    conflicts = list(open_conflicts or [])
    high_conflicts = [c for c in conflicts if c.get("severity") == "high"]
    services = list(due_services or [])

    # priority: any high-severity safety conflict or pending safety value = red
    safety_kinds = {"torque", "pressure"}
    red = bool(high_conflicts) or any((r.get("kind") in safety_kinds) for r in reviews)
    priority = "red" if red else ("amber" if (reviews or conflicts) else "green")

    lines = []
    if reviews:
        lines.append("%d value(s) awaiting SME sign-off%s" %
                     (len(reviews), " (incl. safety-critical)" if any(r.get("kind") in safety_kinds for r in reviews) else ""))
    if high_conflicts:
        lines.append("%d UNRESOLVED cross-manual conflict(s) — verify before working" % len(high_conflicts))
    elif conflicts:
        lines.append("%d cross-manual discrepancy(ies) noted" % len(conflicts))
    if notes:
        lines.append("%d new field note(s) in the last %dh" % (len(notes), since_hours))
    if services:
        lines.append("%d service(s) coming due" % len(services))
    if not lines:
        lines.append("Nothing open — clean handover.")

    return {
        "generated": time.strftime("%Y-%m-%d %H:%M", time.localtime(now)),
        "priority": priority,
        "counts": {"pending_reviews": len(reviews), "recent_notes": len(notes),
                   "open_conflicts": len(conflicts), "high_conflicts": len(high_conflicts),
                   "due_services": len(services)},
        "pending_reviews": reviews[:20], "recent_notes": notes[:20],
        "open_conflicts": conflicts[:20], "due_services": services[:20],
        "summary": lines,
    }


# --------------------------------------------------------------------------- #
# self-test: `python handover.py`                                             #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    now = int(time.time())
    d = build_digest(
        pending_reviews=[{"kind": "torque", "key": "HMMWV mount bolt", "value": "35 ft-lb", "by": "ocr", "ts": now}],
        recent_notes=[{"subject": "half-shaft", "text": "anti-seize the bolt", "by": "SSG Lee", "ts": now},
                      {"subject": "old", "text": "stale", "by": "x", "ts": now - 999999}],   # too old -> dropped
        open_conflicts=[{"type": "torque", "unit": "ft-lb", "severity": "high", "values": [35, 50]}],
        due_services=[{"subject": "engine oil", "value": 3000, "unit": "miles", "basis": "usage"}],
    )
    assert d["priority"] == "red", d["priority"]                        # high conflict + safety review
    assert d["counts"]["pending_reviews"] == 1, d["counts"]
    assert d["counts"]["recent_notes"] == 1, d["counts"]               # stale one dropped
    assert d["counts"]["high_conflicts"] == 1, d["counts"]
    assert d["counts"]["due_services"] == 1, d["counts"]
    assert any("sign-off" in s for s in d["summary"]), d["summary"]
    print("build_digest OK -> priority=%s, %s" % (d["priority"], d["counts"]))
    for s in d["summary"]:
        print("   -", s)

    clean = build_digest()
    assert clean["priority"] == "green" and clean["summary"] == ["Nothing open — clean handover."], clean
    print("clean handover OK")
    print("handover self-test PASS")

# END OF FILE
