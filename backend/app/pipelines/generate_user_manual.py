"""사용자 매뉴얼 LLM 생성 파이프라인.

원천 문서에서 검증된 UserManualDocument(섹션·단계 JSON)를 생성한다. 화면 캡처 이미지는
이 단계에서 만들지 않으며(LLM 은 screen_ref 만 출력), 렌더 시 이미지 맵이 없으면 플레이스홀더로
표시된다. 실제 캡처(Playwright)는 후속 단계에서 처리한다. REQ→SCR→TC 체인과 독립적이다.
"""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.llm.prompts import USER_MANUAL_SYSTEM, build_user_manual_prompt
from app.pipelines.chunking import generate_map_reduce
from app.pipelines.source_loader import SourceDocument, load_source
from app.renderers.user_manual_renderer import render_user_manual
from app.schemas.user_manual import UserManualDocument

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
USER_MANUAL_TEMPLATE = ROOT / "backend" / "templates" / "user_manual.docx"

# 수동 이미지 폴더에서 인식하는 확장자
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp")


@dataclass(frozen=True)
class UserManualResult:
    """사용자 매뉴얼 산출물 경로와 통계."""

    user_manual_path: Path
    section_count: int
    step_count: int
    image_count: int  # 실제 삽입된 캡처 이미지 수 (나머지 화면 자리는 플레이스홀더)


def collect_images(images_dir: Path, screen_refs: Iterable[str]) -> dict[str, Path]:
    """이미지 폴더에서 screen_ref 와 같은 이름의 이미지 파일을 찾아 맵(screen_ref→경로)을 만든다.

    예: screen_ref="SCR-001" 이면 images_dir/SCR-001.png(또는 .jpg 등)을 찾는다.
    """
    mapping: dict[str, Path] = {}
    for ref in screen_refs:
        if not ref:
            continue
        for ext in _IMAGE_EXTS:
            candidate = images_dir / f"{ref}{ext}"
            if candidate.is_file():
                mapping[ref] = candidate
                break
    return mapping


def generate_user_manual(
    input_path: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> UserManualDocument:
    """원천 문서에서 검증된 사용자 매뉴얼(JSON 모델)을 생성한다.

    model 이 주어지면 그 모델을, 없으면 설정의 user_manual_model(또는 기본 모델)을 쓴다.
    """
    if on_progress is not None:
        on_progress("parsing")
    logger.info("원천 문서 파싱(사용자 매뉴얼): %s", input_path)
    source = load_source(input_path)

    if on_progress is not None:
        on_progress("generating")
    logger.info("사용자 매뉴얼 LLM 생성 시작 (Map-Reduce 적용 가능)")

    def build_prompt(src: SourceDocument) -> str:
        return build_user_manual_prompt(
            src,
            UserManualDocument,
            project_name=project_name,
            system_name=system_name,
            author=author,
            written_date=written_date,
        )

    manual = generate_map_reduce(
        source,
        UserManualDocument,
        build_prompt,
        system=USER_MANUAL_SYSTEM,
        model=model or get_settings().user_manual_model,
        on_progress=on_progress,
    )
    logger.info("사용자 매뉴얼 생성 완료: 섹션 %d개", len(manual.sections))
    return manual


def generate_and_render_user_manual(
    input_path: Path,
    output_dir: Path,
    *,
    project_name: str,
    system_name: str,
    author: str,
    written_date: str,
    model: str | None = None,
    images: dict[str, Path] | None = None,
    images_dir: Path | None = None,
) -> UserManualResult:
    """원천 문서 1건에서 사용자 매뉴얼을 생성·렌더링한다 (CLI 일괄 흐름).

    images(screen_ref→캡처 파일) 또는 images_dir(폴더에서 {screen_ref}.png 수집)로 캡처를 채운다.
    둘 다 없으면 화면 캡처 자리는 플레이스홀더로 렌더된다.
    """
    doc = generate_user_manual(
        input_path,
        project_name=project_name,
        system_name=system_name,
        author=author,
        written_date=written_date,
        model=model,
    )
    if images is None and images_dir is not None:
        refs = {st.screen_ref for s in doc.sections for st in s.steps if st.screen_ref}
        images = collect_images(images_dir, refs)
    images = images or {}

    output_dir.mkdir(parents=True, exist_ok=True)
    path = render_user_manual(
        doc, USER_MANUAL_TEMPLATE, output_dir / "user_manual.docx", images=images
    )
    step_count = sum(len(s.steps) for s in doc.sections)
    logger.info(
        "사용자 매뉴얼 렌더링 완료: %s (섹션 %d · 단계 %d · 이미지 %d)",
        path,
        len(doc.sections),
        step_count,
        len(images),
    )
    return UserManualResult(
        user_manual_path=path,
        section_count=len(doc.sections),
        step_count=step_count,
        image_count=len(images),
    )
