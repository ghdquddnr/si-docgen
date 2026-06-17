"""WBS(work breakdown structure, 작업분해구조) 산출물의 Pydantic 스키마.

설계 원칙(CLAUDE.md): **계층 번호(1.1.2)와 일정 계산은 LLM 이 아니라 렌더러 측 코드 로직**이
담당한다. 따라서 입력 모델은 태스크의 트리 구조·기간·공수·선행 관계만 담고,
계층 번호·시작일/종료일·요약 태스크 공수 합산은 렌더러가 계산한다.

선행 태스크(predecessors)는 렌더러가 계산하는 계층 번호가 아니라 안정적 `id` 로 참조한다.
"""

from datetime import date

from pydantic import BaseModel, Field, model_validator


class WBSTask(BaseModel):
    """WBS 태스크 1개 — 자식이 있으면 요약 태스크, 없으면 작업(leaf) 태스크."""

    id: str = Field(
        ...,
        min_length=1,
        description="태스크 식별자 (선행 참조용, 문서 내 유일). 계층 번호와 별개의 안정적 키",
    )
    name: str = Field(..., min_length=1, description="태스크명 (예: 요구사항 분석)")
    role: str = Field("", description="담당 역할 (예: PL). 요약 태스크는 비울 수 있음")
    duration_days: int = Field(
        0,
        ge=0,
        description="기간(일). 작업(leaf) 태스크의 일정 계산용. 요약 태스크는 자식 기준 자동 계산",
    )
    effort_md: float = Field(
        0,
        ge=0,
        description="공수(MD). 작업(leaf) 태스크 값. 요약 태스크는 자식 합산으로 렌더러가 계산",
    )
    predecessors: list[str] = Field(
        default_factory=list,
        description="선행 태스크 id 목록(작업 태스크 id 참조). 일정은 선행 종료 다음 날부터 시작",
    )
    deliverable: str = Field("", description="산출물 (예: 요구사항정의서). 없으면 빈 문자열")
    children: list["WBSTask"] = Field(
        default_factory=list, description="하위 태스크 목록. 비어 있지 않으면 요약 태스크"
    )

    @property
    def is_summary(self) -> bool:
        """자식이 있으면 요약 태스크."""
        return len(self.children) > 0


def _iter_tasks(tasks: list[WBSTask]) -> list[WBSTask]:
    """트리를 전위 순회로 평탄화한다."""
    flat: list[WBSTask] = []
    for task in tasks:
        flat.append(task)
        flat.extend(_iter_tasks(task.children))
    return flat


class WBSDocument(BaseModel):
    """WBS 산출물 전체 — 표지 정보, 프로젝트 시작일, 태스크 트리."""

    project_name: str = Field(..., min_length=1, description="프로젝트명 (표지)")
    system_name: str = Field(..., min_length=1, description="시스템명 (표지)")
    author: str = Field(..., min_length=1, description="작성자 (표지)")
    written_date: date = Field(..., description="작성일 (YYYY-MM-DD)")
    start_date: date = Field(..., description="프로젝트 시작일. 일정 계산의 기준일")
    tasks: list[WBSTask] = Field(..., min_length=1, description="최상위 태스크 목록 (최소 1건)")

    @model_validator(mode="after")
    def _check_tree(self) -> "WBSDocument":
        """ID 유일성·작업 태스크 기간·선행 참조·순환을 검증한다."""
        flat = _iter_tasks(self.tasks)

        # ① ID 유일성
        ids = [t.id for t in flat]
        dups = sorted({i for i in ids if ids.count(i) > 1})
        if dups:
            raise ValueError(f"태스크 id 가 중복되었습니다: {dups}")

        leaf_ids = {t.id for t in flat if not t.is_summary}
        all_task_ids = {t.id for t in flat}

        # ② 작업(leaf) 태스크는 기간 1일 이상
        bad_duration = sorted(t.id for t in flat if not t.is_summary and t.duration_days < 1)
        if bad_duration:
            raise ValueError(f"작업 태스크는 기간이 1 이상이어야 합니다: {bad_duration}")

        # ③ 선행 참조는 존재하는 태스크 id 만, 자기 자신 금지
        for task in flat:
            for pred in task.predecessors:
                if pred == task.id:
                    raise ValueError(f"태스크 '{task.id}' 가 자기 자신을 선행으로 참조합니다")
                if pred not in all_task_ids:
                    raise ValueError(
                        f"태스크 '{task.id}' 의 선행 '{pred}' 가 존재하지 않는 태스크입니다"
                    )

        # ④ 선행 그래프 순환 검출 (요약 태스크 선행 참조를 리프 태스크로 풀어서 검사)
        self._check_no_cycle(flat, leaf_ids)
        return self

    @staticmethod
    def _check_no_cycle(flat: list[WBSTask], leaf_ids: set[str]) -> None:
        tasks_dict = {t.id: t for t in flat}
        parent_map = {}
        for t in flat:
            for child in t.children:
                parent_map[child.id] = t.id

        def get_leaf_descendants(tid: str) -> set[str]:
            t = tasks_dict[tid]
            if not t.is_summary:
                return {t.id}
            res = set()
            for child in t.children:
                res.update(get_leaf_descendants(child.id))
            return res

        def get_ancestors(tid: str) -> list[str]:
            ancestors = [tid]
            curr = tid
            while curr in parent_map:
                curr = parent_map[curr]
                ancestors.append(curr)
            return ancestors

        # Resolve leaf-to-leaf dependencies
        leaf_dependencies: dict[str, set[str]] = {lid: set() for lid in leaf_ids}
        for lid in leaf_ids:
            for ancestor_id in get_ancestors(lid):
                ancestor_task = tasks_dict[ancestor_id]
                for pred in ancestor_task.predecessors:
                    if pred in tasks_dict:
                        leaf_dependencies[lid].update(get_leaf_descendants(pred))

        state: dict[str, int] = {}  # 0=방문중, 1=완료

        def visit(node: str) -> None:
            if state.get(node) == 1:
                return
            if state.get(node) == 0:
                raise ValueError(f"선행 관계에 순환이 있습니다 (태스크 '{node}')")
            state[node] = 0
            for p in leaf_dependencies.get(node, []):
                if p == node:
                    raise ValueError(
                        f"태스크 '{node}' 가 자기 자신(또는 하위/상위 태스크)을 "
                        "선행으로 참조하거나 순환을 형성합니다"
                    )
                visit(p)
            state[node] = 1

        for lid in leaf_ids:
            visit(lid)

