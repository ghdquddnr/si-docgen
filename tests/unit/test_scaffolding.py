"""P0-1 스캐폴딩 검증용 최소 테스트.

pytest가 테스트 0건이면 종료 코드 5를 반환하므로,
파이프라인 통과를 위한 최소 1건의 테스트를 유지한다.
"""

import app


def test_app_package_importable() -> None:
    """backend/app 패키지가 pythonpath 설정으로 임포트 가능한지 확인한다."""
    assert app is not None
