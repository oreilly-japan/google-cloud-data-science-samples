"""Shared safe command-line entry point for the three Vizier samples."""

from __future__ import annotations

import argparse
import sys

from vizier_runner import render_dry_run, run_workflow, settings_from_args

DEFAULTS = {
    "grid": ("HVAC Basic Grid Search", 7),
    "bayesian": ("HVAC Bayesian Optimization", 15),
    "multi_objective": ("HVAC Advanced Optimization", 25),
}


def build_parser(step: str) -> argparse.ArgumentParser:
    display_name, trial_count = DEFAULTS[step]
    parser = argparse.ArgumentParser(description=f"Chapter 13 {step} Vizier workflow")
    parser.add_argument("--project", help="Google Cloud project ID (or GOOGLE_CLOUD_PROJECT)")
    parser.add_argument("--location", help="regional location (or GOOGLE_CLOUD_LOCATION)")
    parser.add_argument(
        "--experiment",
        default=f"ch13-{step}",
        help="Experiments on Agent Platform display name",
    )
    parser.add_argument(
        "--client-id", default="chapter-13-sample", help="stable Vizier suggestion client ID"
    )
    parser.add_argument("--study-display-name", default=display_name)
    parser.add_argument(
        "--study-name", help="reuse this full Study resource name; avoids creating another Study"
    )
    parser.add_argument("--trial-count", type=int, default=trial_count)
    parser.add_argument("--seed", type=int, help="seed only the local simulator noise")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate settings and print requests without importing Cloud SDKs",
    )
    parser.add_argument(
        "--confirm-cloud-run",
        action="store_true",
        help="required before any Cloud client or API call",
    )
    if step != "grid":
        parser.add_argument(
            "--allow-billable",
            action="store_true",
            help="acknowledge default-algorithm Trial billing risk",
        )
    return parser


def main(step: str, argv: list[str] | None = None) -> int:
    parser = build_parser(step)
    args = parser.parse_args(argv)
    if not args.dry_run and not args.confirm_cloud_run:
        parser.error("refusing Cloud access: pass --dry-run or --confirm-cloud-run")
    if step != "grid" and not args.dry_run and not args.allow_billable:
        parser.error(
            "refusing default-algorithm Trials: pass --allow-billable "
            "after checking current pricing"
        )
    try:
        result = run_workflow(
            step=step,
            settings=settings_from_args(args),
            display_name=args.study_display_name,
            trial_count=args.trial_count,
            seed=args.seed,
            dry_run=args.dry_run,
            existing_study_name=args.study_name,
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    if args.dry_run:
        print(render_dry_run(result))
    else:
        print(f"Study: {result.study_name}")
        print(f"Completed trials: {result.completed_trials}")
        print(f"Optimal trials returned: {len(result.optimal_trials)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main("grid"))
