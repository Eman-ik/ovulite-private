"""Command-line entry point for the pregnancy prediction experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

from .experiment import ExperimentConfig, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None)
    parser.add_argument("--output", default="outputs/pregnancy_prediction")
    parser.add_argument("--cutoff", default="2025-12-01")
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()
    result = run_experiment(
        args.csv,
        ExperimentConfig(output_dir=Path(args.output), cutoff=args.cutoff, folds=args.folds),
    )
    print(f"Experiment complete: {args.output}")
    print(f"OOF champion: {result['champion_by_oof_brier']}")


if __name__ == "__main__":
    main()
