"""화면정의서 PPT 렌더러.

순수 함수: (검증된 ScreenSpecDocument, 템플릿 경로) → 출력 .pptx 파일.
템플릿의 표준 슬라이드(2번째)를 XML 레벨로 복제해 화면 수만큼 만들고,
shape name 기반으로 텍스트/표 값만 주입한다. 서식은 템플릿의 책임이다.
"""

import copy
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.presentation import Presentation as PresentationType
from pptx.shapes.base import BaseShape
from pptx.slide import Slide
from pptx.text.text import TextFrame

from app.exceptions import RenderError
from app.schemas.screen_spec import Screen, ScreenSpecDocument

# 템플릿 구조 상수 (backend/templates/screen_spec.pptx 와 일치해야 함)
COVER_SLIDE_INDEX = 0
STANDARD_SLIDE_INDEX = 1
FIELD_TABLE_COLUMNS = 5


def circled_number(no: int) -> str:
    """항목 번호를 ①②③ 형태의 원문자로 변환한다 (1~20 지원)."""
    if 1 <= no <= 20:
        return chr(0x2460 + no - 1)
    return str(no)


def render_screen_spec(
    doc: ScreenSpecDocument,
    template_path: Path,
    output_path: Path,
    mockup_images: dict[str, Path] | None = None,
) -> Path:
    """표지를 채우고 표준 슬라이드를 화면 수만큼 복제해 화면정의서를 생성한다.

    mockup_images 는 {화면 ID: PNG 경로} 매핑이며, 항목이 있는 화면에만 목업을 삽입한다.
    """
    if not template_path.is_file():
        raise RenderError(f"템플릿 파일이 없습니다: {template_path}")

    prs = Presentation(str(template_path))
    if len(prs.slides) < 2:
        raise RenderError(f"템플릿에 표지/표준 슬라이드 2장이 필요합니다: {template_path}")

    _fill_cover(prs.slides[COVER_SLIDE_INDEX], doc)

    standard = prs.slides[STANDARD_SLIDE_INDEX]
    for screen in doc.screens:
        new_slide = _duplicate_slide(prs, standard)
        _fill_screen(new_slide, screen)
        mockup_path = (mockup_images or {}).get(screen.screen_id)
        if mockup_path is not None:
            _insert_mockup(new_slide, mockup_path)
    _remove_slide(prs, STANDARD_SLIDE_INDEX)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    return output_path


def _duplicate_slide(prs: PresentationType, source: Slide) -> Slide:
    """슬라이드의 모든 shape 를 XML deepcopy 해 새 슬라이드로 복제한다."""
    dest = prs.slides.add_slide(source.slide_layout)
    for shape in source.shapes:
        dest.shapes._spTree.insert_element_before(copy.deepcopy(shape._element), "p:extLst")
    return dest


def _remove_slide(prs: PresentationType, index: int) -> None:
    """슬라이드 목록에서 index 위치의 슬라이드를 제거한다."""
    sld_id_lst = prs.slides._sldIdLst
    sld_id_lst.remove(list(sld_id_lst)[index])


def _find_shape(slide: Slide, name: str) -> BaseShape:
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    raise RenderError(f"슬라이드에 shape '{name}' 가 없습니다 (템플릿 구조 확인 필요)")


def _set_text(text_frame: TextFrame, text: str) -> None:
    """첫 run 의 서식을 유지한 채 텍스트만 교체한다 ('\\n' 은 줄바꿈으로 변환)."""
    para = text_frame.paragraphs[0]
    if not para.runs:
        raise RenderError("템플릿 텍스트 프레임에 서식 기준 run 이 없습니다")
    para.runs[0].text = text
    for run in para.runs[1:]:
        run._r.getparent().remove(run._r)


def _fill_cover(slide: Slide, doc: ScreenSpecDocument) -> None:
    values = {
        "cover_project": doc.project_name,
        "cover_system": doc.system_name,
        "cover_author": doc.author,
        "cover_date": doc.written_date.isoformat(),
    }
    for name, value in values.items():
        _set_text(_find_shape(slide, name).text_frame, value)


def _fill_screen(slide: Slide, screen: Screen) -> None:
    _set_text(_find_shape(slide, "slide_title").text_frame, screen.screen_name)
    _set_text(_find_shape(slide, "screen_id").text_frame, screen.screen_id)
    _set_text(_find_shape(slide, "screen_name").text_frame, screen.screen_name)
    _set_text(_find_shape(slide, "menu_path").text_frame, screen.menu_path)

    logic_text = "\n".join(f"{i}. {line}" for i, line in enumerate(screen.logic, start=1))
    _set_text(_find_shape(slide, "logic_text").text_frame, logic_text)

    _fill_field_table(slide, screen)


def _insert_mockup(slide: Slide, image_path: Path) -> None:
    """목업 PNG 를 mockup_area 영역 안에 비율을 유지(contain)하며 가운데 삽입한다."""
    if not image_path.is_file():
        raise RenderError(f"목업 이미지가 없습니다: {image_path}")
    area = _find_shape(slide, "mockup_area")
    _set_text(area.text_frame, "")  # 자리표시 문구 제거 (테두리 사각형은 액자로 유지)

    with Image.open(image_path) as image:
        img_w, img_h = image.size
    scale = min(area.width / img_w, area.height / img_h)
    width = int(img_w * scale)
    height = int(img_h * scale)
    left = area.left + (area.width - width) // 2
    top = area.top + (area.height - height) // 2
    slide.shapes.add_picture(str(image_path), left, top, width, height)


def _fill_field_table(slide: Slide, screen: Screen) -> None:
    """항목 정의 표의 서식 기준 행(2행)을 복제해 항목 수만큼 채운다."""
    frame = _find_shape(slide, "field_table")
    if not frame.has_table:
        raise RenderError("shape 'field_table' 이 표가 아닙니다 (템플릿 구조 확인 필요)")
    table = frame.table
    if len(table.columns) != FIELD_TABLE_COLUMNS or len(table.rows) < 2:
        raise RenderError("항목 정의 표는 5열 + 헤더/서식 기준 행 구조여야 합니다")

    tbl = table._tbl
    sample_tr = tbl.tr_lst[1]
    for _ in range(len(screen.fields) - 1):
        tbl.append(copy.deepcopy(sample_tr))

    # python-pptx 의 행 컬렉션은 슬라이싱을 지원하지 않아 list 로 변환한다
    for row, field in zip(list(table.rows)[1:], screen.fields, strict=True):
        values = [
            circled_number(field.no),
            field.name,
            field.field_type,
            "Y" if field.required else "N",
            field.description,
        ]
        for cell, value in zip(row.cells, values, strict=True):
            _set_text(cell.text_frame, value)
