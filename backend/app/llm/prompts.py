"""LLM 프롬프트 템플릿.

출력 JSON 스키마 설명은 Pydantic 모델의 한국어 description 에서 자동 생성한다
(스키마가 단일 진실 공급원 — 프롬프트와 검증 기준이 어긋나지 않도록).
"""

import json

from pydantic import BaseModel

from app.pipelines.source_loader import SourceDocument

TEST_SCENARIO_SYSTEM = (
    "당신은 한국 SI 프로젝트의 테스트 시나리오 작성 전문가다. "
    "요구사항 문서를 분석해 단위/통합 테스트 시나리오를 작성한다. "
    "반드시 지시된 JSON 스키마에 맞는 JSON 객체 하나만 출력한다."
)

TEST_SCENARIO_PROMPT_TEMPLATE = """다음 원천 문서를 분석하여 테스트 시나리오를 작성하라.

[원천 문서: {filename}]
{source_text}

[작성 규칙]
1. 출력은 아래 JSON 스키마를 만족하는 JSON 객체 하나만 출력한다. 설명 문장·마크다운 금지.
2. tc_id 는 TC-001 부터 순번으로 부여한다 (단위/통합 통합 순번, 중복 금지).
3. req_id 는 원천 문서에 등장하는 요건 ID 만 참조한다. 요건 ID 가 없으면 REQ-001 부터 부여한다.
4. 단위 테스트는 기능별 정상/예외/경계 케이스를 포함하고, 통합 테스트는 기능 간 흐름을 다룬다.
5. 모든 텍스트는 한국어로 작성한다. result 는 아직 수행 전이므로 null 로 둔다.
6. 표지 정보: project_name="{project_name}", system_name="{system_name}",
   author="{author}", written_date="{written_date}".

[출력 JSON 스키마]
{schema_json}
"""


def schema_to_prompt_json(schema_cls: type[BaseModel]) -> str:
    """Pydantic 모델의 JSON Schema(한국어 description 포함)를 프롬프트용 문자열로 변환한다."""
    return json.dumps(schema_cls.model_json_schema(), ensure_ascii=False, indent=2)


def source_to_prompt_text(source: SourceDocument) -> str:
    """원천 문서를 프롬프트 삽입용 텍스트로 변환한다 (표는 행 단위 '|' 구분)."""
    parts = [source.text]
    for i, table in enumerate(source.tables, start=1):
        rows = "\n".join(" | ".join(row) for row in table)
        parts.append(f"[표 {i}]\n{rows}")
    return "\n\n".join(parts)


def build_test_scenario_prompt(
    source: SourceDocument,
    schema_cls: type[BaseModel],
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> str:
    """테스트시나리오 생성 프롬프트를 조립한다."""
    return TEST_SCENARIO_PROMPT_TEMPLATE.format(
        filename=source.filename,
        source_text=source_to_prompt_text(source),
        schema_json=schema_to_prompt_json(schema_cls),
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )
