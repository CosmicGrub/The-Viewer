"""training.py -- guided LEARN / QUIZ mode generated from the corpus (brief-req: young mechanics AND seasoned
SMEs). Turns real, cited facts (torque values, dimensions, part identities, procedure steps) into multiple-
choice questions with plausible distractors, so a new mechanic builds knowledge against the actual manuals --
and every answer links back to the cited page to learn from, not just guess. Deterministic given a seed
(reproducible quizzes). Pure and unit-testable; the route feeds it facts from measures / parts."""

from __future__ import annotations
import random, re

_NUM = re.compile(r"[-+]?\d*\.?\d+")


def _f(v):
    m = _NUM.search(str(v or ""))
    return float(m.group(0)) if m else None


def _distractors(correct, unit, rng, k=3):
    """Plausible wrong numeric answers near the correct value (never equal)."""
    c = _f(correct)
    out = []
    if c is None:
        return out
    tries = 0
    while len(out) < k and tries < 40:
        tries += 1
        factor = rng.choice([0.5, 0.75, 0.8, 1.25, 1.5, 2.0]) if abs(c) >= 1 else 1
        delta = rng.choice([-3, -2, -1, 1, 2, 3]) * (max(1, round(abs(c) * 0.15)) if abs(c) >= 1 else 0.01)
        cand = round(c * factor + delta, 3) if rng.random() < 0.5 else round(c + delta, 3)
        if cand <= 0 or abs(cand - c) < 1e-9 or cand in out:
            continue
        txt = ("%g %s" % (cand, unit)).strip()
        if txt not in out:
            out.append(txt)
    return out


def build_quiz(facts, n=10, seed=None):
    """facts: [{subject, type, value, unit, doc, page}]. -> [{question, choices, answer, cite}].
    Numeric facts become 'what is the <type> for <subject>?' with nearby distractors."""
    rng = random.Random(seed if seed is not None else 1234)
    items = []
    for f in facts or []:
        subj = (f.get("subject") or "").strip()
        typ = (f.get("type") or "value").strip()
        val = f.get("value")
        unit = (f.get("unit") or "").strip()
        if not subj or val is None:
            continue
        correct = ("%s %s" % (val, unit)).strip()
        distr = _distractors(val, unit, rng)
        if len(distr) < 3:
            continue
        choices = distr[:3] + [correct]
        rng.shuffle(choices)
        items.append({
            "question": "What is the %s for %s?" % (typ, subj),
            "choices": choices,
            "answer": correct,
            "answer_idx": choices.index(correct),
            "cite": ({"doc": f.get("doc"), "page": f.get("page")} if f.get("doc") else None),
        })
        if len(items) >= n:
            break
    return items


def score(items, answers):
    """answers: list of chosen indices (or None). -> {correct, total, pct, review:[wrong items]}."""
    correct, review = 0, []
    for i, it in enumerate(items):
        chosen = answers[i] if i < len(answers) else None
        if chosen == it["answer_idx"]:
            correct += 1
        else:
            review.append({"question": it["question"], "your": (it["choices"][chosen] if (chosen is not None and chosen < len(it["choices"])) else None),
                           "answer": it["answer"], "cite": it["cite"]})
    total = len(items)
    return {"correct": correct, "total": total, "pct": round(100 * correct / total) if total else 0, "review": review}


# --------------------------------------------------------------------------- #
# self-test: `python training.py`                                             #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    facts = [
        {"subject": "the alternator mounting bolts", "type": "torque", "value": "35", "unit": "ft-lb", "doc": "2", "page": "4-12"},
        {"subject": "highway tire pressure", "type": "pressure", "value": "35", "unit": "psi", "doc": "1", "page": "2-3"},
        {"subject": "the input shaft", "type": "diameter", "value": "0.50", "unit": "in", "doc": "3", "page": "5-1"},
    ]
    quiz = build_quiz(facts, seed=7)
    assert len(quiz) == 3, quiz
    for q in quiz:
        assert len(q["choices"]) == 4 and q["answer"] in q["choices"], q
        assert q["choices"][q["answer_idx"]] == q["answer"], q
        assert len(set(q["choices"])) == 4, ("distractors not unique", q)
    print("build_quiz OK -> %d questions, e.g. %r" % (len(quiz), quiz[0]["question"]))
    print("   choices:", quiz[0]["choices"], "answer:", quiz[0]["answer"])

    # score: answer first right, others wrong
    ans = [quiz[0]["answer_idx"], (quiz[1]["answer_idx"] + 1) % 4, None]
    sc = score(quiz, ans)
    assert sc["correct"] == 1 and sc["total"] == 3 and len(sc["review"]) == 2, sc
    print("score OK -> %d/%d (%d%%), %d to review" % (sc["correct"], sc["total"], sc["pct"], len(sc["review"])))
    # reproducible with a seed
    assert build_quiz(facts, seed=7)[0]["choices"] == quiz[0]["choices"], "not reproducible"
    print("reproducible-with-seed OK")
    print("training self-test PASS")

# END OF FILE
