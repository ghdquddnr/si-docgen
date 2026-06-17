"""chunking.py 모듈에 대한 단위 테스트.

텍스트 청킹(분할), 각 산출물 유형별 병합(Deduplication/Renumbering),
그리고 generate_map_reduce 파이프라인의 오케스트레이션 및 임계값 동작을 검증한다.
"""

from datetime import date
from typing import Any

import pytest

from app.pipelines.chunking import (
    chunk_text,
    generate_map_reduce,
    merge_requirement_specs,
    merge_table_specs,
    merge_test_scenarios,
    merge_wbs,
)
from app.pipelines.source_loader import SourceDocument
from app.schemas.requirement_spec import Requirement, RequirementSpecDocument, Revision
from app.schemas.table_spec import Column, Table, TableSpecDocument
from app.schemas.test_scenario import TestCase, TestScenarioDocument
from app.schemas.wbs import WBSDocument, WBSTask


def test_chunk_text_기본_분할() -> None:
    text = "문단1입니다.\n\n문단2입니다.\n\n문단3입니다."
    # 문단 단위 합이 15자 내로 묶이게 조절
    chunks = chunk_text(text, max_chars=18)
    # "문단1입니다.\n\n문단2입니다." -> 18자 (14자 + 2자 + 2자 = 18자 이하)
    # "문단3입니다."
    assert len(chunks) == 2
    assert chunks[0] == "문단1입니다.\n\n문단2입니다."
    assert chunks[1] == "문단3입니다."


def test_chunk_text_초과_문단_단일_처리() -> None:
    text = "문단1입니다.\n\n엄청나게매우긴문단입니다.\n\n문단3"
    chunks = chunk_text(text, max_chars=10)
    # max_chars 보다 단일 문단 크기가 크면 단독 청크로 출력됨
    assert len(chunks) == 3
    assert chunks[0] == "문단1입니다."
    assert chunks[1] == "엄청나게매우긴문단입니다."
    assert chunks[2] == "문단3"


def test_merge_requirement_specs_동작() -> None:
    doc1 = RequirementSpecDocument(
        project_name="P",
        system_name="S",
        doc_no="DOC-1",
        author="A",
        written_date=date(2026, 6, 17),
        revisions=[
            Revision(version="1.0", revised_date=date(2026, 6, 17), author="A", description="최초")
        ],
        requirements=[
            Requirement(
                req_id="REQ-001",
                name="로그인",
                category="기능",
                priority="상",
                description="로그인 상세",
            ),
            Requirement(
                req_id="REQ-002",
                name="회원가입",
                category="기능",
                priority="상",
                description="회원가입 상세",
            ),
        ],
    )
    doc2 = RequirementSpecDocument(
        project_name="P",
        system_name="S",
        doc_no="DOC-1",
        author="A",
        written_date=date(2026, 6, 17),
        revisions=[
            Revision(version="1.0", revised_date=date(2026, 6, 17), author="A", description="최초")
        ],
        requirements=[
            # ID 가 겹치지만 다른 이름 -> ID 재부여 (REQ-003)
            Requirement(
                req_id="REQ-001",
                name="비밀번호 찾기",
                category="기능",
                priority="중",
                description="비번 찾기",
            ),
            # ID 와 이름이 같음 -> 병합 및 중복제거
            Requirement(
                req_id="REQ-002",
                name="회원가입",
                category="기능",
                priority="상",
                description="회원가입 상세 더긴버전 설명",
            ),
        ],
    )

    merged = merge_requirement_specs([doc1, doc2])
    assert len(merged.requirements) == 3

    req_map = {r.req_id: r for r in merged.requirements}
    assert "REQ-001" in req_map
    assert "REQ-002" in req_map
    assert "REQ-003" in req_map

    assert req_map["REQ-002"].description == "회원가입 상세 더긴버전 설명"
    assert req_map["REQ-003"].name == "비밀번호 찾기"
    assert len(merged.revisions) == 1


def test_merge_test_scenarios_동작() -> None:
    doc1 = TestScenarioDocument(
        project_name="P",
        system_name="S",
        author="A",
        written_date=date(2026, 6, 17),
        unit_test_cases=[
            TestCase(
                tc_id="TC-001",
                req_id="REQ-001",
                category_major="A",
                category_minor="B",
                scenario_name="S1",
                test_steps=["1"],
                expected_result="E1",
            ),
        ],
        integration_test_cases=[],
    )
    doc2 = TestScenarioDocument(
        project_name="P",
        system_name="S",
        author="A",
        written_date=date(2026, 6, 17),
        unit_test_cases=[
            TestCase(
                tc_id="TC-001",
                req_id="REQ-002",
                category_major="A",
                category_minor="B",
                scenario_name="S2",
                test_steps=["2"],
                expected_result="E2",
            ),
        ],
        integration_test_cases=[
            TestCase(
                tc_id="TC-002",
                req_id="REQ-002",
                category_major="A",
                category_minor="C",
                scenario_name="S3",
                test_steps=["3"],
                expected_result="E3",
            ),
        ],
    )

    merged = merge_test_scenarios([doc1, doc2])
    all_tc_ids = [c.tc_id for c in merged.unit_test_cases + merged.integration_test_cases]
    assert len(all_tc_ids) == 3
    assert len(set(all_tc_ids)) == 3  # 중복 없음
    assert "TC-003" in all_tc_ids or "TC-001" in all_tc_ids


def test_merge_wbs_동작() -> None:
    doc1 = WBSDocument(
        project_name="P",
        system_name="S",
        author="A",
        written_date=date(2026, 6, 17),
        start_date=date(2026, 6, 17),
        tasks=[
            WBSTask(
                id="analysis",
                name="분석",
                children=[
                    WBSTask(
                        id="req-analysis", name="요구사항 분석", duration_days=5, effort_md=5.0
                    ),
                ],
            )
        ],
    )
    doc2 = WBSDocument(
        project_name="P",
        system_name="S",
        author="A",
        written_date=date(2026, 6, 17),
        start_date=date(2026, 6, 17),
        tasks=[
            WBSTask(
                id="analysis",
                name="분석",
                children=[
                    # ID 중복 및 설계 참조 추가
                    WBSTask(
                        id="req-analysis", name="요구사항 추가 분석", duration_days=3, effort_md=3.0
                    ),
                ],
            ),
            WBSTask(
                id="design",
                name="설계",
                children=[
                    # 선행으로 doc2의 req-analysis 참조
                    WBSTask(
                        id="screen-design",
                        name="화면 설계",
                        duration_days=4,
                        effort_md=4.0,
                        predecessors=["req-analysis"],
                    ),
                ],
            ),
        ],
    )

    merged = merge_wbs([doc1, doc2])

    # 분석 단계 하위로 융합되어 children 2개가 되어야 함
    analysis_nodes = [t for t in merged.tasks if t.name == "분석"]
    assert len(analysis_nodes) == 1
    analysis_task = analysis_nodes[0]
    assert len(analysis_task.children) == 2

    # ID 중복으로 doc2의 req-analysis는 req-analysis-1
    # (또는 req-analysis-1-1 등)로 재생성되었어야 함
    new_analysis_id = analysis_task.children[1].id
    assert new_analysis_id != "req-analysis"

    # 설계의 screen-design predecessors 도 갱신되었어야 함
    design_task = [t for t in merged.tasks if t.name == "설계"][0]
    screen_design = design_task.children[0]
    assert screen_design.predecessors[0] == new_analysis_id


def test_merge_table_specs_동작() -> None:
    doc1 = TableSpecDocument(
        project_name="P",
        system_name="S",
        author="A",
        written_date=date(2026, 6, 17),
        tables=[
            Table(
                logical_name="사용자",
                physical_name="TB_USER",
                columns=[
                    Column(
                        logical_name="아이디",
                        physical_name="USER_ID",
                        data_type="VARCHAR(50)",
                        is_pk=True,
                    ),
                    Column(
                        logical_name="이름", physical_name="USER_NAME", data_type="VARCHAR(100)"
                    ),
                ],
            )
        ],
    )
    doc2 = TableSpecDocument(
        project_name="P",
        system_name="S",
        author="A",
        written_date=date(2026, 6, 17),
        tables=[
            Table(
                logical_name="사용자",
                physical_name="TB_USER",
                columns=[
                    Column(
                        logical_name="이름",
                        physical_name="USER_NAME",
                        data_type="VARCHAR(100)",
                        description="설명 추가",
                    ),
                    Column(logical_name="이메일", physical_name="EMAIL", data_type="VARCHAR(255)"),
                ],
            )
        ],
    )

    merged = merge_table_specs([doc1, doc2])
    assert len(merged.tables) == 1
    table = merged.tables[0]
    assert len(table.columns) == 3

    col_map = {c.physical_name: c for c in table.columns}
    assert "USER_ID" in col_map
    assert "USER_NAME" in col_map
    assert "EMAIL" in col_map
    assert col_map["USER_NAME"].description == "설명 추가"


@pytest.fixture
def mock_generate_validated(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    responses = []

    def fake_generate_validated(
        prompt: str, schema_cls: Any, system: str | None = None, model: str | None = None
    ) -> Any:
        # 응답이 순차적으로 소모됨
        data = responses.pop(0)
        return schema_cls.model_validate(data)

    monkeypatch.setattr("app.pipelines.chunking.generate_validated", fake_generate_validated)
    return responses


def test_generate_map_reduce_임계값_이하_직접호출(
    mock_generate_validated: list[dict[str, Any]],
) -> None:
    source = SourceDocument(filename="small.txt", text="짧은 텍스트입니다. 50자 미만.")

    expected_data = {
        "project_name": "P",
        "system_name": "S",
        "author": "A",
        "written_date": "2026-06-17",
        "unit_test_cases": [],
        "integration_test_cases": [],
    }
    mock_generate_validated.append(expected_data)

    # 임계값을 100자로 주어 직접 호출되게 유도
    result = generate_map_reduce(
        source,
        TestScenarioDocument,
        lambda src: "PROMPT",
        chunk_threshold=100,
    )

    assert result.project_name == "P"
    assert len(mock_generate_validated) == 0  # 소모 완료


def test_generate_map_reduce_임계값_초과_청킹분할호출(
    mock_generate_validated: list[dict[str, Any]],
) -> None:
    # double newline으로 분리된 문단 3개 구성
    source = SourceDocument(
        filename="large.txt", text="문단 1입니다.\n\n문단 2입니다.\n\n문단 3입니다."
    )

    expected_data1 = {
        "project_name": "P",
        "system_name": "S",
        "author": "A",
        "written_date": "2026-06-17",
        "unit_test_cases": [
            {
                "tc_id": "TC-001",
                "req_id": "REQ-001",
                "category_major": "A",
                "category_minor": "B",
                "scenario_name": "S1",
                "test_steps": ["1"],
                "expected_result": "E1",
            }
        ],
        "integration_test_cases": [],
    }
    expected_data2 = {
        "project_name": "P",
        "system_name": "S",
        "author": "A",
        "written_date": "2026-06-17",
        "unit_test_cases": [
            {
                "tc_id": "TC-001",
                "req_id": "REQ-002",
                "category_major": "A",
                "category_minor": "B",
                "scenario_name": "S2",
                "test_steps": ["2"],
                "expected_result": "E2",
            }
        ],
        "integration_test_cases": [],
    }
    expected_data3 = {
        "project_name": "P",
        "system_name": "S",
        "author": "A",
        "written_date": "2026-06-17",
        "unit_test_cases": [],
        "integration_test_cases": [],
    }
    mock_generate_validated.append(expected_data1)
    mock_generate_validated.append(expected_data2)
    mock_generate_validated.append(expected_data3)

    # 임계값을 15자로 낮춰 청킹을 강제 (각 문단은 7~8자 정도)
    result = generate_map_reduce(
        source,
        TestScenarioDocument,
        lambda src: "PROMPT",
        chunk_threshold=15,
        chunk_size=15,
    )

    assert result.project_name == "P"
    assert len(result.unit_test_cases) == 2
    assert result.unit_test_cases[0].tc_id == "TC-001"
    assert result.unit_test_cases[1].tc_id == "TC-002"  # ID 중복 자동 해결 검증
    assert len(mock_generate_validated) == 0  # 2번의 LLM 호출 모두 소모
