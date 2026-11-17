"""Two-minute first run: a throwaway store for the fictional user Alex, a dry run over demo/, and a sample report.

Nothing is read from a mailbox and nothing is written anywhere but the folder given (or a new temp folder).
"""
import os, tempfile
from . import store, classify as C, learn as L, report as R, doctor as D
from .util import load, dump, parse_ts

DEMO_NOW = "2026-03-02T08:00:00Z"
NOTE = "Sample run on fictional data (Alex, example.com). Nothing was read, changed or sent."


def run(skill_dir, out_dir=None, preset="medium"):
    demo = os.path.join(skill_dir, "demo")
    out_dir = out_dir or tempfile.mkdtemp(prefix="dear-inbox-zero-demo-")
    store_dir = os.path.join(out_dir, "store")
    if os.path.exists(store_dir) and os.listdir(store_dir):
        raise store.StoreError(f"{store_dir} is not empty; pick a new --dir")
    now = parse_ts(DEMO_NOW)

    # setup, as first-install does it: consent → study → calibration answers → go live
    store.init(store_dir, "alex-demo", "Europe/Amsterdam", ["mail", "calendar", "teams"], now)
    st = store.load_state(store_dir)
    L.study(st, load(os.path.join(demo, "observations.json")), now)
    L.apply_answers(st, load(os.path.join(demo, "answers.json")), now)
    L.go_live(st, now, preset)
    store.publish(store_dir, st, now)

    # the daily run, dry: plan nothing, change nothing
    st = store.load_state(store_dir)
    decisions = C.classify(st, load(os.path.join(demo, "items.json")), load(os.path.join(demo, "calendar.json")), dry_run=True)
    md = R.render(st, decisions, now, [NOTE])

    paths = {"store": store_dir, "decisions": os.path.join(out_dir, "decisions.json"), "report": os.path.join(out_dir, "report.md")}
    dump(paths["decisions"], decisions)
    with open(paths["report"], "w", encoding="utf-8") as fh:
        fh.write(md)
    check = D.run(skill_dir, store_dir)
    return {"report": md, "paths": paths, "doctor_ok": check["ok"], "doctor_errors": check["errors"]}
