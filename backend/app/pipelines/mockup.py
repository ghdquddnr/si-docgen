"""화면 목업 파이프라인: 화면 JSON → 고정 HTML 템플릿 → Playwright 캡처 PNG.

Phase 0 에서는 LLM 을 사용하지 않고 고정 템플릿(backend/templates/mockup.html.j2)에
값만 주입한다. 목업의 번호 오버레이(①②③…)는 항목 정의 표의 번호와 1:1 대응한다.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from app.renderers.pptx_renderer import circled_number
from app.schemas.screen_spec import Screen, ScreenSpecDocument

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
MOCKUP_TEMPLATE = "mockup.html.j2"

# 캡처 뷰포트 — 템플릿 목업 영역(7.0 x 5.4 inch)과 동일한 비율
VIEWPORT_WIDTH = 1120
VIEWPORT_HEIGHT = 864


def build_mockup_html(screen: Screen) -> str:
    """화면 정의 1건을 고정 HTML 템플릿에 주입해 목업 HTML 을 생성한다 (LLM 미사용)."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template(MOCKUP_TEMPLATE)
    fields = [
        {
            "name": field.name,
            "field_type": field.field_type,
            "required": field.required,
            "badge": circled_number(field.no),
        }
        for field in screen.fields
    ]
    return template.render(
        screen_name=screen.screen_name, menu_path=screen.menu_path, fields=fields
    )


def generate_mockups(doc: ScreenSpecDocument, output_dir: Path) -> dict[str, Path]:
    """모든 화면의 목업 PNG 를 생성하고 {화면 ID: PNG 경로} 를 반환한다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
            device_scale_factor=2,  # 슬라이드 확대 시에도 선명하도록 2배 해상도로 캡처
        )
        for screen in doc.screens:
            page.set_content(build_mockup_html(screen), wait_until="load")
            png_path = output_dir / f"{screen.screen_id}.png"
            page.screenshot(path=str(png_path))
            results[screen.screen_id] = png_path
        browser.close()
    return results
