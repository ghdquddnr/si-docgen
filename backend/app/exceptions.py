"""si-docgen 공통 커스텀 예외 계층.

모든 도메인 예외는 SiDocgenError 를 상속한다.
"""


class SiDocgenError(Exception):
    """si-docgen 커스텀 예외의 공통 기반 클래스."""


class ValidationFailedError(SiDocgenError):
    """LLM 출력이 Pydantic 스키마 검증을 재시도 한도까지 통과하지 못했을 때 발생."""


class RenderError(SiDocgenError):
    """산출물 렌더링 오류 (템플릿 파일 누락, 시트/플레이스홀더 구조 불일치 등)."""


class SourceParseError(SiDocgenError):
    """원천 문서 파싱 오류 (미지원 형식, 손상된 파일 등)."""


class LLMError(SiDocgenError):
    """LLM 호출 계층 오류 (타임아웃, 응답 형식 오류, 벤더 API 오류 등)."""
