"""목업 HTML 생성 단위 테스트 (Playwright 캡처는 제외, 결정론적 HTML 생성만 검증)."""

import json
import re
from pathlib import Path

import pytest
from markupsafe import escape

from app.pipelines.mockup import build_mockup_html
from app.renderers.pptx_renderer import circled_number
from app.schemas import screen_spec as ss

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "golden" / "fixtures" / "screen_spec_5.json"


@pytest.fixture(scope="module")
def screens() -> list[ss.Screen]:
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return ss.ScreenSpecDocument.model_validate(raw).screens


def test_번호_오버레이가_항목_번호와_1대1_대응(screens: list[ss.Screen]) -> None:
    for screen in screens:
        html = build_mockup_html(screen)
        badges = re.findall(r'<span class="badge">(.+?)</span>', html)
        assert badges == [circled_number(f.no) for f in screen.fields], screen.screen_id


def test_화면명과_메뉴_경로_주입(screens: list[ss.Screen]) -> None:
    for screen in screens:
        html = build_mockup_html(screen)
        # autoescape 가 켜져 있어 '>' 등은 HTML 엔티티로 비교한다
        assert str(escape(screen.screen_name)) in html
        assert str(escape(screen.menu_path)) in html


def test_필수_항목_표시(screens: list[ss.Screen]) -> None:
    login = screens[0]
    html = build_mockup_html(login)
    required_count = html.count('<span class="req">')
    assert required_count == sum(1 for f in login.fields if f.required)


def test_원문자_변환_경계값() -> None:
    assert circled_number(1) == "①"
    assert circled_number(20) == "⑳"
    assert circled_number(21) == "21"


def test_항목_유형별_컨트롤_렌더링(screens: list[ss.Screen]) -> None:
    login_html = build_mockup_html(screens[0])  # 로그인: 텍스트/비밀번호/버튼/링크
    assert 'type="password"' in login_html
    assert "<button" in login_html
    assert 'class="link"' in login_html
    board_html = build_mockup_html(screens[2])  # 공지사항: 콤보/그리드
    assert "<select>" in board_html
    assert 'class="grid"' in board_html
