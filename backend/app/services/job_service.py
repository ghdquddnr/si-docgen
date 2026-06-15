"""생성 잡 오케스트레이션 — 업로드 파일 저장, 잡 생성, 백그라운드 파이프라인 실행.

생성 단계는 검증된 JSON(시나리오, 선택적 화면정의서)까지 만들어 DB 에 저장한다 (렌더링은 검수 후).
with_screens 잡은 체인(시나리오 + 화면정의서)을 실행하고 RTM 에 화면 ID 를 연결한다.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Job, JobStatus
from app.db.session import SessionLocal
from app.exceptions import SiDocgenError
from app.pipelines.generate_chain import REQUIREMENT_SPEC_TEMPLATE, SCREEN_SPEC_TEMPLATE
from app.pipelines.generate_interface_spec import (
    INTERFACE_SPEC_TEMPLATE,
    generate_interface_spec,
)
from app.pipelines.generate_proposal import PROPOSAL_TEMPLATE, generate_proposal
from app.pipelines.generate_requirement_spec import generate_requirement_spec
from app.pipelines.generate_screen_spec import generate_screen_spec
from app.pipelines.generate_table_spec import TABLE_SPEC_TEMPLATE, generate_table_spec
from app.pipelines.generate_test_scenario import (
    RTM_TEMPLATE,
    TEST_SCENARIO_TEMPLATE,
    generate_scenario,
)
from app.pipelines.generate_user_manual import (
    USER_MANUAL_TEMPLATE,
    collect_images,
    generate_user_manual,
)
from app.pipelines.generate_wbs import WBS_TEMPLATE, generate_wbs
from app.renderers.docx_renderer import render_requirement_spec
from app.renderers.interface_spec_renderer import render_interface_spec
from app.renderers.pptx_renderer import render_screen_spec
from app.renderers.proposal_renderer import render_proposal
from app.renderers.rtm_renderer import render_rtm
from app.renderers.table_spec_renderer import render_table_spec
from app.renderers.user_manual_renderer import render_user_manual
from app.renderers.wbs_renderer import render_wbs
from app.renderers.xlsx_renderer import render_test_scenario
from app.schemas.interface_spec import InterfaceSpecDocument
from app.schemas.proposal import ProposalDocument
from app.schemas.requirement_spec import RequirementSpecDocument
from app.schemas.rtm import (
    build_rtm_from_chain,
    validate_requirement_consistency,
    validate_rtm_consistency,
    validate_screen_consistency,
)
from app.schemas.screen_spec import ScreenSpecDocument
from app.schemas.table_spec import TableSpecDocument
from app.schemas.test_scenario import TestScenarioDocument
from app.schemas.user_manual import UserManualDocument
from app.schemas.wbs import WBSDocument

logger = logging.getLogger(__name__)

# 원천 문서로 허용하는 확장자 (source_loader 지원 범위와 일치)
SUPPORTED_SUFFIXES = {".docx", ".pdf", ".md", ".markdown", ".txt"}

# 다운로드 종류 → 산출물 파일명
OUTPUT_FILES = {
    "proposal": "proposal.pptx",
    "requirement_spec": "requirement_spec.docx",
    "test_scenario": "test_scenario.xlsx",
    "rtm": "rtm.xlsx",
    "screen_spec": "screen_spec.pptx",
    "wbs": "wbs.xlsx",
    "table_spec": "table_spec.xlsx",
    "interface_spec": "interface_spec.xlsx",
    "user_manual": "user_manual.docx",
}

# 사용자 매뉴얼 화면 캡처 업로드 시 허용하는 이미지 확장자
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}


class UnsupportedSourceError(SiDocgenError):
    """업로드된 원천 문서 형식이 지원 범위를 벗어났을 때 발생 (API 에서 400 으로 매핑)."""


@dataclass(frozen=True)
class JobRenderResult:
    """잡 렌더링 결과 통계와 생성된 산출물 종류."""

    unit_count: int
    integration_count: int
    requirement_count: int
    screen_count: int
    kinds: list[str]


def job_dir(job_id: str) -> Path:
    """잡별 저장 디렉토리 경로."""
    return Path(get_settings().storage_dir) / job_id


def source_path(job_id: str, original_filename: str) -> Path:
    """잡의 원천 파일 저장 경로 (원본 확장자 유지)."""
    return job_dir(job_id) / f"source{Path(original_filename).suffix.lower()}"


def output_dir(job_id: str) -> Path:
    """잡의 렌더링 산출물 디렉토리."""
    return job_dir(job_id) / "output"


def manual_images_dir(job_id: str) -> Path:
    """사용자 매뉴얼 화면 캡처 업로드 디렉토리 ({screen_ref}.{ext} 형태로 저장)."""
    return job_dir(job_id) / "manual_images"


def manual_screen_refs(user_manual_json: dict) -> list[str]:
    """매뉴얼 JSON 에서 화면 캡처가 필요한 screen_ref 목록을 순서대로(중복 제거) 추출한다."""
    refs: list[str] = []
    for section in user_manual_json.get("sections", []):
        for step in section.get("steps", []):
            ref = step.get("screen_ref") or ""
            if ref and ref not in refs:
                refs.append(ref)
    return refs


def is_safe_screen_ref(ref: str) -> bool:
    """screen_ref 가 파일명 스템으로 안전한지 검사한다 (경로 탈출·구분자 차단)."""
    return bool(ref) and "/" not in ref and "\\" not in ref and ".." not in ref


class UnknownScreenRefError(SiDocgenError):
    """매뉴얼에 존재하지 않는 screen_ref 로 이미지를 업로드하려 할 때 발생 (API 404)."""


class UnsupportedImageError(SiDocgenError):
    """지원하지 않는 이미지 형식 업로드 시 발생 (API 400)."""


def save_manual_image(
    job_id: str, user_manual_json: dict, screen_ref: str, *, filename: str, data: bytes
) -> Path:
    """화면 캡처 이미지를 {screen_ref}.{ext} 로 저장한다.

    screen_ref 가 매뉴얼에 실제 존재하고 파일명 스템으로 안전할 때만 저장한다.
    같은 screen_ref 의 기존 이미지(확장자 무관)는 먼저 제거해 단일 매칭을 보장한다.
    """
    if not is_safe_screen_ref(screen_ref) or screen_ref not in manual_screen_refs(user_manual_json):
        raise UnknownScreenRefError(f"매뉴얼에 없는 화면 참조입니다: {screen_ref}")
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_IMAGE_SUFFIXES:
        raise UnsupportedImageError(
            f"지원하지 않는 이미지 형식입니다: {suffix or '(확장자 없음)'} "
            f"(지원: {', '.join(sorted(SUPPORTED_IMAGE_SUFFIXES))})"
        )
    images = manual_images_dir(job_id)
    images.mkdir(parents=True, exist_ok=True)
    for ext in SUPPORTED_IMAGE_SUFFIXES:  # 기존 변형 제거 (확장자가 바뀌어도 1개만 유지)
        prior = images / f"{screen_ref}{ext}"
        if prior.is_file():
            prior.unlink()
    target = images / f"{screen_ref}{suffix}"
    target.write_bytes(data)
    return target


def list_manual_images(job_id: str, user_manual_json: dict) -> dict[str, bool]:
    """매뉴얼의 screen_ref 별로 업로드된 이미지 존재 여부를 반환한다 (검수 UI 표시용)."""
    refs = manual_screen_refs(user_manual_json)
    uploaded = collect_images(manual_images_dir(job_id), refs)
    return {ref: ref in uploaded for ref in refs}


def delete_manual_image(job_id: str, screen_ref: str) -> bool:
    """업로드된 화면 캡처를 삭제한다. 삭제했으면 True, 없었으면 False."""
    if not is_safe_screen_ref(screen_ref):
        return False
    images = manual_images_dir(job_id)
    removed = False
    for ext in SUPPORTED_IMAGE_SUFFIXES:
        path = images / f"{screen_ref}{ext}"
        if path.is_file():
            path.unlink()
            removed = True
    return removed


def render_job_outputs(
    job_id: str,
    scenario_json: dict | None = None,
    screen_spec_json: dict | None = None,
    requirement_spec_json: dict | None = None,
    wbs_json: dict | None = None,
    table_spec_json: dict | None = None,
    interface_spec_json: dict | None = None,
    user_manual_json: dict | None = None,
    proposal_json: dict | None = None,
    templates: dict[str, Path] | None = None,
) -> JobRenderResult:
    """저장된(검수된) JSON 으로 산출물을 렌더링한다 (LLM 미사용).

    각 산출물은 독립적이다 — 해당 JSON 이 있을 때만 렌더링한다(문서별 메뉴 모델).
    테스트 묶음(시나리오)이 있으면 test_scenario + RTM 을, 화면정의서가 함께 있으면 RTM 에
    화면 ID 를 연결하고 pptx 도 렌더링한다(REQ→SCR→TC 추적성). 요구사항정의서·WBS·테이블·
    인터페이스정의서·사용자 매뉴얼은 각자 독립 렌더링한다.

    templates(종류→양식 경로)가 주어지면 그 양식으로, 없으면 기본 양식으로 렌더링한다.
    """
    tpls = templates or {}

    def tpl(kind: str, default: Path) -> Path:
        return tpls.get(kind, default)

    scenario = TestScenarioDocument.model_validate(scenario_json) if scenario_json else None
    screen_spec = ScreenSpecDocument.model_validate(screen_spec_json) if screen_spec_json else None
    requirement_spec = (
        RequirementSpecDocument.model_validate(requirement_spec_json)
        if requirement_spec_json
        else None
    )

    out = output_dir(job_id)
    out.mkdir(parents=True, exist_ok=True)
    kinds: list[str] = []
    unit_count = integration_count = requirement_count = screen_count = 0

    # 요구사항정의서 (독립 docx). 시나리오가 함께 있으면 요건↔시나리오/화면 추적성도 검증
    if requirement_spec is not None:
        if scenario is not None:
            validate_requirement_consistency(requirement_spec, scenario, screen_spec)
        render_requirement_spec(
            requirement_spec,
            tpl("requirement_spec", REQUIREMENT_SPEC_TEMPLATE),
            out / OUTPUT_FILES["requirement_spec"],
        )
        kinds.append("requirement_spec")

    # 테스트 묶음: 시나리오 → test_scenario + RTM (+화면정의서 pptx, 추적성)
    if scenario is not None:
        if requirement_spec is None and screen_spec is not None:
            validate_screen_consistency(screen_spec, scenario)
        rtm = build_rtm_from_chain(scenario, screen_spec, requirement_spec)
        validate_rtm_consistency(rtm, scenario)
        render_test_scenario(
            scenario,
            tpl("test_scenario", TEST_SCENARIO_TEMPLATE),
            out / OUTPUT_FILES["test_scenario"],
        )
        render_rtm(rtm, tpl("rtm", RTM_TEMPLATE), out / OUTPUT_FILES["rtm"])
        kinds.extend(["test_scenario", "rtm"])
        unit_count = len(scenario.unit_test_cases)
        integration_count = len(scenario.integration_test_cases)
        requirement_count = len(rtm.rows)
        if screen_spec is not None:
            render_screen_spec(
                screen_spec,
                tpl("screen_spec", SCREEN_SPEC_TEMPLATE),
                out / OUTPUT_FILES["screen_spec"],
            )
            kinds.append("screen_spec")
            screen_count = len(screen_spec.screens)
    elif screen_spec is not None:
        # 시나리오 없이 화면정의서만 있는 경우(방어적): pptx 만 렌더
        render_screen_spec(
            screen_spec, tpl("screen_spec", SCREEN_SPEC_TEMPLATE), out / OUTPUT_FILES["screen_spec"]
        )
        kinds.append("screen_spec")
        screen_count = len(screen_spec.screens)

    if wbs_json:
        wbs = WBSDocument.model_validate(wbs_json)
        render_wbs(wbs, tpl("wbs", WBS_TEMPLATE), out / OUTPUT_FILES["wbs"])
        kinds.append("wbs")
    if table_spec_json:
        table_spec = TableSpecDocument.model_validate(table_spec_json)
        render_table_spec(
            table_spec, tpl("table_spec", TABLE_SPEC_TEMPLATE), out / OUTPUT_FILES["table_spec"]
        )
        kinds.append("table_spec")
    if interface_spec_json:
        interface_spec = InterfaceSpecDocument.model_validate(interface_spec_json)
        render_interface_spec(
            interface_spec,
            tpl("interface_spec", INTERFACE_SPEC_TEMPLATE),
            out / OUTPUT_FILES["interface_spec"],
        )
        kinds.append("interface_spec")
    if user_manual_json:
        manual = UserManualDocument.model_validate(user_manual_json)
        refs = manual_screen_refs(user_manual_json)
        images = collect_images(manual_images_dir(job_id), refs)  # 업로드 없으면 플레이스홀더
        render_user_manual(
            manual,
            tpl("user_manual", USER_MANUAL_TEMPLATE),
            out / OUTPUT_FILES["user_manual"],
            images=images,
        )
        kinds.append("user_manual")
    if proposal_json:
        proposal = ProposalDocument.model_validate(proposal_json)
        render_proposal(
            proposal, tpl("proposal", PROPOSAL_TEMPLATE), out / OUTPUT_FILES["proposal"]
        )
        kinds.append("proposal")

    return JobRenderResult(
        unit_count=unit_count,
        integration_count=integration_count,
        requirement_count=requirement_count,
        screen_count=screen_count,
        kinds=kinds,
    )


def create_job(
    db: Session,
    *,
    filename: str,
    file_bytes: bytes,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    client: str = "",
    with_screens: bool = False,
    with_requirements: bool = False,
    with_wbs: bool = False,
    with_table_spec: bool = False,
    with_interface_spec: bool = False,
    with_user_manual: bool = False,
    with_proposal: bool = False,
    start_date: str = "",
    requirement_spec_model: str | None = None,
    scenario_model: str | None = None,
    screen_spec_model: str | None = None,
    wbs_model: str | None = None,
    table_spec_model: str | None = None,
    interface_spec_model: str | None = None,
    user_manual_model: str | None = None,
    proposal_model: str | None = None,
    template_ids: dict | None = None,
) -> Job:
    """업로드 파일을 저장하고 대기 상태 잡을 생성한다."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise UnsupportedSourceError(
            f"지원하지 않는 원천 문서 형식입니다: {suffix or '(확장자 없음)'} "
            f"(지원: {', '.join(sorted(SUPPORTED_SUFFIXES))})"
        )

    written_date = written_date or date.today().isoformat()  # 빈 값이면 오늘로 보정
    job_id = uuid.uuid4().hex
    target = source_path(job_id, filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(file_bytes)

    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        input_filename=filename,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        client=client,
        with_screens=with_screens,
        with_requirements=with_requirements,
        with_wbs=with_wbs,
        with_table_spec=with_table_spec,
        with_interface_spec=with_interface_spec,
        with_user_manual=with_user_manual,
        with_proposal=with_proposal,
        start_date=start_date or written_date,
        requirement_spec_model=requirement_spec_model or None,
        scenario_model=scenario_model or None,
        screen_spec_model=screen_spec_model or None,
        wbs_model=wbs_model or None,
        table_spec_model=table_spec_model or None,
        interface_spec_model=interface_spec_model or None,
        user_manual_model=user_manual_model or None,
        proposal_model=proposal_model or None,
        template_ids=template_ids or None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(
        "잡 생성: id=%s file=%s with_screens=%s with_requirements=%s",
        job_id,
        filename,
        with_screens,
        with_requirements,
    )
    return job


def run_job(job_id: str) -> None:
    """백그라운드 실행: 원천 파싱 → LLM 생성 → JSON 저장. 자체 DB 세션을 연다.

    각 산출물은 요청된 것만 독립 생성한다(문서별 메뉴 모델). with_screens 묶음은 시나리오에
    이어 화면정의서까지 생성하고 추적성을 검증한다. 진행값(progress)은 단계명으로 통지한다.
    """
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            logger.error("실행할 잡을 찾을 수 없음: %s", job_id)
            return
        job.status = JobStatus.RUNNING
        job.progress = "queued"
        db.commit()

        def set_progress(stage: str) -> None:
            job.progress = stage
            db.commit()

        try:
            src = source_path(job_id, job.input_filename)
            cover = {
                "project_name": job.project_name,
                "system_name": job.system_name,
                "author": job.author,
                "written_date": job.written_date or "",
            }

            # 제안서 (독립 메뉴) — RFP → 제안서 pptx. 발주처(client)는 표지에 들어간다
            if job.with_proposal:
                set_progress("proposal")
                proposal = generate_proposal(
                    src,
                    **cover,
                    client=job.client or "발주처",
                    model=job.proposal_model,
                )
                job.proposal_json = proposal.model_dump(mode="json")
                db.commit()

            # 요구사항정의서 (독립 메뉴) — 요건정의서 docx 만 생성
            if job.with_requirements:
                set_progress("requirements")
                requirement_spec = generate_requirement_spec(
                    src, **cover, model=job.requirement_spec_model
                )
                job.requirement_spec_json = requirement_spec.model_dump(mode="json")
                db.commit()

            # 테스트 설계 묶음 (독립 메뉴) — 시나리오 + 화면정의서(추적성), RTM 은 렌더 시 파생
            if job.with_screens:
                set_progress("scenario")
                scenario = generate_scenario(src, **cover, model=job.scenario_model)
                job.scenario_json = scenario.model_dump(mode="json")
                db.commit()

                set_progress("screens")
                req_ids = sorted(
                    {c.req_id for c in scenario.unit_test_cases + scenario.integration_test_cases}
                )
                screen_spec = generate_screen_spec(
                    src, **cover, req_ids=req_ids, model=job.screen_spec_model
                )
                validate_screen_consistency(screen_spec, scenario)
                job.screen_spec_json = screen_spec.model_dump(mode="json")
                db.commit()

            if job.with_wbs:
                set_progress("wbs")
                wbs = generate_wbs(
                    src,
                    **cover,
                    start_date=job.start_date or job.written_date or date.today().isoformat(),
                    model=job.wbs_model,
                )
                job.wbs_json = wbs.model_dump(mode="json")
                db.commit()

            if job.with_table_spec:
                set_progress("table_spec")
                table_spec = generate_table_spec(src, **cover, model=job.table_spec_model)
                job.table_spec_json = table_spec.model_dump(mode="json")
                db.commit()

            if job.with_interface_spec:
                set_progress("interface_spec")
                interface_spec = generate_interface_spec(
                    src, **cover, model=job.interface_spec_model
                )
                job.interface_spec_json = interface_spec.model_dump(mode="json")
                db.commit()

            if job.with_user_manual:
                set_progress("user_manual")
                manual = generate_user_manual(src, **cover, model=job.user_manual_model)
                job.user_manual_json = manual.model_dump(mode="json")
                db.commit()

            job.status = JobStatus.SUCCEEDED
            job.progress = "done"
            job.error = None
            logger.info("잡 완료: id=%s", job_id)
        except Exception as exc:  # 백그라운드라 모든 예외를 잡아 잡 상태로 기록한다
            job.status = JobStatus.FAILED
            job.progress = "error"
            job.error = str(exc)
            logger.exception("잡 실패: id=%s", job_id)
        db.commit()
