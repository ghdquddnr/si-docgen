"""사용자 매뉴얼 워드 렌더러.

순수 함수: (검증된 UserManualDocument, 템플릿 경로, 이미지 맵) → 출력 .docx 파일.
docxtpl(Jinja) 태그 치환 + 단계별 화면 캡처 이미지 삽입(InlineImage)을 수행한다.

이미지(캡처)는 렌더러 외부에서 준비되어 `images`(screen_ref → 이미지 파일 경로)로 전달된다.
렌더러는 네트워크 I/O·캡처를 수행하지 않는다(절대 원칙: 렌더러는 순수 함수).
참조 키에 해당하는 이미지가 없으면 '[화면 캡처: …]' 플레이스홀더 문자열로 대체한다.
"""

from pathlib import Path

from docx.shared import Cm
from docxtpl import DocxTemplate, InlineImage
from jinja2 import TemplateError

from app.exceptions import RenderError
from app.schemas.user_manual import UserManualDocument

# 본문 이미지 표시 폭 (A4 본문 폭에 맞춤)
_IMAGE_WIDTH = Cm(14)


def render_user_manual(
    doc: UserManualDocument,
    template_path: Path,
    output_path: Path,
    images: dict[str, Path] | None = None,
) -> Path:
    """템플릿에 매뉴얼 본문을 주입하고 단계별 캡처 이미지를 삽입해 파일을 생성한다.

    images 는 screen_ref → 캡처 이미지 파일 경로 맵이다. 누락된 참조는 플레이스홀더로 표시된다.
    """
    if not template_path.is_file():
        raise RenderError(f"템플릿 파일이 없습니다: {template_path}")

    tpl = DocxTemplate(str(template_path))
    images = images or {}
    context = doc.model_dump(mode="json")
    for section in context["sections"]:
        for step in section["steps"]:
            step["image"] = _step_image(tpl, step["screen_ref"], images)

    try:
        tpl.render(context)
    except TemplateError as exc:
        raise RenderError(f"템플릿 렌더링 실패: {template_path} ({exc})") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tpl.save(str(output_path))
    return output_path


def _step_image(tpl: DocxTemplate, screen_ref: str, images: dict[str, Path]) -> object:
    """단계의 이미지 자리를 채운다: 이미지가 있으면 InlineImage, 없으면 플레이스홀더/빈 값."""
    if screen_ref and screen_ref in images and Path(images[screen_ref]).is_file():
        return InlineImage(tpl, str(images[screen_ref]), width=_IMAGE_WIDTH)
    if screen_ref:
        return f"[화면 캡처: {screen_ref}]"
    return ""
