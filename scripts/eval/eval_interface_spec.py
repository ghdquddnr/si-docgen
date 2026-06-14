"""인터페이스정의서 생성 프롬프트 평가 스크립트 — 실제 LLM 을 호출한다 (pytest 미포함).

실행 예:
  uv run python scripts/eval/eval_interface_spec.py
  uv run python scripts/eval/eval_interface_spec.py --runs 3 --input <원천 문서 경로>
"""

import argparse
import logging
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.exceptions import LLMError, ValidationFailedError  # noqa: E402
from app.pipelines.generate_interface_spec import generate_interface_spec  # noqa: E402

DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="인터페이스정의서 생성 품질 평가")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원천 문서 경로")
    parser.add_argument("--runs", type=int, default=1, help="반복 실행 횟수")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print(f"\n=== 평가 시작: input={args.input.name}, runs={args.runs} ===")
    successes = 0
    for run in range(1, args.runs + 1):
        start = time.monotonic()
        try:
            doc = generate_interface_spec(
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
        fields = sum(len(i.fields) for i in doc.interfaces)
        methods = Counter(i.method for i in doc.interfaces)
        ids = [i.interface_id for i in doc.interfaces]
        print(f"[run {run}] 성공 ({time.monotonic() - start:.1f}s)")
        print(f"  - 인터페이스 {len(doc.interfaces)}개 / 항목 {fields}개")
        print(f"  - IF ID 중복: {'없음' if len(ids) == len(set(ids)) else '있음!'}")
        print(f"  - 연계 방식 분포: {dict(methods)}")

    print(f"=== 결과: {successes}/{args.runs} 성공 (검증 통과율, 재시도 포함) ===")


if __name__ == "__main__":
    main()
