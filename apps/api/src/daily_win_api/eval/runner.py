from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from daily_win_api.ai.exceptions import ModelGatewayError, ModelGatewaySchemaError
from daily_win_api.ai.gateway import ModelGateway, build_model_gateway
from daily_win_api.ai.providers.fake import FakeModelGateway, adaptive_daily_win_draft
from daily_win_api.ai.schemas import DailyWinGenerationResult
from daily_win_api.core.config import DEFAULT_OPENAI_MODEL, Settings, get_settings
from daily_win_api.eval.fixtures import load_eval_fixtures
from daily_win_api.eval.scoring import (
    HUMAN_RUBRIC_KEYS,
    result_to_dict,
    score_generation,
    score_invalid_payload,
    write_results,
)

RESULTS_DIR = Path(__file__).resolve().parents[3] / "eval-results"
SUPPORTED_MODELS = ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol")


def run_eval(
    *,
    sample: int | None,
    fixture_ids: list[str] | None,
    live: bool,
    model: str,
    settings: Settings | None = None,
    output_dir: Path | None = None,
) -> Path:
    fixtures = load_eval_fixtures()
    if fixture_ids:
        wanted = set(fixture_ids)
        fixtures = [item for item in fixtures if item.id in wanted]
    if sample is not None:
        fixtures = fixtures[:sample]
    if not fixtures:
        raise SystemExit("No eval fixtures selected.")

    gateway = _gateway(live=live, model=model, settings=settings)
    rows = []
    for fixture in fixtures:
        try:
            generated = _generate(gateway, fixture)
            scored = score_generation(fixture, generated)
        except (ModelGatewaySchemaError, ModelGatewayError) as exc:
            scored = score_invalid_payload(
                fixture,
                model=model,
                provider="openai" if live else "fake",
                error=exc.code,
            )
        rows.append(scored)

    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "live": live,
        "model": model,
        "baseline_model": DEFAULT_OPENAI_MODEL,
        "fixture_count": len(rows),
        "automated_pass_count": sum(1 for item in rows if item.all_automated_passed),
        "human_rubric_keys": list(HUMAN_RUBRIC_KEYS),
        "note": (
            "Eval results are operational comparison artifacts. They are not "
            "canonical learner memory and must not be written to PostgreSQL "
            "child tables."
        ),
        "results": [result_to_dict(item) for item in rows],
    }
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    mode = "live" if live else "fake"
    directory = output_dir or RESULTS_DIR
    path = directory / f"{stamp}-{mode}-{model.replace('.', '_')}.json"
    write_results(path, payload)
    return path


def _generate(gateway: ModelGateway, fixture) -> DailyWinGenerationResult:
    if isinstance(gateway, FakeModelGateway) and fixture.win_kind == "adaptive":
        return FakeModelGateway(
            draft=adaptive_daily_win_draft(fixture.context.nickname)
        ).generate_daily_win(fixture.context)
    return gateway.generate_daily_win(fixture.context)


def _gateway(*, live: bool, model: str, settings: Settings | None) -> ModelGateway:
    if not live:
        return FakeModelGateway()
    resolved = settings or get_settings()
    live_settings = resolved.model_copy(update={"openai_model": model})
    return build_model_gateway(live_settings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a small Daily Win model evaluation. Default uses the fake "
            "gateway and does not call OpenAI. Pass --live only when you "
            "intend to spend API budget."
        )
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=2,
        help="Number of fixtures to run from the start of the catalog (default 2).",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        dest="fixture_ids",
        help="Run a specific fixture id. Repeatable. Overrides --sample.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the configured OpenAI model. Off by default.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_OPENAI_MODEL,
        choices=SUPPORTED_MODELS,
        help="Model id for live runs. Terra remains the product default.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print fixture ids and exit without generating.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every fixture. Still fake unless --live is also passed.",
    )
    parser.add_argument(
        "--suite",
        choices=(
            "planner",
            "learner",
            "probes",
            "quality",
            "decision",
            "integrity",
            "all",
        ),
        help=(
            "Run offline educational-quality suites instead of generation eval. "
            "Does not call a live model."
        ),
    )
    parser.add_argument(
        "--compare",
        choices=("terra-luna",),
        help=(
            "Fair frozen-plan renderer bakeoff. Does not change OPENAI_MODEL. "
            "Still fake unless --live is also passed."
        ),
    )
    parser.add_argument(
        "--rescore-bakeoff",
        nargs="?",
        const="DEFAULT",
        metavar="PATH",
        help=(
            "Re-score stored Terra/Luna drafts. No live calls. "
            "Defaults to the 20260919T211946Z artifact."
        ),
    )
    parser.add_argument(
        "--summarize-review",
        metavar="PATH",
        help="Aggregate filled blinded human scores. Exploratory, n=8.",
    )
    parser.add_argument(
        "--reveal",
        metavar="PATH",
        help="Reveal mapping JSON for --summarize-review.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.summarize_review:
        from daily_win_api.eval.human_review import (
            load_reveal,
            summarize_human_review,
        )
        from daily_win_api.eval.scoring import write_results

        review_path = Path(args.summarize_review)
        reveal_path = Path(args.reveal) if args.reveal else review_path.with_name(
            review_path.name.replace("-review.md", "-reveal.json")
        )
        if not reveal_path.exists():
            reveal_path = RESULTS_DIR / "20260919T211946Z-terra-luna-reveal.json"
        summary = summarize_human_review(
            review_path.read_text(encoding="utf-8"),
            load_reveal(reveal_path),
        )
        out = review_path.with_name(
            review_path.stem + "-summary.json"
        )
        write_results(out, summary)
        print(f"Wrote {out}")
        if not summary["complete"]:
            print(
                f"Human scores incomplete ({summary['n_scored']}/"
                f"{summary['n_cases']} cases). Fill the review file first."
            )
        return
    if args.rescore_bakeoff:
        from daily_win_api.eval.bakeoff_rescore import (
            ORIGINAL_BAKEOFF,
            rescore_terra_luna_artifact,
        )

        source = (
            ORIGINAL_BAKEOFF
            if args.rescore_bakeoff == "DEFAULT"
            else Path(args.rescore_bakeoff)
        )
        paths = rescore_terra_luna_artifact(source)
        for label, path in paths.items():
            print(f"Wrote {label}: {path}")
        return
    if args.compare == "terra-luna":
        from daily_win_api.eval.bakeoff import run_terra_luna_bakeoff

        paths = run_terra_luna_bakeoff(live=args.live)
        for label, path in paths.items():
            print(f"Wrote {label}: {path}")
        return
    if args.suite:
        path = _run_suite(args.suite)
        print(f"Wrote {path}")
        return
    fixtures = load_eval_fixtures()
    if args.list:
        for item in fixtures:
            print(f"{item.id}\t{item.win_kind}\t{item.support}\t{item.label}")
        return
    sample = None if args.all or args.fixture_ids else args.sample
    path = run_eval(
        sample=sample,
        fixture_ids=args.fixture_ids,
        live=args.live,
        model=args.model,
    )
    print(f"Wrote {path}")


def _run_suite(name: str) -> Path:
    from daily_win_api.eval.suites import SUITE_RUNNERS, write_offline_report

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    if name == "all":
        path = RESULTS_DIR / f"{stamp}-edu-all.json"
        write_offline_report(path)
        return path
    result = SUITE_RUNNERS[name]()
    path = RESULTS_DIR / f"{stamp}-edu-{name}.json"
    write_results(
        path,
        {
            "created_at": datetime.now(UTC).isoformat(),
            "suite": name,
            "total": result.total,
            "failed": result.failed,
            "errors": list(result.errors),
            "passed": result.passed,
            "note": "Offline educational-quality eval. Not learner memory.",
        },
    )
    return path
