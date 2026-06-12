"""요구사항정의서 워드 렌더러.

순수 함수: (검증된 RequirementSpecDocument, 템플릿 경로) → 출력 .docx 파일.
docxtpl(Jinja) 태그 치환만 수행하며, 문서 구조와 서식은 템플릿의 책임이다.
"""

from pathlib import Path

from docxtpl import DocxTemplate
from jinja2 import TemplateError

from app.exceptions import RenderError
from app.schemas.requirement_spec import RequirementSpecDocument


def render_requirement_spec(
    doc: RequirementSpecDocument, template_path: Path, output_path: Path
) -> Path:
    """템플릿의 Jinja 태그에 값을 주입해 요구사항정의서 파일을 생성한다."""
    if not template_path.is_file():
        raise RenderError(f"템플릿 파일이 없습니다: {template_path}")

    tpl = DocxTemplate(str(template_path))
    # mode="json": date 등을 직렬화 가능한 문자열(YYYY-MM-DD)로 변환해 치환한다
    context = doc.model_dump(mode="json")
    try:
        tpl.render(context)
    except TemplateError as exc:
        raise RenderError(f"템플릿 렌더링 실패: {template_path} ({exc})") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tpl.save(str(output_path))
    return output_path
