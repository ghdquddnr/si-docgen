"""LLM JSON 생성 + Pydantic 검증-재시도 루프.

절대 원칙의 구현 지점: 모든 LLM 출력은 스키마 검증을 통과해야 하며,
검증 실패 시 오류 내용을 프롬프트에 포함해 최대 3회(설정값) 재시도한다.
최종 실패 시 ValidationFailedError 를 올리고, 미검증 데이터는 절대 반환하지 않는다.
"""

import json
import logging

from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.exceptions import ValidationFailedError
from app.llm.client import complete_json

logger = logging.getLogger(__name__)

RETRY_FEEDBACK_TEMPLATE = """{prompt}

[이전 응답의 오류]
{error}

위 오류를 수정하여, 처음 지시한 것과 동일한 JSON 스키마로 전체를 다시 출력하세요."""


def _strip_code_fence(raw: str) -> str:
    """마크다운 코드펜스(```json ... ```)로 감싼 응답에서 봉투만 제거한다.

    데이터 추출이 아니라 정규화 단계다 — 본문은 그대로 json.loads + Pydantic 으로
    검증한다. 로컬 모델은 구조화 출력을 지시해도 펜스를 붙이는 경우가 잦다.
    """
    text = raw.strip()
    if not text.startswith("```"):
        return text
    newline = text.find("\n")
    if newline != -1:
        text = text[newline + 1 :]  # ``` 또는 ```json 여는 줄 제거
    text = text.rstrip()
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def generate_validated[T: BaseModel](
    prompt: str,
    schema_cls: type[T],
    *,
    system: str | None = None,
    max_attempts: int | None = None,
) -> T:
    """LLM 으로 JSON 을 생성하고 schema_cls 검증을 통과한 모델만 반환한다."""
    attempts = max_attempts or get_settings().llm_max_attempts
    current_prompt = prompt
    last_error = ""
    json_schema = schema_cls.model_json_schema()

    for attempt in range(1, attempts + 1):
        raw = complete_json(current_prompt, system=system, json_schema=json_schema)
        try:
            data = json.loads(_strip_code_fence(raw))
        except json.JSONDecodeError as exc:
            last_error = f"JSON 파싱 실패: {exc}"
        else:
            try:
                return schema_cls.model_validate(data)
            except ValidationError as exc:
                last_error = f"스키마 검증 실패: {exc}"

        logger.warning(
            "LLM 출력 검증 실패 (시도 %d/%d, schema=%s): %s",
            attempt,
            attempts,
            schema_cls.__name__,
            last_error,
        )
        current_prompt = RETRY_FEEDBACK_TEMPLATE.format(prompt=prompt, error=last_error)

    raise ValidationFailedError(
        f"{attempts}회 시도 모두 {schema_cls.__name__} 검증 실패. 마지막 오류: {last_error}"
    )
