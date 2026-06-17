"""대용량 문서 청킹 및 스키마별 Map-Reduce 병합 모듈.

원천 문서가 설정된 임계값을 초과할 때 문단 단위로 지능적으로 청킹하여 분석하고,
각 청크별 분석 결과를 각 산출물 도메인 규칙에 맞게 정밀 병합합니다.
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from app.llm.generate import generate_validated
from app.pipelines.source_loader import SourceDocument
from app.schemas.interface_spec import InterfaceSpecDocument
from app.schemas.proposal import ProposalDocument
from app.schemas.requirement_spec import RequirementSpecDocument
from app.schemas.screen_spec import ScreenSpecDocument
from app.schemas.table_spec import TableSpecDocument
from app.schemas.test_scenario import TestScenarioDocument
from app.schemas.user_manual import UserManualDocument
from app.schemas.wbs import WBSDocument, WBSTask

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    """텍스트를 double newline(\\n\\n) 기준으로 문단을 나누어 max_chars 내로 청킹한다.

    각 청크는 가급적 문맥이 끊기지 않는 문단 단위로 묶인다.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len + (2 if current_chunk else 0) > max_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            # 만약 단일 문단 자체가 max_chars 보다 크다면, 그냥 하나의 청크로 만든다.
            if p_len > max_chars:
                chunks.append(p)
            else:
                current_chunk.append(p)
                current_len = p_len
        else:
            current_chunk.append(p)
            current_len += p_len + (2 if current_len > 0 else 0)

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def _next_id(prefix: str, existing_ids: set[str], start_seq: int = 1) -> str:
    """순차적인 새로운 고유 ID를 부여한다."""
    seq = start_seq
    while True:
        candidate = f"{prefix}-{seq:03d}"
        if candidate not in existing_ids:
            return candidate
        seq += 1


def merge_requirement_specs(docs: list[RequirementSpecDocument]) -> RequirementSpecDocument:
    """요구사항정의서 목록을 정밀 병합한다."""
    if not docs:
        raise ValueError("병합할 요구사항정의서가 없습니다.")
    base = docs[0]

    merged_requirements = []
    seen_names = {}  # name -> req
    used_ids = set()

    for req in base.requirements:
        merged_requirements.append(req.model_copy())
        seen_names[req.name.strip().lower()] = merged_requirements[-1]
        used_ids.add(req.req_id)

    for doc in docs[1:]:
        for req in doc.requirements:
            name_key = req.name.strip().lower()
            if name_key in seen_names:
                existing = seen_names[name_key]
                if len(req.description) > len(existing.description):
                    existing.description = req.description
                if req.note and not existing.note:
                    existing.note = req.note
            else:
                new_req = req.model_copy()
                if new_req.req_id in used_ids:
                    new_id = _next_id("REQ", used_ids)
                    new_req.req_id = new_id
                merged_requirements.append(new_req)
                seen_names[name_key] = new_req
                used_ids.add(new_req.req_id)

    # 개정이력 병합
    all_revisions = []
    seen_revisions = set()
    for doc in docs:
        for rev in doc.revisions:
            rev_key = (rev.version, rev.revised_date.isoformat(), rev.author)
            if rev_key not in seen_revisions:
                all_revisions.append(rev.model_copy())
                seen_revisions.add(rev_key)

    return RequirementSpecDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        doc_no=base.doc_no,
        author=base.author,
        written_date=base.written_date,
        revisions=all_revisions,
        requirements=merged_requirements,
    )


def merge_test_scenarios(docs: list[TestScenarioDocument]) -> TestScenarioDocument:
    """테스트시나리오 목록을 병합하고 ID 고유성을 보장한다."""
    if not docs:
        raise ValueError("병합할 테스트시나리오가 없습니다.")
    base = docs[0]

    unit_cases = []
    integration_cases = []
    used_tc_ids = set()

    for tc in base.unit_test_cases:
        unit_cases.append(tc.model_copy())
        used_tc_ids.add(tc.tc_id)
    for tc in base.integration_test_cases:
        integration_cases.append(tc.model_copy())
        used_tc_ids.add(tc.tc_id)

    for doc in docs[1:]:
        for tc in doc.unit_test_cases:
            new_tc = tc.model_copy()
            if new_tc.tc_id in used_tc_ids:
                new_id = _next_id("TC", used_tc_ids)
                new_tc.tc_id = new_id
            unit_cases.append(new_tc)
            used_tc_ids.add(new_tc.tc_id)

        for tc in doc.integration_test_cases:
            new_tc = tc.model_copy()
            if new_tc.tc_id in used_tc_ids:
                new_id = _next_id("TC", used_tc_ids)
                new_tc.tc_id = new_id
            integration_cases.append(new_tc)
            used_tc_ids.add(new_tc.tc_id)

    return TestScenarioDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        unit_test_cases=unit_cases,
        integration_test_cases=integration_cases,
    )


def merge_screen_specs(docs: list[ScreenSpecDocument]) -> ScreenSpecDocument:
    """화면정의서 목록을 병합하며 화면명 매칭 시 내부 필드 및 로직을 병합한다."""
    if not docs:
        raise ValueError("병합할 화면정의서가 없습니다.")
    base = docs[0]

    screens = []
    seen_screen_names = {}
    used_screen_ids = set()

    for scr in base.screens:
        screens.append(scr.model_copy())
        seen_screen_names[scr.screen_name.strip().lower()] = screens[-1]
        used_screen_ids.add(scr.screen_id)

    for doc in docs[1:]:
        for scr in doc.screens:
            name_key = scr.screen_name.strip().lower()
            if name_key in seen_screen_names:
                existing = seen_screen_names[name_key]
                existing_field_names = {f.name.strip().lower() for f in existing.fields}
                for f in scr.fields:
                    if f.name.strip().lower() not in existing_field_names:
                        new_f = f.model_copy()
                        new_f.no = len(existing.fields) + 1
                        existing.fields.append(new_f)
                        existing_field_names.add(f.name.strip().lower())

                for logic_item in scr.logic:
                    if logic_item not in existing.logic:
                        existing.logic.append(logic_item)

                for req_id in scr.req_ids:
                    if req_id not in existing.req_ids:
                        existing.req_ids.append(req_id)
            else:
                new_scr = scr.model_copy()
                if new_scr.screen_id in used_screen_ids:
                    new_id = _next_id("SCR", used_screen_ids)
                    new_scr.screen_id = new_id
                screens.append(new_scr)
                seen_screen_names[name_key] = new_scr
                used_screen_ids.add(new_scr.screen_id)

    return ScreenSpecDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        screens=screens,
    )


def merge_wbs(docs: list[WBSDocument]) -> WBSDocument:
    """WBS 트리를 융합하고 중복 ID 발생 시 predecessors 관계를 보존하며 수정한다."""
    if not docs:
        raise ValueError("병합할 WBS 가 없습니다.")
    base = docs[0]

    merged_tasks = []
    seen_top_names = {}
    used_task_ids = set()

    def collect_ids(task: WBSTask):
        used_task_ids.add(task.id)
        for child in task.children:
            collect_ids(child)

    for task in base.tasks:
        merged_tasks.append(task.model_copy())
        seen_top_names[task.name.strip().lower()] = merged_tasks[-1]
        collect_ids(merged_tasks[-1])

    for doc_idx, doc in enumerate(docs[1:], start=1):
        id_map = {}

        def assign_unique_ids(
            task: WBSTask, doc_idx: int = doc_idx, id_map: dict[str, str] = id_map
        ):
            old_id = task.id
            if old_id in used_task_ids:
                new_id = f"{old_id}-{doc_idx}"
                seq = 1
                while (
                    f"{new_id}-{seq}" in used_task_ids or f"{old_id}-{doc_idx}" == f"{new_id}-{seq}"
                ):
                    seq += 1
                task.id = f"{new_id}-{seq}" if seq > 1 else new_id
            else:
                task.id = old_id

            id_map[old_id] = task.id
            used_task_ids.add(task.id)
            for child in task.children:
                assign_unique_ids(child, doc_idx, id_map)

        def update_predecessors(task: WBSTask, id_map: dict[str, str] = id_map):
            task.predecessors = [id_map.get(p, p) for p in task.predecessors]
            for child in task.children:
                update_predecessors(child, id_map)

        copied_tasks = [t.model_copy() for t in doc.tasks]
        for t in copied_tasks:
            assign_unique_ids(t)
        for t in copied_tasks:
            update_predecessors(t)

        for t in copied_tasks:
            name_key = t.name.strip().lower()
            if name_key in seen_top_names:
                existing = seen_top_names[name_key]
                if existing.is_summary and t.is_summary:
                    existing.children.extend(t.children)
                else:
                    merged_tasks.append(t)
            else:
                merged_tasks.append(t)
                seen_top_names[name_key] = t

    return WBSDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        start_date=base.start_date,
        tasks=merged_tasks,
    )


def merge_table_specs(docs: list[TableSpecDocument]) -> TableSpecDocument:
    """물리 테이블명 기준으로 중복 컬럼 제거하며 컬럼 목록 및 옵션을 융합한다."""
    if not docs:
        raise ValueError("병합할 테이블정의서가 없습니다.")
    base = docs[0]

    tables = []
    seen_table_physical = {}

    for t in base.tables:
        tables.append(t.model_copy())
        seen_table_physical[t.physical_name.strip().upper()] = tables[-1]

    for doc in docs[1:]:
        for t in doc.tables:
            phys_key = t.physical_name.strip().upper()
            if phys_key in seen_table_physical:
                existing = seen_table_physical[phys_key]
                existing_col_physical = {c.physical_name.strip().upper() for c in existing.columns}
                for c in t.columns:
                    c_phys_key = c.physical_name.strip().upper()
                    if c_phys_key not in existing_col_physical:
                        existing.columns.append(c.model_copy())
                        existing_col_physical.add(c_phys_key)
                    else:
                        existing_c = next(
                            ec
                            for ec in existing.columns
                            if ec.physical_name.strip().upper() == c_phys_key
                        )
                        if c.is_pk:
                            existing_c.is_pk = True
                        if not c.is_nullable:
                            existing_c.is_nullable = False
                        if c.description and not existing_c.description:
                            existing_c.description = c.description
                        if c.fk_ref and not existing_c.fk_ref:
                            existing_c.fk_ref = c.fk_ref
            else:
                new_t = t.model_copy()
                tables.append(new_t)
                seen_table_physical[phys_key] = new_t

    return TableSpecDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        tables=tables,
    )


def merge_interface_specs(docs: list[InterfaceSpecDocument]) -> InterfaceSpecDocument:
    """인터페이스 목록을 병합하고 고유한 interface_id 를 보장한다."""
    if not docs:
        raise ValueError("병합할 인터페이스정의서가 없습니다.")
    base = docs[0]

    interfaces = []
    seen_interface_names = {}
    used_interface_ids = set()

    for ifs in base.interfaces:
        interfaces.append(ifs.model_copy())
        seen_interface_names[ifs.name.strip().lower()] = interfaces[-1]
        used_interface_ids.add(ifs.interface_id)

    for doc in docs[1:]:
        for ifs in doc.interfaces:
            name_key = ifs.name.strip().lower()
            if name_key in seen_interface_names:
                existing = seen_interface_names[name_key]
                existing_field_names = {f.name.strip().lower() for f in existing.fields}
                for f in ifs.fields:
                    if f.name.strip().lower() not in existing_field_names:
                        existing.fields.append(f.model_copy())
                        existing_field_names.add(f.name.strip().lower())
            else:
                new_ifs = ifs.model_copy()
                if new_ifs.interface_id in used_interface_ids:
                    new_id = _next_id("IF", used_interface_ids)
                    new_ifs.interface_id = new_id
                interfaces.append(new_ifs)
                seen_interface_names[name_key] = new_ifs
                used_interface_ids.add(new_ifs.interface_id)

    return InterfaceSpecDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        interfaces=interfaces,
    )


def merge_user_manuals(docs: list[UserManualDocument]) -> UserManualDocument:
    """사용자 매뉴얼 섹션 목록을 융합하고 내부 단계를 병합한다."""
    if not docs:
        raise ValueError("병합할 사용자 매뉴얼이 없습니다.")
    base = docs[0]

    sections = []
    seen_sections = {}

    for sec in base.sections:
        sections.append(sec.model_copy())
        seen_sections[sec.title.strip().lower()] = sections[-1]

    for doc in docs[1:]:
        for sec in doc.sections:
            title_key = sec.title.strip().lower()
            if title_key in seen_sections:
                existing = seen_sections[title_key]
                existing_instructions = {st.instruction.strip().lower() for st in existing.steps}
                for st in sec.steps:
                    if st.instruction.strip().lower() not in existing_instructions:
                        existing.steps.append(st.model_copy())
                        existing_instructions.add(st.instruction.strip().lower())
            else:
                new_sec = sec.model_copy()
                sections.append(new_sec)
                seen_sections[title_key] = new_sec

    return UserManualDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        sections=sections,
    )


def merge_proposals(docs: list[ProposalDocument]) -> ProposalDocument:
    """제안서 슬라이드를 병합하고 동일 섹션 타이틀 내 불릿을 통합한다."""
    if not docs:
        raise ValueError("병합할 제안서가 없습니다.")
    base = docs[0]

    slides = []
    seen_slides = {}

    for s in base.slides:
        slides.append(s.model_copy())
        seen_slides[s.title.strip().lower()] = slides[-1]

    for doc in docs[1:]:
        for s in doc.slides:
            title_key = s.title.strip().lower()
            if title_key in seen_slides:
                existing = seen_slides[title_key]
                existing_bullets = {b.strip().lower() for b in existing.bullets}
                for b in s.bullets:
                    if b.strip().lower() not in existing_bullets:
                        existing.bullets.append(b)
                        existing_bullets.add(b.strip().lower())
            else:
                new_slide = s.model_copy()
                slides.append(new_slide)
                seen_slides[title_key] = new_slide

    return ProposalDocument(
        project_name=base.project_name,
        system_name=base.system_name,
        author=base.author,
        written_date=base.written_date,
        title=base.title,
        client=base.client,
        slides=slides,
    )


# 스펙 문서 타입별 병합 함수 등록 매핑
_MERGE_FUNCTIONS: dict[type[BaseModel], Callable[[list[Any]], Any]] = {
    RequirementSpecDocument: merge_requirement_specs,
    TestScenarioDocument: merge_test_scenarios,
    ScreenSpecDocument: merge_screen_specs,
    WBSDocument: merge_wbs,
    TableSpecDocument: merge_table_specs,
    InterfaceSpecDocument: merge_interface_specs,
    UserManualDocument: merge_user_manuals,
    ProposalDocument: merge_proposals,
}


def generate_map_reduce[T: BaseModel](
    source: SourceDocument,
    schema_cls: type[T],
    build_prompt_fn: Callable[[SourceDocument], str],
    *,
    system: str | None = None,
    model: str | None = None,
    chunk_threshold: int = 6000,
    chunk_size: int = 4000,
    on_progress: Callable[[str], None] | None = None,
) -> T:
    """원천 문서의 길이가 임계값을 초과하면 Map-Reduce 방식으로 LLM 생성 및 검증 병합을 수행하고,

    초과하지 않으면 단일 생성 및 검증을 바로 수행한다.
    """
    from app.llm.prompts import source_to_prompt_text

    # 원천 문서에서 전체 프롬프트 텍스트를 빌드
    full_text = source_to_prompt_text(source)

    if len(full_text) <= chunk_threshold:
        logger.info(
            "원천 텍스트가 임계값(%d자) 이하이므로 단일 생성으로 처리합니다 (길이: %d자)",
            chunk_threshold,
            len(full_text),
        )
        prompt = build_prompt_fn(source)
        return generate_validated(prompt, schema_cls, system=system, model=model)

    logger.info(
        "원천 텍스트가 임계값(%d자)을 초과하여 Map-Reduce 파이프라인을 가동합니다 (길이: %d자)",
        chunk_threshold,
        len(full_text),
    )

    # 1. Chunking
    chunks = chunk_text(full_text, max_chars=chunk_size)
    num_chunks = len(chunks)
    logger.info("원천 문서를 총 %d개의 청크로 분할했습니다", num_chunks)

    # 2. Map (청크별로 LLM 요청 및 스키마 검증 수행)
    chunk_docs: list[T] = []
    for idx, chunk_content in enumerate(chunks, start=1):
        logger.info("청크 생성 중 (%d/%d)...", idx, num_chunks)
        if on_progress is not None:
            on_progress(f"generating_chunk_{idx}_{num_chunks}")

        # 개별 청크용 임시 SourceDocument 생성
        temp_source = SourceDocument(
            filename=f"{source.filename}_chunk_{idx}", text=chunk_content, tables=[]
        )
        prompt = build_prompt_fn(temp_source)

        chunk_doc = generate_validated(prompt, schema_cls, system=system, model=model)
        chunk_docs.append(chunk_doc)

    # 3. Reduce (결과들을 하나로 병합)
    logger.info("청크 결과 병합 중 (Reduce)...")
    merge_fn = _MERGE_FUNCTIONS.get(schema_cls)
    if not merge_fn:
        raise ValueError(f"스키마 {schema_cls.__name__}에 대한 병합 함수가 정의되지 않았습니다.")

    merged_doc = merge_fn(chunk_docs)
    logger.info("Map-Reduce 완료 및 병합 성공")
    return merged_doc
