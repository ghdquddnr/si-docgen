"""테스트시나리오 생성 프롬프트 평가 스크립트 — 실제 LLM 을 호출한다 (pytest 미포함).

실행 예:
  uv run python scripts/eval/eval_test_scenario.py
  uv run python scripts/eval/eval_test_scenario.py --runs 3 --input <원천 문서 경로>
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.exceptions import LLMError, ValidationFailedError  # noqa: E402
from app.llm.generate import generate_validated  # noqa: E402
from app.llm.prompts import TEST_SCENARIO_SYSTEM, build_test_scenario_prompt  # noqa: E402
from app.pipelines.source_loader import load_source  # noqa: E402
from app.schemas.test_scenario import TestScenarioDocument  # noqa: E402

DEFAULT_INPUT = ROOT / "tests" / "fixtures" / "sources" / "sample_requirements.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="테스트시나리오 생성 품질 평가")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="원천 문서 경로")
    parser.add_argument("--runs", type=int, default=1, help="반복 실행 횟수")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    source = load_source(args.input)
    source_req_ids = set(re.findall(r"REQ-\d{3,}", source.text))
    prompt = build_test_scenario_prompt(
        source,
        TestScenarioDocument,
        project_name="평가용 프로젝트",
        system_name="평가용 시스템",
        author="평가 스크립트",
        written_date="2026-06-13",
    )

    condition = f"model={settings.llm_model}, input={args.input.name}, runs={args.runs}"
    print(f"\n=== 평가 시작: {condition} ===")
    successes = 0
    for run in range(1, args.runs + 1):
        start = time.monotonic()
        try:
            doc = generate_validated(prompt, TestScenarioDocument, system=TEST_SCENARIO_SYSTEM)
        except (ValidationFailedError, LLMError) as exc:
            print(f"[run {run}] 실패 ({time.monotonic() - start:.1f}s): {exc}")
            continue
        successes += 1
        elapsed = time.monotonic() - start
        all_cases = doc.unit_test_cases + doc.integration_test_cases
        tc_ids = [c.tc_id for c in all_cases]
        used_req_ids = {c.req_id for c in all_cases}
        unknown_reqs = used_req_ids - source_req_ids if source_req_ids else set()
        print(
            f"[run {run}] 성공 ({elapsed:.1f}s): 단위 {len(doc.unit_test_cases)}건"
            f" + 통합 {len(doc.integration_test_cases)}건"
        )
        print(f"  - TC ID 중복: {'없음' if len(tc_ids) == len(set(tc_ids)) else '있음!'}")
        print(f"  - 참조 요건 ID: {sorted(used_req_ids)}")
        if unknown_reqs:
            print(f"  - ⚠ 원천 문서에 없는 요건 ID 참조: {sorted(unknown_reqs)}")

    print(f"=== 결과: {successes}/{args.runs} 성공 (검증 통과율, 재시도 포함) ===")


if __name__ == "__main__":
    main()
