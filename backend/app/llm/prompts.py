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
{req_context}
[작성 규칙]
1. 출력은 아래 JSON 스키마를 만족하는 JSON 객체 하나만 출력한다. 설명 문장·마크다운 금지.
2. tc_id 는 TC-001 부터 순번으로 부여한다 (단위/통합 통합 순번, 중복 금지).
3. req_id 는 [요건 목록] 이 주어지면 그 목록의 ID 만 사용한다(목록에 없는 ID 생성 금지).
   목록이 없으면 원천 문서의 요건 ID 를, 그것도 없으면 REQ-001 부터 부여한다.
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


def _requirement_context(requirements: list[tuple[str, str]] | None) -> str:
    """확정 요건 목록(REQ ID, 요건명)을 프롬프트 삽입용 블록으로 변환한다.

    체인의 머리(요구사항정의서)에서 확정된 요건을 시나리오 생성에 주입해,
    TC 가 그 요건 ID 만 참조하도록(추적성) 유도한다. 비어 있으면 빈 문자열.
    """
    if not requirements:
        return ""
    lines = "\n".join(f"- {req_id}: {name}" for req_id, name in requirements)
    return f"\n[요건 목록] — req_id 는 반드시 이 목록의 ID 만 사용한다\n{lines}\n"


def build_test_scenario_prompt(
    source: SourceDocument,
    schema_cls: type[BaseModel],
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    requirements: list[tuple[str, str]] | None = None,
) -> str:
    """테스트시나리오 생성 프롬프트를 조립한다.

    requirements(확정 요건 목록)가 주어지면 TC 가 그 요건 ID 만 참조하도록 유도한다.
    """
    return TEST_SCENARIO_PROMPT_TEMPLATE.format(
        filename=source.filename,
        source_text=source_to_prompt_text(source),
        req_context=_requirement_context(requirements),
        schema_json=schema_to_prompt_json(schema_cls),
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )


SCREEN_SPEC_SYSTEM = (
    "당신은 한국 SI 프로젝트의 화면 설계 전문가다. "
    "요구사항 문서를 분석해 화면정의서를 작성한다. "
    "반드시 지시된 JSON 스키마에 맞는 JSON 객체 하나만 출력한다."
)

SCREEN_SPEC_PROMPT_TEMPLATE = """다음 원천 문서를 분석하여 화면정의서를 작성하라.

[원천 문서: {filename}]
{source_text}

[작성 규칙]
1. 출력은 아래 JSON 스키마를 만족하는 JSON 객체 하나만 출력한다. 설명 문장·마크다운 금지.
2. screen_id 는 SCR-001 부터 순번으로 부여한다 (중복 금지).
3. 각 화면의 req_ids 에는 그 화면이 실현하는 요건 ID 를 아래 [요건 ID 목록] 에서만 선택해 넣는다.
   목록에 없는 요건 ID 는 절대 만들지 않는다.
4. fields 의 no 는 1 부터 순번이며, 화면의 입력/표시 항목을 빠짐없이 나열한다.
5. logic 에는 화면의 주요 처리 로직을 줄 단위로 작성한다.
6. 모든 텍스트는 한국어로 작성한다.
7. 표지 정보: project_name="{project_name}", system_name="{system_name}",
   author="{author}", written_date="{written_date}".

[요건 ID 목록]
{req_ids}

[출력 JSON 스키마]
{schema_json}
"""


REQUIREMENT_SPEC_SYSTEM = (
    "당신은 한국 SI 프로젝트의 요구사항 분석 전문가다. "
    "RFP·회의록·기존 요구사항 문서를 분석해 요구사항정의서를 작성한다. "
    "반드시 지시된 JSON 스키마에 맞는 JSON 객체 하나만 출력한다."
)

REQUIREMENT_SPEC_PROMPT_TEMPLATE = """다음 원천 문서를 분석하여 요구사항정의서를 작성하라.

[원천 문서: {filename}]
{source_text}

[작성 규칙]
1. 출력은 아래 JSON 스키마를 만족하는 JSON 객체 하나만 출력한다. 설명 문장·마크다운 금지.
2. req_id 는 REQ-001 부터 순번으로 부여한다 (중복 금지). 원천 문서에 요건 ID 가 이미
   있으면 그 ID 를 보존한다.
3. 각 요건의 name 은 간결한 명사형, description 은 검증 가능한 수준으로 구체적으로 작성한다.
4. category 는 기능/비기능/인터페이스/보안 중 가장 적합한 값으로, priority 는 상/중/하 로 정한다.
5. 원천 문서에 근거가 없는 요건을 지어내지 않는다. note 는 근거가 있을 때만 채우고 없으면 "".
6. doc_no 는 "REQ-SPEC-{year}-001" 형식으로 작성한다.
7. revisions 에는 최초 작성 이력 1건을 넣는다:
   version="1.0", revised_date="{written_date}", author="{author}", description="최초 작성".
8. 모든 텍스트는 한국어로 작성한다.
9. 표지 정보: project_name="{project_name}", system_name="{system_name}",
   author="{author}", written_date="{written_date}".

[출력 JSON 스키마]
{schema_json}
"""


def build_requirement_spec_prompt(
    source: SourceDocument,
    schema_cls: type[BaseModel],
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> str:
    """요구사항정의서 생성 프롬프트를 조립한다."""
    return REQUIREMENT_SPEC_PROMPT_TEMPLATE.format(
        filename=source.filename,
        source_text=source_to_prompt_text(source),
        schema_json=schema_to_prompt_json(schema_cls),
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        year=written_date[:4] if len(written_date) >= 4 else written_date,
    )


WBS_SYSTEM = (
    "당신은 한국 SI 프로젝트의 PM(프로젝트 관리) 전문가다. "
    "프로젝트 범위 문서를 분석해 작업분해구조(WBS)를 작성한다. "
    "반드시 지시된 JSON 스키마에 맞는 JSON 객체 하나만 출력한다."
)

WBS_PROMPT_TEMPLATE = """다음 원천 문서를 분석하여 작업분해구조(WBS)를 작성하라.

[원천 문서: {filename}]
{source_text}

[작성 규칙]
1. 출력은 아래 JSON 스키마를 만족하는 JSON 객체 하나만 출력한다. 설명 문장·마크다운 금지.
2. 2~3단계 트리로 구성한다: 최상위는 공정 단계(예: 분석/설계/개발/시험/이행),
   그 아래 children 으로 세부 작업을 둔다.
3. 각 태스크의 id 는 영문 소문자-하이픈 슬러그로 문서 전체에서 유일하게 부여한다
   (예: req-analysis, screen-design). 계층 번호(1.1.2)는 출력하지 않는다 — 렌더러가 계산한다.
4. 자식이 없는 '작업' 태스크에만 duration_days(1 이상)·effort_md(0 초과)·role 을 채운다.
   요약(상위) 태스크의 기간·공수는 비워도 된다(렌더러가 자식에서 계산).
5. predecessors 에는 선행 '작업' 태스크의 id 만 넣는다(요약 태스크 id·순환 금지).
   시작일/종료일은 출력하지 않는다 — 렌더러가 선행 관계로 계산한다.
6. deliverable 에는 그 작업의 산출물명을 적는다(예: 요구사항정의서). 없으면 "".
7. 모든 텍스트는 한국어로 작성한다.
8. 표지 정보: project_name="{project_name}", system_name="{system_name}",
   author="{author}", written_date="{written_date}", start_date="{start_date}".

[출력 JSON 스키마]
{schema_json}
"""


TABLE_SPEC_SYSTEM = (
    "당신은 한국 SI 프로젝트의 데이터 모델링(DBA) 전문가다. "
    "요구사항 문서를 분석해 테이블정의서를 작성한다. "
    "반드시 지시된 JSON 스키마에 맞는 JSON 객체 하나만 출력한다."
)

TABLE_SPEC_PROMPT_TEMPLATE = """다음 원천 문서를 분석하여 테이블정의서를 작성하라.

[원천 문서: {filename}]
{source_text}

[작성 규칙]
1. 출력은 아래 JSON 스키마를 만족하는 JSON 객체 하나만 출력한다. 설명 문장·마크다운 금지.
2. 업무에 필요한 테이블을 도출한다. 각 테이블의 physical_name 은 영문 대문자+언더스코어
   (예: TB_USER), 문서 전체에서 유일하게 부여한다.
3. 각 테이블의 columns 에는 컬럼을 빠짐없이 나열한다. physical_name 은 한 테이블 안에서 유일,
   data_type 은 VARCHAR(n)/NUMBER/DATE/CHAR(n) 등 구체적으로 적는다.
4. 각 테이블에 기본키(is_pk=true) 컬럼을 둔다. 외래키는 fk_ref 에 "참조테이블.컬럼" 형식으로
   적고(예: TB_DEPT.DEPT_CODE), 외래키가 아니면 "".
5. is_nullable 은 필수 컬럼이면 false. default 와 description 은 해당될 때만 채운다.
6. 모든 한국어 텍스트는 한국어로 작성한다(논리명·설명). 물리명·타입은 영문/표준 표기.
7. 표지 정보: project_name="{project_name}", system_name="{system_name}",
   author="{author}", written_date="{written_date}".

[출력 JSON 스키마]
{schema_json}
"""


def build_table_spec_prompt(
    source: SourceDocument,
    schema_cls: type[BaseModel],
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
) -> str:
    """테이블정의서 생성 프롬프트를 조립한다."""
    return TABLE_SPEC_PROMPT_TEMPLATE.format(
        filename=source.filename,
        source_text=source_to_prompt_text(source),
        schema_json=schema_to_prompt_json(schema_cls),
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
    )


def build_wbs_prompt(
    source: SourceDocument,
    schema_cls: type[BaseModel],
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    start_date: str,
) -> str:
    """WBS 생성 프롬프트를 조립한다. 계층번호·일정은 렌더러가 계산하므로 LLM 은 구조만 만든다."""
    return WBS_PROMPT_TEMPLATE.format(
        filename=source.filename,
        source_text=source_to_prompt_text(source),
        schema_json=schema_to_prompt_json(schema_cls),
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        start_date=start_date,
    )


def build_screen_spec_prompt(
    source: SourceDocument,
    schema_cls: type[BaseModel],
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    req_ids: list[str],
) -> str:
    """화면정의서 생성 프롬프트를 조립한다. req_ids 로 화면↔요건 연결을 유도한다."""
    req_id_text = ", ".join(req_ids) if req_ids else "(원천 문서에서 식별되는 요건 ID 사용)"
    return SCREEN_SPEC_PROMPT_TEMPLATE.format(
        filename=source.filename,
        source_text=source_to_prompt_text(source),
        schema_json=schema_to_prompt_json(schema_cls),
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        req_ids=req_id_text,
    )
