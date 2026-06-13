# TASKS.md — si-docgen 작업 관리

> **운영 규칙**
> - 모든 세션은 이 파일을 읽는 것으로 시작한다.
> - 상태 표기: `[ ]` 대기 / `[~]` 진행 중 / `[x]` 완료 / `[!]` 차단됨(사유 필수)
> - 태스크 완료 조건: 완료 기준(AC) 충족 + 테스트 통과 + 커밋 완료. 셋 중 하나라도 빠지면 완료로 표시하지 않는다.
> - 태스크를 완료하면 해당 태스크 아래 `메모:` 줄에 다음 세션이 알아야 할 특이사항을 1~2줄로 남긴다.
> - 진행 중(`[~]`) 태스크는 항상 1개만 유지한다.

---

## 현재 상태

- **현재 Phase**: Phase 1 완료 (2026-06-14 검수 합격) → 다음 Phase 2 착수 대기
- **진행 중 태스크**: 없음 (다음: Phase 2 분해 — 착수 시 사용자와 범위 확정)
- **차단 사항**: 없음.

---

## Phase 0 — 렌더러 PoC (목표: 양식 충실도 검증)

**Phase 목표**: 양식 3종을 하드코딩 JSON으로 채워서 "발주처 제출 가능 수준"의 파일이 나오는지 검증한다.
LLM 호출은 이 Phase에 포함되지 않는다. 품질이 안 나오면 이후 Phase는 무의미하므로 여기서 기술 리스크를 전부 제거한다.

### P0-1. 프로젝트 스캐폴딩
- [x] 디렉토리 구조 생성 (CLAUDE.md의 구조 그대로), uv 초기화, ruff/pytest 설정
- **AC**: `uv run pytest` 가 빈 테스트로 통과하고, `uv run ruff check` 가 통과한다.
- 메모: uv 프로젝트 루트는 저장소 루트(pyproject.toml), pytest `pythonpath=["backend"]` 설정으로 테스트에서 `import app.…` 사용. git 저장소 신규 init(main 브랜치). 렌더링 라이브러리(openpyxl 등)는 각 렌더러 태스크에서 `uv add`로 추가할 것.

### P0-2. 테스트시나리오 엑셀 양식 제작
- [x] 전형적인 한국 SI 단위테스트 시나리오 양식을 `backend/templates/test_scenario.xlsx` 로 직접 제작
- 포함 요소: 표지 정보 영역(프로젝트명/시스템명/작성자/작성일), 결재란(셀 병합), 데이터 헤더 행(TC ID/연관 요건 ID/대분류/중분류/시나리오명/사전조건/테스트 절차/기대 결과/결과/비고), 서식 기준 행 1개(테두리/폰트/정렬 완성 상태)
- **AC**: 양식 파일을 열었을 때 실무에서 쓰던 단위테스트 시나리오와 구분되지 않는 수준. 단위/통합 시트 분리.
- 메모: 제작 스크립트 `scripts/templates/build_test_scenario_template.py` 로 재현 가능. 헤더 8행, 서식 기준 행 9행(렌더러는 이 행 서식 복제). 시각 품질 최종 판정은 P0-10 사람 게이트에서 수행할 것.

### P0-3. 엑셀 렌더러 구현
- [x] `backend/app/schemas/test_scenario.py` — Pydantic 모델 (모든 필드에 한국어 description)
- [x] `backend/app/renderers/xlsx_renderer.py` — 템플릿 로드 → 서식 기준 행 복제 → 값 주입 → 저장
- **AC**: 테스트케이스 30건짜리 픽스처 JSON으로 생성한 파일에서 ① 서식 기준 행의 테두리/정렬이 전체 행에 복제됨 ② 결재란/표지 영역 훼손 없음 ③ 행 수 가변(1건, 30건, 200건) 모두 정상.
- 메모: AC 3건 모두 검증 통과(1/30/200건). 픽스처는 `tests/golden/fixtures/test_scenario_30.json`(단위 30건+통합 5건)으로 P0-4에서 재사용. `app/exceptions.py` 커스텀 예외 계층도 이 태스크에서 신설.

### P0-4. 엑셀 골든 파일 테스트
- [x] `tests/golden/test_xlsx_renderer.py` — 고정 JSON 입력 → 생성 파일의 셀 값을 openpyxl로 추출해 기대값과 비교
- **AC**: 셀 값 비교 + 병합 영역 보존 검증 + 행 수 검증이 자동화됨. 바이너리 비교 사용 금지.
- 메모: 골든 테스트(셀 값 전체/병합/행 수/라벨/서식 복제) + 스키마 경계값 테스트(`tests/unit/test_test_scenario_schema.py`)까지 포함, 총 33건. Pydantic 모델명이 Test* 라서 테스트에서는 모듈 임포트(`ts.TestCase`)로 pytest 오인 수집 방지.

### P0-5. 요구사항정의서 워드 양식 제작 + 렌더러
- [x] `backend/templates/requirement_spec.docx` 제작 — 표지/개정 이력 표/요건 목록 표/요건 상세 섹션(반복 블록) 구조, docxtpl(Jinja) 태그 삽입
- [x] `backend/app/schemas/requirement_spec.py` + `backend/app/renderers/docx_renderer.py`
- **AC**: 요건 15건 픽스처로 생성 시 ① 요건 상세 섹션이 요건 수만큼 반복 생성 ② 표 동적 행 정상 ③ 머리글/바닥글의 문서번호·페이지 유지.
- 메모: 제작 스크립트 `scripts/templates/build_requirement_spec_template.py`. 행 반복은 `{%tr%}`, 상세 섹션 반복은 `{%p for %}` 태그 사용. 픽스처 `tests/golden/fixtures/requirement_spec_15.json`. AC 3건 검증 통과 (상세 15개 반복·표 행 수·머리글 문서번호 치환·바닥글 PAGE 필드).

### P0-6. 워드 골든 파일 테스트
- [x] python-docx로 텍스트/표 내용 추출 비교 방식
- **AC**: 요건 ID 목록, 표 행 수, 섹션 제목이 기대값과 일치함을 자동 검증.
- 메모: `tests/golden/test_docx_renderer.py` (섹션 제목/상세 반복/표 행·ID/표지 치환/잔여 태그/머리글·바닥글) + 스키마 경계값 테스트. 전체 55건 통과.

### P0-7. 화면정의서 PPT 양식 제작
- [x] `backend/templates/screen_spec.pptx` 제작 — 표지 슬라이드 + "화면정의 표준 슬라이드" 1장(화면 ID/화면명/메뉴 경로 텍스트 프레임, 목업 이미지 영역, 항목 정의 표 5열)
- **AC**: 표준 슬라이드의 각 요소에 코드에서 식별 가능한 이름(shape name) 부여 완료.
- 메모: 제작 스크립트 `scripts/templates/build_screen_spec_template.py`. shape name 규약: 표지 `cover_*`, 표준 슬라이드 `slide_title`/`screen_id`/`screen_name`/`menu_path`/`mockup_area`/`field_table`/`logic_text`. 16:9, 표는 Table Grid 스타일 + 헤더·서식 기준 행 1개.

### P0-8. PPT 렌더러 — 슬라이드 복제 + 텍스트/표 주입
- [x] `backend/app/renderers/pptx_renderer.py` — 표준 슬라이드 XML 레벨 복제 유틸 → 화면 수만큼 복제 → shape name 기반 텍스트/표 주입
- **AC**: 화면 5개 픽스처로 슬라이드 5장 생성, 레이아웃 깨짐 없음. PowerPoint와 LibreOffice 양쪽에서 열림 확인.
- 메모: 스키마 `screen_spec.py`(SCR ID 패턴, 항목 번호 1~20) + 픽스처 `screen_spec_5.json`. 복제 슬라이드의 shape 위치/크기가 템플릿과 동일함을 검증. ⚠️ 이 PC에 LibreOffice 미설치 — PowerPoint/LibreOffice 실제 열림 확인은 P0-10 사람 게이트에서 수행 필요.

### P0-9. 목업 파이프라인 — HTML → PNG → 슬라이드 삽입
- [x] 화면 JSON → HTML 목업 생성(이 Phase에서는 고정 HTML 템플릿 + 값 주입, LLM 미사용) → Playwright 캡처 → PNG를 목업 영역에 삽입
- [x] 목업의 입력 필드에 ①②③ 번호 오버레이, 항목 정의 표의 번호와 일치
- **AC**: 목업 이미지의 번호와 하단 표의 번호가 1:1 대응. 이미지가 목업 영역 비율에 맞게 삽입됨.
- 메모: HTML 템플릿 `backend/templates/mockup.html.j2` + 파이프라인 `app/pipelines/mockup.py`(뷰포트 1120×864 = 목업 영역 비율, 2배 해상도 캡처). `render_screen_spec` 에 `mockup_images` 매개변수 추가(contain-fit 가운데 삽입). 캡처 테스트는 브라우저 의존이라 미포함 — HTML 생성만 단위 테스트. Chromium은 `uv run playwright install chromium` 필요.

### P0-10. Phase 0 품질 검수 (사람 게이트)
- [x] 산출물 3종을 직접 열어 "발주처 제출 가능 수준" 여부 판정. 미달 항목은 태스크로 환원하여 이 섹션에 추가
- **AC**: 3종 모두 합격 판정. 판정 결과와 개선 필요 사항을 메모에 기록.
- 메모: 2026-06-13 사용자 검수 — **3종 모두 합격**, 개선 요구 사항 없음. 검수 샘플은 `out/review/` 에서 생성했음(재생성 가능). Phase 0 종료.

---

## Phase 1 — 단일 파이프라인

**Phase 목표**: 원천 문서(요구사항정의서 등) 1개를 입력하면 CLI 로 테스트시나리오 + RTM 엑셀을 출력한다.
LLM 호출이 처음 들어가는 Phase 이므로, "LLM은 JSON만 생성 + Pydantic 검증 + 3회 재시도" 원칙을 여기서 코드로 고정한다.

> **착수 전 결정 필요 사항** (P1-1 시작 시 사용자 확인):
> 1. 기본 사용 모델/벤더 (예: claude-sonnet-4-6, gpt 계열, 로컬 모델) 및 API 키 확보
> 2. 신규 의존성 승인: `litellm`(스택 명시됨), `pydantic-settings`(설정 관리), `pypdf`(PDF 파싱)

### P1-1. LiteLLM 래퍼 + 검증-재시도 루프
- [x] `backend/app/config.py` — 모델명/타임아웃/재시도 횟수 설정 (환경 변수 + `.env`, 모델명은 설정에서만 관리)
- [x] `backend/app/llm/client.py` — LiteLLM 기반 JSON 모드 호출 래퍼. 모델명·토큰 수·소요 시간 INFO 로깅, 프롬프트 본문은 DEBUG
- [x] `backend/app/llm/generate.py` — `generate_validated(prompt, schema_cls) -> BaseModel`: JSON 파싱 → Pydantic 검증 → 실패 시 오류 내용을 포함해 최대 3회 재시도 → 최종 실패 시 `ValidationFailedError`
- **AC**: LLM 모킹 테스트로 ① 1~2회 실패 후 재시도 성공 ② 3회 실패 시 예외 발생 ③ 미검증 데이터가 절대 반환되지 않음을 검증. 실제 API 호출 테스트는 작성하지 않는다.
- 메모: 기본 모델 `ollama/gemma4:e4b`(사용자 결정, 임시), `.env.example` 참조. 설정 접두사 `SIDOCGEN_`. litellm 은 임포트가 무거워 호출 시점 지연 임포트 처리(테스트 속도 24s→1.4s). 실제 Ollama 호출 확인은 P1-3 평가 스크립트에서.

### P1-2. 원천 문서 파서
- [x] `backend/app/pipelines/source_loader.py` — 입력 파일 확장자별 텍스트 추출: `.docx`(python-docx, 표 내용 포함), `.md`/`.txt`(plain), `.pdf`(pypdf)
- [x] 추출 결과는 `SourceDocument(filename, text, tables)` 형태의 단순 모델로 통일
- **AC**: 픽스처 원천 문서(docx/md/pdf 각 1개, `tests/fixtures/sources/`)에서 본문과 표 텍스트가 추출됨을 단위 테스트로 검증. 미지원 확장자는 명확한 예외.
- 메모: `SourceParseError` 예외 신설. 표 추출은 docx 만 지원(pdf 표는 텍스트로 평탄화됨). 픽스처 pdf 는 Chromium 인쇄로 생성.

### P1-3. 테스트시나리오 생성 프롬프트 + 평가 스크립트
- [x] `backend/app/llm/prompts.py` — 테스트시나리오 생성 프롬프트 템플릿. 스키마 필드의 한국어 description 을 자동 포함해 출력 형식을 지시
- [x] `scripts/eval/eval_test_scenario.py` — 실제 LLM 을 호출해 ① 검증 통과율(재시도 포함) ② TC/REQ ID 형식 적합성 ③ 생성 건수 분포를 리포트
- **AC**: 평가 스크립트가 샘플 원천 문서로 end-to-end 생성 리포트를 출력한다. 프롬프트는 코드와 분리된 상수/템플릿으로 관리된다.
- 메모: **2026-06-13 gemma4:e4b 로 평가 3/3 통과** (단위 5~7 + 통합 1건, 회당 83~98s, TC ID 중복 없음, 원천 외 요건 ID 참조 없음). 블로커 원인 2가지 해소: ① 12b 타임아웃 → e4b(경량)로 전환, `.env`/`.env.example` 기본 모델을 e4b 로 변경, 타임아웃 300s. ② e4b 가 구조화 출력 지시에도 응답을 ```json 펜스로 감싸 char-0 파싱 실패 → `generate.py` 에 `_strip_code_fence()` 추가(봉투만 제거, 데이터는 그대로 json.loads+Pydantic 검증 — 정규식 데이터 추출 아님). 상용 모델 전환 시 펜스 처리는 무해하게 그대로 통과.

### P1-4. RTM 스키마/렌더러 + ID 정합성 검증
- [x] `backend/templates/rtm.xlsx` 양식 제작 (제작 스크립트 `scripts/templates/build_rtm_template.py`) — 요건 ID/요건명/화면 ID/프로그램 ID/TC ID/단계별 반영 여부, 서식 기준 행 방식은 P0-3 과 동일
- [x] `backend/app/schemas/rtm.py` + `backend/app/renderers/rtm_renderer.py`
- [x] 테스트시나리오와 동시 생성 시 정합성 검증: RTM 의 TC ID ⊆ 테스트시나리오 TC ID, 요건 ID 상호 일치. 불일치 시 `ValidationFailedError`
- **AC**: 골든 파일 테스트 + 존재하지 않는 TC/REQ ID 참조 픽스처가 검증에서 거부됨을 테스트로 확인.
- 메모: 템플릿은 9열(앞 5열 + '단계별 반영 여부' 그룹 헤더 아래 분석/설계/구현/시험 4열). 헤더는 2행(8~9행) 구성이라 **STYLE_ROW=10**(test_scenario 는 9). 표지/결재란 셀 배치는 test_scenario 와 동일(B5/G5/B6/G6). 정합성 검증 `validate_rtm_consistency(rtm, scenario)` 는 schemas/rtm.py 에 위치 — ① RTM TC ID ⊆ 시나리오 TC(유령 TC 참조 거부) ② 시나리오 요건 ID ⊆ RTM 요건(추적 완전성). RTM 에 TC 미작성 요건이 있어도 통과(단방향). 스키마는 요건 ID 중복 거부 + 리스트 항목 ID 형식(SCR/TC) 제약. 픽스처 `tests/golden/fixtures/rtm_10.json`. 테스트 총 105건 통과(렌더러 골든 8 + 스키마 경계 11 + 정합성 4 신규). 다단 헤더 셀은 `get_column_letter` 사용(병합셀 .column_letter 미지원).

### P1-5. CLI 엔트리포인트
- [x] `backend/app/cli.py` + pyproject `[project.scripts]` — `si-docgen generate --input 요구사항.docx --output ./out [--model ...]`
- [x] 파이프라인 오케스트레이션 `backend/app/pipelines/generate_test_scenario.py`: 원천 파서 → LLM 생성(P1-1 루프) → 테스트시나리오 + RTM 렌더링 → 출력 경로 반환
- [x] 진행 상황과 실패 사유를 사람이 읽을 수 있게 stdout/로그로 출력
- **AC**: LLM 을 모킹한 e2e 테스트로 입력 docx → xlsx 2종 출력 흐름이 통과. 실제 모델 호출 확인은 P1-3 평가 스크립트로 수행.
- 메모: **RTM 은 별도 LLM 호출 없이 시나리오에서 결정론적 파생**(`build_rtm_from_scenario`, schemas/rtm.py) — 사용자 결정(1번 방식). 구성상 ID 정합성 자동 보장, 파이프라인에서 `validate_rtm_consistency` 로 방어적 재확인. **패키징**: `[build-system]=hatchling` + `[project.scripts] si-docgen=app.cli:main` 신규 추가(사용자 승인), `[tool.hatch.build.targets.wheel] packages=["backend/app"]`. `uv sync` 로 콘솔 스크립트 설치됨 → `uv run si-docgen generate ...`. e2e 테스트(LLM 모킹) `tests/unit/test_generate_pipeline.py` 5건 — 파이프라인 직접 호출 + CLI main() 종료코드(성공 0 / 미지원입력 1) 검증. 실모델 스모크(gemma4:e4b, sample md): 단위 7+통합 2, RTM 요건 3건 정상 생성 확인. **한계(P1-6 검토)**: 요건명을 시나리오 '대분류-중분류'로 대체(원천 정식 요건명 미사용), 화면/프로그램 ID 비움, 단계 반영은 분석·시험만 True. 전체 110건 통과.

### P1-6. Phase 1 품질 검수 (사람 게이트)
- [x] 실제 원천 문서 1건으로 CLI 실행 → 생성된 테스트시나리오/RTM 의 내용 품질·ID 정합성 판정
- **AC**: 생성물이 "검수 후 제출 가능" 수준인지 판정하고, 프롬프트/스키마 개선 항목을 태스크로 환원.
- 메모: **2026-06-14 사용자 검수 — 합격** ("문서 확인해 보니 잘 나왔다"). gemma4:e4b 생성물(테스트시나리오 + RTM) 품질·정합성 양호. 추가 개선 요구 없음. Phase 1 종료. P1-5 메모에 적은 RTM 한계 3건(요건명 대체/화면·프로그램 ID 공백/단계 반영 분석·시험만)은 현 시점 차단 요인 아님 — Phase 3(다중 산출물 체이닝·화면정의서 연계) 착수 시 자연 해소 대상.

---

## Phase 2 — 웹화 (FastAPI + Next.js)

**Phase 목표**: CLI 흐름(원천 문서 → 테스트시나리오 + RTM)을 웹으로 제공한다.
업로드 → 백그라운드 생성(진행 상태 SSE) → JSON 검수 화면(표 편집 → 재검증) → 재렌더링 → 다운로드.

> **착수 결정사항 (2026-06-14 사용자 확정)**:
> 1. 시작 순서: **백엔드 API 먼저**(P2-1~5), 이후 Next.js 프론트(P2-6~7).
> 2. 상태 저장: **SQLite 로 시작하되 SQLAlchemy 2.0 + Alembic 으로 추상화** — DB URL 만 바꾸면
>    PostgreSQL/MySQL 로 전환 가능하게. 인메모리 아님(잡/검수 상태 영속화).
> 3. 신규 의존성: `fastapi`, `uvicorn[standard]`, `python-multipart`, `sqlalchemy`, `alembic`,
>    (SSE 단계에서 `sse-starlette`), dev: `httpx`(TestClient).

### P2-1. 백엔드 API 스캐폴딩 + DB 계층
- [x] 신규 의존성 추가, `config.py` 에 `database_url`(기본 `sqlite:///./data/si_docgen.db`) 추가
- [x] `backend/app/db/` — Declarative Base, 엔진/세션(`get_db` 의존성), `Job` 모델(상태/입력파일/표지정보/scenario_json/오류/타임스탬프)
- [x] Alembic 셋업(`alembic.ini` + `env.py` 가 설정의 DB URL·Base.metadata 사용) + 초기 마이그레이션
- [x] `backend/app/api/main.py` — FastAPI 앱 + 헬스체크 라우터
- **AC**: FastAPI TestClient 로 `GET /health` 200, `Job` 모델 CRUD 단위 테스트 통과(임시 sqlite). `alembic upgrade head` 로 스키마 생성됨.
- 메모: DB URL 은 `app.config` 단일 관리, **alembic.ini 에 URL 미기재**(env.py 가 설정에서 주입). `alembic.ini` 는 **ASCII 전용**(Windows cp949 로캘이 ini 를 로캘 인코딩으로 읽어 한글 주석 시 UnicodeDecodeError). 마이그레이션은 `render_as_batch=True`(SQLite ALTER 제약 우회) + `JobStatus` 는 `native_enum=False`(VARCHAR 저장)로 **PostgreSQL/MySQL 이식성 확보**. `JobStatus` 는 `StrEnum`(py312), DB 에는 멤버명(PENDING 등) 저장. 엔진은 `session.py` 에 모듈 전역 + `rebind_engine()`(테스트 임시 DB 주입용). 자동생성 마이그레이션(`versions/`)은 ruff `extend-exclude`. 전체 114건 통과. 서버 실행: `uv run uvicorn app.api.main:app --reload`.

### P2-2. 업로드 → 생성 잡 엔드포인트
- [x] `POST /jobs` (multipart 업로드 + 표지 정보) → 잡 생성 → 백그라운드로 파이프라인 실행 → 잡 ID 반환
- [x] 생성 파이프라인을 잡 상태(대기/진행/완료/실패)와 연동, 결과 JSON·오류를 DB 에 저장
- **AC**: LLM 모킹 e2e 로 업로드 → 잡 완료 → DB 에 scenario_json 저장 확인.
- 메모: 파이프라인을 **`generate_scenario`(JSON 까지)** 와 **`render_scenario_and_rtm`(렌더링)** 으로 분리 — 웹은 생성 후 JSON 만 저장하고 렌더링은 검수 후(P2-5). 서비스 `app/services/job_service.py`: `create_job`(파일 저장 `data/jobs/{id}/source<ext>` + Job 행) / `run_job`(자체 `SessionLocal` 세션으로 백그라운드 실행, 모든 예외를 잡 상태 failed+error 로 기록). `storage_dir` 설정 추가. 빈 작성일은 오늘로 보정(미보정 시 LLM 이 written_date="" 출력→검증 실패). 미지원 확장자는 `UnsupportedSourceError`→400, 미존재 잡 404. FastAPI 파라미터는 `Annotated[...,File()/Form()/Depends()]` 스타일(ruff B008 회피). TestClient 는 BackgroundTasks 를 응답 후 동기 실행 → POST 직후 완료 검증 가능. 4건 추가(총 118건).

### P2-3. SSE 진행 상태 스트림
- [x] `GET /jobs/{id}/events` — 잡 진행 단계(파싱/LLM 생성/렌더링/완료)를 SSE 로 푸시
- **AC**: 잡 진행에 따라 이벤트가 순서대로 전달되고 완료 시 종료됨을 테스트로 확인.
- 메모: `sse-starlette` 의 `EventSourceResponse`. 백그라운드 워커와 메모리 공유 없이 **DB 폴링**으로 상태 전파(멀티프로세스 안전). `Job.progress`(String(32)) 컬럼 신설 + 마이그레이션, `generate_scenario(on_progress=...)` 콜백으로 parsing→generating 단계 통지, `run_job` 이 각 단계에서 progress 갱신·commit. 폴링 간격 설정 `sse_poll_interval`(테스트 0). 스냅샷 변경 시에만 emit, terminal 상태에서 스트림 종료. 테스트: 진행 순서(read_job_state 스크립트 대체)·완료 종료·없는 잡 에러 3건. 총 121건.

### P2-4. 결과 조회 + JSON 검수(편집)
- [x] `GET /jobs/{id}/scenario` 생성 JSON 반환, `PUT /jobs/{id}/scenario` 편집본을 Pydantic 재검증(+RTM 정합성)
- **AC**: 잘못된 편집본(스키마 위반/ID 불일치)이 422 로 거부되고, 유효 편집본은 저장됨.
- 메모: `GET /jobs/{id}`=상태(JobOut), `GET /jobs/{id}/scenario`=시나리오 JSON(미생성 시 409), `PUT /jobs/{id}/scenario`=편집본. PUT 본문을 `TestScenarioDocument` 로 선언 → FastAPI 가 자동 검증, 스키마 위반·TC ID 중복은 **422**. RTM 정합성은 시나리오에서 파생되므로 구조적 보장(별도 교차검증 불필요). **`TestScenarioDocument` 에 TC ID 유일성 model_validator 신설**(절대 원칙 6 강화) — 단위·통합 전체에서 중복 금지. 없는 잡 404. 테스트 7건(조회/409/유효저장/중복422/형식422/404 + 스키마 경계). 총 128건.

### P2-5. 재렌더링 + 다운로드
- [x] `POST /jobs/{id}/render` 검증된 JSON 으로 xlsx 2종 재렌더링, `GET /jobs/{id}/download/{kind}` 파일 다운로드
- **AC**: 편집 → 재렌더링 → 다운로드 흐름이 e2e 테스트로 통과.
- 메모: `render_job_outputs(job_id, scenario_json)` → `output_dir = data/jobs/{id}/output`. POST /render 동기 처리(LLM 미사용, 빠름), 시나리오 미생성 시 409. `download/{kind}`(kind: test_scenario|rtm), 미렌더링 시 409, 알수없는 종류 404, `FileResponse`+xlsx media type. 테스트 5건: 렌더링→다운로드(xlsx 유효성 openpyxl 검증)/렌더링 전 409/알수없는 종류 404/**편집→재렌더링 반영 확인**/없는 잡 404. 총 133건. **→ P2 백엔드(API) 완료.**

### P2-6. Next.js 프론트 골격 + 업로드 화면
- [ ] `frontend/` Next.js(App Router)+TS+Tailwind 스캐폴딩, `lib/api.ts` 타입 클라이언트, 업로드 페이지
- **AC**: 업로드 → 잡 생성 → 진행 상태 표시까지 동작.
- 메모:

### P2-7. 프론트 검수 화면
- [ ] 생성 JSON 표 편집 UI → 재검증 → 재렌더링 → 다운로드
- **AC**: 편집·재렌더링·다운로드가 브라우저에서 동작.
- 메모:

### P2-8. Phase 2 통합 검수 (사람 게이트)
- [ ] 업로드~다운로드 전 과정을 실제로 수행해 판정.
- **AC**: 전 흐름 합격 판정, 개선 항목 환원.
- 메모:

---

## Phase 3~4 — 개요만 유지 (착수 전 분해 금지)

- **Phase 3**: 다중 산출물 체이닝(요구사항 → 화면정의서 → 테스트시나리오) + ID 추적성 + 로컬/상용 모델 전환
- **Phase 4**: React Flow 노드 캔버스 UI

---

## 백로그 (Phase 미배정)

- [ ] 양식 온보딩 반자동화: 고객사 양식 분석 → 플레이스홀더 위치 제안 도구
- [ ] HWP(hwpx) 출력 지원 검토
- [ ] WBS 산출물 (계층 번호·일정 계산 로직 포함)
- [ ] 인터페이스정의서, 테이블정의서 산출물 추가

---

## 의사결정 기록 (ADR 요약)

| 날짜 | 결정 | 사유 |
|---|---|---|
| 2026-06-13 | LLM은 JSON만 생성, 렌더링은 결정론적 코드 | 양식 충실도를 LLM 능력과 분리 |
| 2026-06-13 | 템플릿 보존 + 값 주입 방식 (코드로 서식 재생성 금지) | 고객사 양식 100% 보존 |
| 2026-06-13 | PPT 목업은 HTML → Playwright 캡처 → PNG 삽입 | LLM의 HTML 생성 품질 > PPT 도형 조작 품질 |
| 2026-06-13 | 개발 도구는 Claude Code 단일 사용 | 컨텍스트 일관성, 도구 교체 오버헤드 제거 |
| 2026-06-14 | 기본 LLM 모델 ollama/gemma4:e4b | 12b 는 구조화 출력 추론이 너무 느림(타임아웃). e4b 로 평가 3/3 통과 |
| 2026-06-14 | RTM 은 시나리오에서 결정론적 파생(LLM 미사용) | ID 정합성 자동 보장, 별도 프롬프트·평가 불필요 |
