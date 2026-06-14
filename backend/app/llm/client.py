"""LiteLLM 기반 LLM 호출 래퍼.

LLM 호출은 반드시 이 모듈을 경유한다 (벤더 SDK 직접 호출 금지).
모델명·토큰 수·소요 시간은 INFO, 프롬프트 본문은 DEBUG 레벨로 기록한다.
"""

import logging
import time

from app.config import get_settings
from app.exceptions import LLMError

logger = logging.getLogger(__name__)


def complete_json(
    prompt: str,
    *,
    system: str | None = None,
    json_schema: dict | None = None,
    model: str | None = None,
) -> str:
    """JSON 모드로 LLM 을 호출해 응답 본문 문자열을 반환한다.

    json_schema 가 주어지면 구조화 출력(스키마 강제)을 요청한다 — 로컬 모델처럼
    프롬프트 지시만으로 필드를 누락하기 쉬운 모델에서 검증 통과율을 크게 높인다.
    model 이 주어지면 설정 기본 모델 대신 그 모델을 사용한다 (단계별 모델 전환).
    """
    # litellm 은 임포트가 무겁기(수 초) 때문에 실제 호출 시점에 지연 임포트한다
    from litellm import completion

    settings = get_settings()
    model_name = model or settings.llm_model
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if json_schema is not None:
        response_format: dict = {
            "type": "json_schema",
            "json_schema": {"name": "output", "schema": json_schema, "strict": True},
        }
    else:
        response_format = {"type": "json_object"}

    logger.debug("LLM 프롬프트(system=%s):\n%s", bool(system), prompt)
    start = time.monotonic()
    try:
        response = completion(
            model=model_name,
            messages=messages,
            response_format=response_format,
            api_base=settings.llm_api_base,
            timeout=settings.llm_timeout,
        )
    except Exception as exc:  # litellm 은 벤더별 예외를 던지므로 광범위하게 잡아 변환한다
        raise LLMError(f"LLM 호출 실패 (model={model_name}): {exc}") from exc
    elapsed = time.monotonic() - start

    usage = getattr(response, "usage", None)
    logger.info(
        "LLM 호출 완료: model=%s tokens(prompt=%s, completion=%s) elapsed=%.1fs",
        model_name,
        getattr(usage, "prompt_tokens", "?"),
        getattr(usage, "completion_tokens", "?"),
        elapsed,
    )

    content = response.choices[0].message.content
    if not content:
        raise LLMError(f"LLM 응답이 비어 있습니다 (model={model_name})")
    return content
