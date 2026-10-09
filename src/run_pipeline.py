"""Run the whole project end to end.

    python3 src/run_pipeline.py            # everything
    python3 src/run_pipeline.py --fast     # skip data generation (reuse existing CSVs)

Order matters: each step consumes the previous step's outputs, which is what
makes the pipeline reproducible rather than a pile of notebooks.

    1. generate_data      simulate the star schema (planted DQ issues included)
    2. clean_data         audit + fix, write the data-quality report
    3. run_sql            build the SQLite warehouse, run all sql/*.sql
    4. decompose          mechanism -> structure -> intersect attribution
    5. five_whys          the evidential why-chain
    6. write_report       findings report + recommendations, from the numbers
    7. make_figures       the ten decision charts
    8. write_reports      the brief, the deck, the Word report and the PDF
    9. validate           grade the diagnostic against the ground truth
"""

import importlib
import sys
import time
from pathlib import Path

import _bootstrap  # noqa: F401

sys.path.append(str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

STEPS = [
    ("generate simulated dataset", "generate_data", True),
    ("clean + data-quality report", "clean_data", True),
    ("build warehouse, run SQL", "run_sql", True),
    ("decompose: mechanism/structure/intersect", "decompose", False),
    ("evidential 5-whys", "five_whys", False),
    ("write findings + recommendations", "write_report", False),
    ("figures", "make_figures", False),
    ("reports: brief, deck, word, pdf", "write_reports", False),
    ("validate against ground truth", "validate_against_truth", False),
]


def main():
    fast = "--fast" in sys.argv
    C.ensure_dirs()
    print(f"=== {C.COMPANY} — revenue decline diagnostic ===")
    print(f"    periods: {C.PERIODS[0]['label']} vs {C.PERIODS[1]['label']}"
          f"   seed: {C.SEED}{'   [--fast]' if fast else ''}\n")

    failures = []
    t_all = time.time()
    for i, (label, module_name, regenerate) in enumerate(STEPS, 1):
        if fast and regenerate:
            print(f"[{i}/{len(STEPS)}] {label} — skipped (--fast)")
            continue
        print(f"[{i}/{len(STEPS)}] {label}")
        t0 = time.time()
        module = importlib.import_module(module_name)
        try:
            rc = module.main()
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1
        except Exception as e:  # surface the failing step, keep going
            print(f"    !! {module_name} raised {type(e).__name__}: {e}")
            failures.append(f"{module_name}: {type(e).__name__}: {e}")
            continue
        dt = time.time() - t0
        status = "" if not rc else f"  (exit {rc})"
        print(f"    ok in {dt:.1f}s{status}\n")
        if rc:
            failures.append(f"{module_name}: exit {rc}")

    total = time.time() - t_all
    print(f"=== finished in {total:.1f}s ===")
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("All steps completed and the diagnostic passed validation.")
    print(f"Start here: {C.PROJECT_ROOT / 'README.md'}")
    print(f"Then read:  {C.DOCS / '04_findings_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
