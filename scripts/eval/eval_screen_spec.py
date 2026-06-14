"""화면정의서 생성 프롬프트 평가 스크립트 — 실제 LLM 을 호출한다 (pytest 미포함).

실행 예:
  uv run python scripts/eval/eval_screen_spec.py
  uv run python scripts/eval/eval_screen_spec.py --runs 3 --input <원천 문서 경로>
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.exceptions import LLMError, ValidationFailedError  # noqa: E402
from app.pipelines.generate_screen_spec import generate_screen_spec  # noqa: E402
from app.pipelines.source_loader import load_source  # noqa: E402

DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="화면정의서 생성 품질 평가")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원천 문서 경로")
    parser.add_argument("--runs", type=int, default=1, help="반복 실행 횟수")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    source = load_source(args.input)
    source_req_ids = sorted(set(re.findall(r"REQ-\d{3,}", source.text)))

    print(f"\n=== 평가 시작: input={args.input.name}, runs={args.runs} ===")
    print(f"원천 요건 ID: {source_req_ids}")
    successes = 0
    for run in range(1, args.runs + 1):
        start = time.monotonic()
        try:
            doc = generate_screen_spec(
                args.input,
                project_name="평가용 프로젝트",
                system_name="평가용 시스템",
                author="평가 스크립트",
                written_date="2026-06-14",
                req_ids=source_req_ids,
            )
        except (ValidationFailedError, LLMError) as exc:
            print(f"[run {run}] 실패 ({time.monotonic() - start:.1f}s): {exc}")
            continue
        successes += 1
        elapsed = time.monotonic() - start
        scr_ids = [s.screen_id for s in doc.screens]
        used_reqs = sorted({r for s in doc.screens for r in s.req_ids})
        unknown = sorted(set(used_reqs) - set(source_req_ids)) if source_req_ids else []
        print(f"[run {run}] 성공 ({elapsed:.1f}s): 화면 {len(doc.screens)}개")
        print(f"  - SCR ID 중복: {'없음' if len(scr_ids) == len(set(scr_ids)) else '있음!'}")
        print(f"  - 화면이 참조한 요건 ID: {used_reqs}")
        if unknown:
            print(f"  - ⚠ 원천에 없는 요건 ID 참조: {unknown}")

    print(f"=== 결과: {successes}/{args.runs} 성공 (검증 통과율, 재시도 포함) ===")


if __name__ == "__main__":
    main()
