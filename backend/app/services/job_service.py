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
from app.pipelines.generate_requirement_spec import generate_requirement_spec
from app.pipelines.generate_screen_spec import generate_screen_spec
from app.pipelines.generate_test_scenario import (
    RTM_TEMPLATE,
    TEST_SCENARIO_TEMPLATE,
    generate_scenario,
)
from app.pipelines.generate_wbs import WBS_TEMPLATE, generate_wbs
from app.renderers.docx_renderer import render_requirement_spec
from app.renderers.pptx_renderer import render_screen_spec
from app.renderers.rtm_renderer import render_rtm
from app.renderers.wbs_renderer import render_wbs
from app.renderers.xlsx_renderer import render_test_scenario
from app.schemas.requirement_spec import RequirementSpecDocument
from app.schemas.rtm import (
    build_rtm_from_chain,
    validate_requirement_consistency,
    validate_rtm_consistency,
    validate_screen_consistency,
)
from app.schemas.screen_spec import ScreenSpecDocument
from app.schemas.test_scenario import TestScenarioDocument
from app.schemas.wbs import WBSDocument

logger = logging.getLogger(__name__)

# 원천 문서로 허용하는 확장자 (source_loader 지원 범위와 일치)
SUPPORTED_SUFFIXES = {".docx", ".pdf", ".md", ".markdown", ".txt"}

# 다운로드 종류 → 산출물 파일명
OUTPUT_FILES = {
    "requirement_spec": "requirement_spec.docx",
    "test_scenario": "test_scenario.xlsx",
    "rtm": "rtm.xlsx",
    "screen_spec": "screen_spec.pptx",
    "wbs": "wbs.xlsx",
}


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


def render_job_outputs(
    job_id: str,
    scenario_json: dict,
    screen_spec_json: dict | None = None,
    requirement_spec_json: dict | None = None,
    wbs_json: dict | None = None,
) -> JobRenderResult:
    """저장된(검수된) JSON 으로 산출물을 렌더링한다 (LLM 미사용).

    화면정의서 JSON 이 있으면 RTM 에 화면 ID 를 연결하고 pptx 도 렌더링한다.
    요구사항정의서 JSON 이 있으면(체인의 머리) RTM 요건명을 그것으로 채우고 docx 도 렌더링한다.
    WBS JSON 이 있으면(체인과 독립) wbs.xlsx 도 렌더링한다.
    """
    scenario = TestScenarioDocument.model_validate(scenario_json)
    screen_spec = ScreenSpecDocument.model_validate(screen_spec_json) if screen_spec_json else None
    requirement_spec = (
        RequirementSpecDocument.model_validate(requirement_spec_json)
        if requirement_spec_json
        else None
    )

    if requirement_spec is not None:
        validate_requirement_consistency(requirement_spec, scenario, screen_spec)
    elif screen_spec is not None:
        validate_screen_consistency(screen_spec, scenario)

    rtm = build_rtm_from_chain(scenario, screen_spec, requirement_spec)
    validate_rtm_consistency(rtm, scenario)

    out = output_dir(job_id)
    out.mkdir(parents=True, exist_ok=True)
    kinds: list[str] = []
    if requirement_spec is not None:
        render_requirement_spec(
            requirement_spec, REQUIREMENT_SPEC_TEMPLATE, out / OUTPUT_FILES["requirement_spec"]
        )
        kinds.append("requirement_spec")
    render_test_scenario(scenario, TEST_SCENARIO_TEMPLATE, out / OUTPUT_FILES["test_scenario"])
    render_rtm(rtm, RTM_TEMPLATE, out / OUTPUT_FILES["rtm"])
    kinds.extend(["test_scenario", "rtm"])
    if screen_spec is not None:
        render_screen_spec(screen_spec, SCREEN_SPEC_TEMPLATE, out / OUTPUT_FILES["screen_spec"])
        kinds.append("screen_spec")
    if wbs_json:
        wbs = WBSDocument.model_validate(wbs_json)
        render_wbs(wbs, WBS_TEMPLATE, out / OUTPUT_FILES["wbs"])
        kinds.append("wbs")

    return JobRenderResult(
        unit_count=len(scenario.unit_test_cases),
        integration_count=len(scenario.integration_test_cases),
        requirement_count=len(rtm.rows),
        screen_count=len(screen_spec.screens) if screen_spec else 0,
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
    with_screens: bool = False,
    with_requirements: bool = False,
    with_wbs: bool = False,
    start_date: str = "",
    requirement_spec_model: str | None = None,
    scenario_model: str | None = None,
    screen_spec_model: str | None = None,
    wbs_model: str | None = None,
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
        with_screens=with_screens,
        with_requirements=with_requirements,
        with_wbs=with_wbs,
        start_date=start_date or written_date,
        requirement_spec_model=requirement_spec_model or None,
        scenario_model=scenario_model or None,
        screen_spec_model=screen_spec_model or None,
        wbs_model=wbs_model or None,
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

    with_screens 잡은 시나리오에 이어 화면정의서까지 생성하고 추적성을 검증한다.
    진행값(progress): 비체인=parsing/generating, 체인=scenario/screens.
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

            if job.with_requirements:
                set_progress("requirements")
                requirement_spec = generate_requirement_spec(
                    src, **cover, model=job.requirement_spec_model
                )
                job.requirement_spec_json = requirement_spec.model_dump(mode="json")
                db.commit()
                req_pairs = [(r.req_id, r.name) for r in requirement_spec.requirements]
                screen_req_ids = [r.req_id for r in requirement_spec.requirements]

                set_progress("scenario")
                scenario = generate_scenario(
                    src, **cover, requirements=req_pairs, model=job.scenario_model
                )
                job.scenario_json = scenario.model_dump(mode="json")
                db.commit()

                set_progress("screens")
                screen_spec = generate_screen_spec(
                    src, **cover, req_ids=screen_req_ids, model=job.screen_spec_model
                )
                validate_requirement_consistency(requirement_spec, scenario, screen_spec)
                job.screen_spec_json = screen_spec.model_dump(mode="json")
            elif job.with_screens:
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
            else:
                scenario = generate_scenario(src, **cover, on_progress=set_progress)
                job.scenario_json = scenario.model_dump(mode="json")

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
