"""WBS 생성 프롬프트 평가 스크립트 — 실제 LLM 을 호출한다 (pytest 미포함).

실행 예:
  uv run python scripts/eval/eval_wbs.py
  uv run python scripts/eval/eval_wbs.py --runs 3 --input <원천 문서 경로>
"""

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.exceptions import LLMError, ValidationFailedError  # noqa: E402
from app.pipelines.generate_wbs import generate_wbs  # noqa: E402
from app.schemas.wbs import WBSTask  # noqa: E402

DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"


def _count(tasks: list[WBSTask]) -> tuple[int, int]:
    """(전체 태스크 수, 작업(leaf) 수)."""
    total = leaves = 0
    for t in tasks:
        total += 1
        if t.children:
            ct, cl = _count(t.children)
            total += ct
            leaves += cl
        else:
            leaves += 1
    return total, leaves


def main() -> None:
    parser = argparse.ArgumentParser(description="WBS 생성 품질 평가")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원천 문서 경로")
    parser.add_argument("--runs", type=int, default=1, help="반복 실행 횟수")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print(f"\n=== 평가 시작: input={args.input.name}, runs={args.runs} ===")
    successes = 0
    for run in range(1, args.runs + 1):
        start = time.monotonic()
        try:
            doc = generate_wbs(
                args.input,
                project_name="평가용 프로젝트",
                system_name="평가용 시스템",
                author="평가 스크립트",
                written_date="2026-06-14",
                start_date="2026-07-01",
            )
        except (ValidationFailedError, LLMError) as exc:
            print(f"[run {run}] 실패 ({time.monotonic() - start:.1f}s): {exc}")
            continue
        successes += 1
        total, leaves = _count(doc.tasks)
        has_pred = any(t.predecessors for t in _flatten(doc.tasks))
        print(f"[run {run}] 성공 ({time.monotonic() - start:.1f}s)")
        print(f"  - 최상위 {len(doc.tasks)}개 / 전체 {total}개 / 작업(leaf) {leaves}개")
        print(f"  - 선행 관계 사용: {'있음' if has_pred else '없음'}")

    print(f"=== 결과: {successes}/{args.runs} 성공 (검증 통과율, 재시도 포함) ===")


def _flatten(tasks: list[WBSTask]) -> list[WBSTask]:
    flat: list[WBSTask] = []
    for t in tasks:
        flat.append(t)
        flat.extend(_flatten(t.children))
    return flat


if __name__ == "__main__":
    main()
