"""사용자 매뉴얼 생성 프롬프트 평가 스크립트 — 실제 LLM 을 호출한다 (pytest 미포함).

실행 예:
  uv run python scripts/eval/eval_user_manual.py
  uv run python scripts/eval/eval_user_manual.py --runs 3 --input <원천 문서 경로>
"""

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.exceptions import LLMError, ValidationFailedError  # noqa: E402
from app.pipelines.generate_user_manual import generate_user_manual  # noqa: E402

DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="사용자 매뉴얼 생성 품질 평가")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원천 문서 경로")
    parser.add_argument("--runs", type=int, default=1, help="반복 실행 횟수")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print(f"\n=== 평가 시작: input={args.input.name}, runs={args.runs} ===")
    successes = 0
    for run in range(1, args.runs + 1):
        start = time.monotonic()
        try:
            doc = generate_user_manual(
                args.input,
                project_name="평가용 프로젝트",
                system_name="평가용 시스템",
                author="평가 스크립트",
                written_date="2026-06-14",
            )
        except (ValidationFailedError, LLMError) as exc:
            print(f"[run {run}] 실패 ({time.monotonic() - start:.1f}s): {exc}")
            continue
        successes += 1
        steps = sum(len(s.steps) for s in doc.sections)
        with_ref = sum(1 for s in doc.sections for st in s.steps if st.screen_ref)
        print(f"[run {run}] 성공 ({time.monotonic() - start:.1f}s)")
        print(f"  - 섹션 {len(doc.sections)}개 / 단계 {steps}개")
        print(f"  - screen_ref 가 있는 단계 {with_ref}/{steps}")

    print(f"=== 결과: {successes}/{args.runs} 성공 (검증 통과율, 재시도 포함) ===")


if __name__ == "__main__":
    main()
