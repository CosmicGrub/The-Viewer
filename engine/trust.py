"""trust.py -- ONE canonical trust level for any displayed value (R13). Every number in the app should tell
the mechanic how much to trust it, computed the same way everywhere: from its SOURCE (authoritative manual
vs external), its CONFIDENCE (agreement / sample count), and its VALIDATION status (validate.py). This
module is the single source of that judgement so the chips mean the same thing on every page.

    quarantined -- failed integrity validation; must NOT be shown as fact
    low         -- external / unconfirmed
    review      -- suspect value, or sources disagree, or a lone corpus cite worth a second look
    medium      -- authoritative, single cite
    high        -- authoritative and corroborated (>=2 agreeing) and validation-clean

Pure and unit-testable. UI reads .badge() for a consistent chip (level + color + tooltip)."""

from __future__ import annotations

_ORDER = ["quarantined", "low", "review", "medium", "high"]
_COLOR = {"high": "#7fd6a0", "medium": "#7fb8d6", "review": "#e8c07a", "low": "#c9a06a", "quarantined": "#e39b95"}
_LABEL = {"high": "verified", "medium": "cited", "review": "check", "low": "unconfirmed", "quarantined": "held"}


def level(source=None, confidence=None, validation_status=None, n_samples=None, spread=None, authoritative=None):
    """Fold the available signals into one level. Any argument may be None/absent; the worst applicable
    signal wins (a quarantine or a wide disagreement always dominates)."""
    if validation_status == "quarantine":
        return "quarantined"
    src = (source or "").lower()
    auth = authoritative if authoritative is not None else (src in ("corpus", "manual", "authoritative", "publog"))
    # explicit upstream confidence label (e.g. masterfile._confidence) is respected but never upgrades a bad validation
    if confidence in ("high", "medium", "review", "low"):
        base = confidence
    elif not auth:
        base = "low"
    elif spread == "wide":
        base = "review"
    else:
        base = "high" if (n_samples or 0) >= 2 else "medium"
    if validation_status == "suspect" and _ORDER.index(base) > _ORDER.index("review"):
        base = "review"                         # a suspect value can't be better than 'check'
    if not auth and base in ("high", "medium"):
        base = "low"                            # external can never be 'verified/cited'
    return base


def badge(**kw):
    lv = level(**kw)
    return {"level": lv, "color": _COLOR.get(lv, "#9aa6b6"), "label": _LABEL.get(lv, lv),
            "show": lv != "high"}               # UI can choose to only chip the non-obvious ones


def worst(levels):
    """Aggregate: the least-trustworthy level in a set (for a card/summary)."""
    idx = min((_ORDER.index(l) for l in levels if l in _ORDER), default=_ORDER.index("high"))
    return _ORDER[idx]


# --------------------------------------------------------------------------- #
# self-test: `python trust.py`                                                #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    assert level(source="corpus", n_samples=3) == "high", level(source="corpus", n_samples=3)
    assert level(source="corpus", n_samples=1) == "medium"
    assert level(source="corpus", spread="wide", n_samples=5) == "review"
    assert level(source="external", n_samples=9) == "low"
    assert level(source="corpus", n_samples=5, validation_status="quarantine") == "quarantined"
    assert level(source="corpus", n_samples=5, validation_status="suspect") == "review"
    assert level(confidence="review", source="corpus", n_samples=9) == "review"   # explicit label respected
    assert worst(["high", "medium", "review"]) == "review"
    assert worst(["high", "high"]) == "high"
    b = badge(source="external", n_samples=1)
    assert b["level"] == "low" and b["color"] and b["show"] is True, b
    print("trust self-test PASS  (high/medium/review/low/quarantined + badge + worst)")

# END OF FILE
