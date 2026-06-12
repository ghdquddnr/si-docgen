"""LLM 검증-재시도 루프 테스트 (LLM 호출은 전부 모킹, 실제 API 호출 없음)."""

import pytest
from pydantic import BaseModel, Field

from app import exceptions
from app.llm import generate as gen


class SampleSchema(BaseModel):
    """테스트용 단순 스키마."""

    name: str = Field(..., min_length=1)
    count: int = Field(..., ge=0)


VALID_JSON = '{"name": "테스트", "count": 3}'
INVALID_SCHEMA_JSON = '{"name": "", "count": -1}'
BROKEN_JSON = '{"name": "테스트", '


class FakeLLM:
    """호출 순서대로 준비된 응답을 돌려주는 가짜 complete_json."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def __call__(self, prompt: str, *, system: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.responses[len(self.prompts) - 1]


def test_첫_시도_성공(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLLM([VALID_JSON])
    monkeypatch.setattr(gen, "complete_json", fake)
    result = gen.generate_validated("프롬프트", SampleSchema)
    assert isinstance(result, SampleSchema)
    assert result.name == "테스트"
    assert len(fake.prompts) == 1


def test_JSON_파싱_실패_후_재시도_성공(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLLM([BROKEN_JSON, VALID_JSON])
    monkeypatch.setattr(gen, "complete_json", fake)
    result = gen.generate_validated("프롬프트", SampleSchema)
    assert result.count == 3
    assert len(fake.prompts) == 2
    # 재시도 프롬프트에 원본 지시와 오류 피드백이 모두 포함된다
    assert "프롬프트" in fake.prompts[1]
    assert "JSON 파싱 실패" in fake.prompts[1]


def test_스키마_검증_실패_2회_후_성공(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLLM([INVALID_SCHEMA_JSON, INVALID_SCHEMA_JSON, VALID_JSON])
    monkeypatch.setattr(gen, "complete_json", fake)
    result = gen.generate_validated("프롬프트", SampleSchema)
    assert result.name == "테스트"
    assert len(fake.prompts) == 3
    assert "스키마 검증 실패" in fake.prompts[2]


def test_3회_모두_실패하면_예외(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLLM([INVALID_SCHEMA_JSON] * 3)
    monkeypatch.setattr(gen, "complete_json", fake)
    with pytest.raises(exceptions.ValidationFailedError):
        gen.generate_validated("프롬프트", SampleSchema, max_attempts=3)
    # 정확히 3회만 호출하고, 미검증 데이터는 반환되지 않는다
    assert len(fake.prompts) == 3


def test_max_attempts_인자가_설정보다_우선(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeLLM([BROKEN_JSON] * 5)
    monkeypatch.setattr(gen, "complete_json", fake)
    with pytest.raises(exceptions.ValidationFailedError):
        gen.generate_validated("프롬프트", SampleSchema, max_attempts=1)
    assert len(fake.prompts) == 1
