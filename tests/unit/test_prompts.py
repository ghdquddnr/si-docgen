"""프롬프트 조립 단위 테스트 (LLM 호출 없음)."""

from app.llm.prompts import (
    build_test_scenario_prompt,
    schema_to_prompt_json,
    source_to_prompt_text,
)
from app.pipelines.source_loader import SourceDocument
from app.schemas import test_scenario as ts

SOURCE = SourceDocument(
    filename="req.md",
    text="REQ-001 사용자 로그인 요건",
    tables=[[["요건 ID", "요건명"], ["REQ-001", "사용자 로그인"]]],
)


def test_스키마_설명이_한국어_description_포함() -> None:
    schema_json = schema_to_prompt_json(ts.TestScenarioDocument)
    assert "테스트케이스 ID" in schema_json  # tc_id 필드 description
    assert "단위테스트" in schema_json


def test_표가_프롬프트_텍스트로_평탄화() -> None:
    text = source_to_prompt_text(SOURCE)
    assert "REQ-001 사용자 로그인 요건" in text
    assert "[표 1]" in text
    assert "REQ-001 | 사용자 로그인" in text


def test_프롬프트_조립() -> None:
    prompt = build_test_scenario_prompt(
        SOURCE,
        ts.TestScenarioDocument,
        project_name="P",
        system_name="S",
        author="A",
        written_date="2026-06-13",
    )
    assert "req.md" in prompt
    assert "TC-001 부터 순번" in prompt
    assert 'project_name="P"' in prompt
    assert "출력 JSON 스키마" in prompt
