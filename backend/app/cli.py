"""si-docgen CLI 엔트리포인트.

사용 예:
  uv run si-docgen generate --input 요구사항.docx --output ./out
  uv run si-docgen generate --input req.md --output ./out --model ollama/gemma4:e4b
"""

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.exceptions import SiDocgenError
from app.onboarding import KIND_HEADERS, analyze_xlsx_template, format_report
from app.pipelines.generate_chain import ChainResult, generate_chain
from app.pipelines.generate_interface_spec import generate_and_render_interface_spec
from app.pipelines.generate_proposal import generate_and_render_proposal
from app.pipelines.generate_table_spec import generate_and_render_table_spec
from app.pipelines.generate_test_scenario import generate_test_scenario_and_rtm
from app.pipelines.generate_user_manual import generate_and_render_user_manual
from app.pipelines.generate_wbs import generate_and_render_wbs

logger = logging.getLogger("si_docgen")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="si-docgen", description="한국 SI 표준 산출물 생성기")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="원천 문서에서 테스트시나리오 + RTM 생성")
    gen.add_argument(
        "--input", required=True, type=Path, help="원천 문서 경로 (.docx/.pdf/.md/.txt)"
    )
    gen.add_argument("--output", required=True, type=Path, help="출력 디렉토리")
    gen.add_argument(
        "--model", default=None, help="LLM 모델 오버라이드 (LiteLLM 형식). 미지정 시 설정값"
    )
    gen.add_argument("--project-name", default="프로젝트", help="표지 프로젝트명")
    gen.add_argument("--system-name", default="시스템", help="표지 시스템명")
    gen.add_argument("--author", default="작성자", help="표지 작성자")
    gen.add_argument(
        "--date", default=date.today().isoformat(), help="표지 작성일 (YYYY-MM-DD, 기본: 오늘)"
    )
    gen.add_argument(
        "--with-screens",
        action="store_true",
        help="화면정의서(pptx)도 함께 생성하고 RTM 에 화면 ID 를 연결 (체인)",
    )
    gen.add_argument(
        "--with-requirements",
        action="store_true",
        help="요구사항정의서(docx)를 체인의 머리로 생성 — 확정 REQ ID 로 4종 연결",
    )
    gen.add_argument("--verbose", action="store_true", help="DEBUG 로그 출력 (프롬프트 본문 포함)")

    pro = sub.add_parser("proposal", help="RFP(제안요청서)에서 제안서(pptx) 초안 생성")
    pro.add_argument("--input", required=True, type=Path, help="RFP 경로 (.docx/.pdf/.md/.txt)")
    pro.add_argument("--output", required=True, type=Path, help="출력 디렉토리")
    pro.add_argument("--model", default=None, help="LLM 모델 오버라이드 (LiteLLM 형식)")
    pro.add_argument("--project-name", default="프로젝트", help="표지 사업명/프로젝트명")
    pro.add_argument("--system-name", default="시스템", help="표지 시스템명")
    pro.add_argument("--author", default="제안사", help="표지 제안사")
    pro.add_argument("--client", default="발주처", help="표지 발주처")
    pro.add_argument("--date", default=date.today().isoformat(), help="표지 제안 일자 (기본: 오늘)")
    pro.add_argument("--verbose", action="store_true", help="DEBUG 로그 출력")

    wbs = sub.add_parser("wbs", help="원천 문서에서 WBS(작업분해구조) 생성")
    wbs.add_argument("--input", required=True, type=Path, help="원천 문서 경로 (.docx/.pdf/.md)")
    wbs.add_argument("--output", required=True, type=Path, help="출력 디렉토리")
    wbs.add_argument("--model", default=None, help="LLM 모델 오버라이드 (LiteLLM 형식)")
    wbs.add_argument("--project-name", default="프로젝트", help="표지 프로젝트명")
    wbs.add_argument("--system-name", default="시스템", help="표지 시스템명")
    wbs.add_argument("--author", default="작성자", help="표지 작성자")
    wbs.add_argument("--date", default=date.today().isoformat(), help="표지 작성일 (기본: 오늘)")
    wbs.add_argument(
        "--start-date", default=date.today().isoformat(), help="프로젝트 시작일 (일정 계산 기준)"
    )
    wbs.add_argument("--verbose", action="store_true", help="DEBUG 로그 출력")

    tbl = sub.add_parser("table-spec", help="원천 문서에서 테이블정의서 생성")
    tbl.add_argument("--input", required=True, type=Path, help="원천 문서 경로 (.docx/.pdf/.md)")
    tbl.add_argument("--output", required=True, type=Path, help="출력 디렉토리")
    tbl.add_argument("--model", default=None, help="LLM 모델 오버라이드 (LiteLLM 형식)")
    tbl.add_argument("--project-name", default="프로젝트", help="표지 프로젝트명")
    tbl.add_argument("--system-name", default="시스템", help="표지 시스템명")
    tbl.add_argument("--author", default="작성자", help="표지 작성자")
    tbl.add_argument("--date", default=date.today().isoformat(), help="표지 작성일 (기본: 오늘)")
    tbl.add_argument("--verbose", action="store_true", help="DEBUG 로그 출력")

    itf = sub.add_parser("interface-spec", help="원천 문서에서 인터페이스정의서 생성")
    itf.add_argument("--input", required=True, type=Path, help="원천 문서 경로 (.docx/.pdf/.md)")
    itf.add_argument("--output", required=True, type=Path, help="출력 디렉토리")
    itf.add_argument("--model", default=None, help="LLM 모델 오버라이드 (LiteLLM 형식)")
    itf.add_argument("--project-name", default="프로젝트", help="표지 프로젝트명")
    itf.add_argument("--system-name", default="시스템", help="표지 시스템명")
    itf.add_argument("--author", default="작성자", help="표지 작성자")
    itf.add_argument("--date", default=date.today().isoformat(), help="표지 작성일 (기본: 오늘)")
    itf.add_argument("--verbose", action="store_true", help="DEBUG 로그 출력")

    man = sub.add_parser("user-manual", help="원천 문서에서 사용자 매뉴얼 생성 (캡처 없이 초안)")
    man.add_argument("--input", required=True, type=Path, help="원천 문서 경로 (.docx/.pdf/.md)")
    man.add_argument("--output", required=True, type=Path, help="출력 디렉토리")
    man.add_argument("--model", default=None, help="LLM 모델 오버라이드 (LiteLLM 형식)")
    man.add_argument("--project-name", default="프로젝트", help="표지 프로젝트명")
    man.add_argument("--system-name", default="시스템", help="표지 시스템명")
    man.add_argument("--author", default="작성자", help="표지 작성자")
    man.add_argument("--date", default=date.today().isoformat(), help="표지 작성일 (기본: 오늘)")
    man.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="화면 캡처 폴더. {screen_ref}.png 파일을 각 단계에 삽입 (예: SCR-001.png)",
    )
    man.add_argument("--verbose", action="store_true", help="DEBUG 로그 출력")

    ana = sub.add_parser(
        "analyze-template", help="고객사 엑셀 양식 분석 → 표지 셀·헤더·컬럼 위치 제안"
    )
    ana.add_argument("--input", required=True, type=Path, help="고객 양식 경로 (.xlsx)")
    ana.add_argument("--kind", required=True, choices=sorted(KIND_HEADERS), help="산출물 종류")
    ana.add_argument("--sheet", default=None, help="분석할 시트명 (기본: 첫 번째 시트)")
    return parser


def _run_generate(args: argparse.Namespace) -> int:
    if args.model:
        # 모델명은 설정 계층에서만 관리하므로, 환경 변수를 통해 주입하고 캐시를 무효화한다
        os.environ["SIDOCGEN_LLM_MODEL"] = args.model
        get_settings.cache_clear()
    logger.info("사용 모델: %s", get_settings().llm_model)

    cover = {
        "project_name": args.project_name,
        "system_name": args.system_name,
        "author": args.author,
        "written_date": args.date,
    }
    try:
        if args.with_requirements:
            result = generate_chain(args.input, args.output, with_requirements=True, **cover)
        elif args.with_screens:
            result = generate_chain(args.input, args.output, **cover)
        else:
            result = generate_test_scenario_and_rtm(args.input, args.output, **cover)
    except SiDocgenError as exc:
        logger.error("생성 실패: %s", exc)
        return 1

    print("\n생성 완료:")
    if isinstance(result, ChainResult) and result.requirement_spec_path is not None:
        print(f"  요구사항정의서: {result.requirement_spec_path}")
    print(f"  테스트시나리오: {result.test_scenario_path}")
    print(f"  요건추적표(RTM): {result.rtm_path}")
    if isinstance(result, ChainResult):
        print(f"  화면정의서: {result.screen_spec_path}")
    screen_part = f" / 화면 {result.screen_count}개" if isinstance(result, ChainResult) else ""
    print(
        f"  통계: 요건 {result.requirement_count}건 / "
        f"단위 {result.unit_count}건 + 통합 {result.integration_count}건{screen_part}"
    )
    return 0


def _run_proposal(args: argparse.Namespace) -> int:
    if args.model:
        os.environ["SIDOCGEN_LLM_MODEL"] = args.model
        get_settings.cache_clear()
    logger.info("사용 모델: %s", get_settings().llm_model)

    try:
        result = generate_and_render_proposal(
            args.input,
            args.output,
            project_name=args.project_name,
            system_name=args.system_name,
            author=args.author,
            client=args.client,
            written_date=args.date,
        )
    except SiDocgenError as exc:
        logger.error("생성 실패: %s", exc)
        return 1

    print("\n생성 완료:")
    print(f"  제안서: {result.proposal_path}")
    print(f"  통계: 내용 슬라이드 {result.slide_count}개 / 불릿 {result.bullet_count}개")
    print("  (표지·목차 슬라이드는 렌더러가 자동 생성)")
    return 0


def _run_wbs(args: argparse.Namespace) -> int:
    if args.model:
        os.environ["SIDOCGEN_LLM_MODEL"] = args.model
        get_settings.cache_clear()
    logger.info("사용 모델: %s", get_settings().llm_model)

    try:
        result = generate_and_render_wbs(
            args.input,
            args.output,
            project_name=args.project_name,
            system_name=args.system_name,
            author=args.author,
            written_date=args.date,
            start_date=args.start_date,
        )
    except SiDocgenError as exc:
        logger.error("생성 실패: %s", exc)
        return 1

    print("\n생성 완료:")
    print(f"  WBS: {result.wbs_path}")
    print(f"  통계: 전체 태스크 {result.total_count}개 / 작업(leaf) {result.leaf_count}개")
    return 0


def _run_table_spec(args: argparse.Namespace) -> int:
    if args.model:
        os.environ["SIDOCGEN_LLM_MODEL"] = args.model
        get_settings.cache_clear()
    logger.info("사용 모델: %s", get_settings().llm_model)

    try:
        result = generate_and_render_table_spec(
            args.input,
            args.output,
            project_name=args.project_name,
            system_name=args.system_name,
            author=args.author,
            written_date=args.date,
        )
    except SiDocgenError as exc:
        logger.error("생성 실패: %s", exc)
        return 1

    print("\n생성 완료:")
    print(f"  테이블정의서: {result.table_spec_path}")
    print(f"  통계: 테이블 {result.table_count}개 / 컬럼 {result.column_count}개")
    return 0


def _run_interface_spec(args: argparse.Namespace) -> int:
    if args.model:
        os.environ["SIDOCGEN_LLM_MODEL"] = args.model
        get_settings.cache_clear()
    logger.info("사용 모델: %s", get_settings().llm_model)

    try:
        result = generate_and_render_interface_spec(
            args.input,
            args.output,
            project_name=args.project_name,
            system_name=args.system_name,
            author=args.author,
            written_date=args.date,
        )
    except SiDocgenError as exc:
        logger.error("생성 실패: %s", exc)
        return 1

    print("\n생성 완료:")
    print(f"  인터페이스정의서: {result.interface_spec_path}")
    print(f"  통계: 인터페이스 {result.interface_count}개 / 항목 {result.field_count}개")
    return 0


def _run_user_manual(args: argparse.Namespace) -> int:
    if args.model:
        os.environ["SIDOCGEN_LLM_MODEL"] = args.model
        get_settings.cache_clear()
    logger.info("사용 모델: %s", get_settings().llm_model)

    try:
        result = generate_and_render_user_manual(
            args.input,
            args.output,
            project_name=args.project_name,
            system_name=args.system_name,
            author=args.author,
            written_date=args.date,
            images_dir=args.images_dir,
        )
    except SiDocgenError as exc:
        logger.error("생성 실패: %s", exc)
        return 1

    print("\n생성 완료:")
    print(f"  사용자 매뉴얼: {result.user_manual_path}")
    print(f"  통계: 섹션 {result.section_count}개 / 단계 {result.step_count}개")
    if result.image_count:
        print(f"  삽입된 화면 캡처: {result.image_count}개 (나머지 화면 자리는 플레이스홀더)")
    else:
        print("  ※ 화면 캡처 미삽입 (--images-dir 로 {screen_ref}.png 제공 시 삽입).")
    return 0


def _run_analyze_template(args: argparse.Namespace) -> int:
    try:
        analysis = analyze_xlsx_template(args.input, args.kind, sheet_name=args.sheet)
    except SiDocgenError as exc:
        logger.error("분석 실패: %s", exc)
        return 1
    print(format_report(analysis))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점. 종료 코드를 반환한다 (0=성공, 1=도메인 오류)."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if args.command == "generate":
        return _run_generate(args)
    if args.command == "proposal":
        return _run_proposal(args)
    if args.command == "wbs":
        return _run_wbs(args)
    if args.command == "table-spec":
        return _run_table_spec(args)
    if args.command == "interface-spec":
        return _run_interface_spec(args)
    if args.command == "user-manual":
        return _run_user_manual(args)
    if args.command == "analyze-template":
        return _run_analyze_template(args)
    return 2  # argparse 가 required subcommand 를 강제하므로 도달하지 않음


if __name__ == "__main__":
    sys.exit(main())
