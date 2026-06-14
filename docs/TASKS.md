# TASKS.md — si-docgen 작업 관리

> **운영 규칙**
> - 모든 세션은 이 파일을 읽는 것으로 시작한다.
> - 상태 표기: `[ ]` 대기 / `[~]` 진행 중 / `[x]` 완료 / `[!]` 차단됨(사유 필수)
> - 태스크 완료 조건: 완료 기준(AC) 충족 + 테스트 통과 + 커밋 완료. 셋 중 하나라도 빠지면 완료로 표시하지 않는다.
> - 태스크를 완료하면 해당 태스크 아래 `메모:` 줄에 다음 세션이 알아야 할 특이사항을 1~2줄로 남긴다.
> - 진행 중(`[~]`) 태스크는 항상 1개만 유지한다.

---

## 현재 상태

- **현재 Phase**: 로드맵(Phase 0~4) 완료. **백로그 — B1~B5 완료, B6(사용자 매뉴얼) 렌더러 PoC 완료**.
- **진행 중 태스크**: 없음 (B6-1 렌더러 PoC 완료. 다음: 양식 사람 검수 → 합격 시 LLM 생성, 이후 캡처(Playwright)).
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
- [x] `frontend/` Next.js(App Router)+TS+Tailwind 스캐폴딩, `lib/api.ts` 타입 클라이언트, 업로드 페이지
- **AC**: 업로드 → 잡 생성 → 진행 상태 표시까지 동작.
- 메모: **Next 16**(Turbopack) + React 19 + Tailwind 4. pnpm 은 PATH 설치 권한(EPERM) 막혀 **corepack 경유**(`corepack pnpm -C frontend ...`). pnpm 11 네이티브 빌드 차단 → `frontend/pnpm-workspace.yaml` 의 `allowBuilds: {sharp:false, unrs-resolver:false}` 로 설치 exit 0. `lib/api.ts` 타입 클라이언트(createJob/getJob/getScenario/putScenario/renderJob/eventsUrl/downloadUrl, `ApiError`). `app/page.tsx`: 업로드 폼 + `EventSource` 로 SSE 진행 표시, 완료 시 `/jobs/{id}`(P2-7) 링크. 백엔드에 **CORS 미들웨어**(`cors_origins` 설정, 기본 localhost:3000) 추가. `lint`/`build`(타입체크 포함) 통과. API 기본 URL `NEXT_PUBLIC_API_BASE`(기본 localhost:8000). 백엔드 133건 유지.

### P2-7. 프론트 검수 화면
- [x] 생성 JSON 표 편집 UI → 재검증 → 재렌더링 → 다운로드
- **AC**: 편집·재렌더링·다운로드가 브라우저에서 동작.
- 메모: `app/jobs/[id]/page.tsx`(클라이언트). **Next 16 변경점**: 동적 route `params` 가 Promise → `use(params)` 로 언래핑. `getScenario` 로 로드, 단위/통합 표 편집(텍스트 필드 인라인 입력 + 테스트 절차 textarea 줄바꿈↔배열). `저장(재검증)`=PUT(422 시 detail 노출), `저장 후 렌더링`=PUT→POST /render→다운로드 링크 노출(`downloadUrl`). `api.ts` 에 `Scenario`/`TestCase`/`CaseListKey` 타입 추가, get/put 시그니처를 Record→Scenario 로 강화. lint/build 통과. **행 추가/삭제는 MVP 제외**(백로그). → 브라우저 실동작 판정은 P2-8.

### P2-8. Phase 2 통합 검수 (사람 게이트)
- [x] 업로드~다운로드 전 과정을 실제로 수행해 판정.
- **AC**: 전 흐름 합격 판정, 개선 항목 환원.
- 메모: **2026-06-14 사용자 검수 — 기능 합격**. 개선 요구 2건 환원 → P2-9 에서 처리: ① UI 단조로움(엔터프라이즈급 재디자인) ② 완료 화면에서 홈 복귀 동선.

### P2-9. 엔터프라이즈 UI 리디자인 + 홈 내비게이션
- [x] 디자인 시스템(`globals.css`: slate+indigo 토큰, `.btn-primary/secondary/success`, `.card`, `.field-*` 공통 클래스), 앱 셸(`AppHeader` 로고/홈 링크 + `AppFooter`), 업로드 화면(드롭존 스타일 + 진행 스텝퍼 + 완료/실패 패널), 검수 화면(← 홈으로 백링크 + 메타 헤더 + 카드형 표 zebra + 하단 sticky 액션 바 + 렌더링 후 다운로드 패널에 홈으로)
- **AC**: lint/build 통과, 프리뷰에서 홈·검수 화면 시각 확인, 모든 완료 화면에서 홈 복귀 가능.
- 메모: **Tailwind v4 주의**: `@apply` 는 커스텀 클래스를 참조 못 함(유틸리티만) → 버튼 변형은 self-contained 유틸 나열. 라이트 테마 고정(globals 의 prefers-color-scheme 다크 자동 제거 — 흰 카드와 충돌 방지). 홈 복귀 동선 3곳: 헤더 '홈', 검수 상단 '← 홈으로', 렌더링 완료 패널 '홈으로'(+ 업로드 완료 패널 '새 문서 생성'). 프리뷰 스크린샷으로 홈/검수 확인.

---

## Phase 3 — 다중 산출물 체이닝 + ID 추적성

**Phase 목표**: 원천 문서 1개에서 화면정의서(SCR)와 테스트시나리오(TC)를 함께 생성하고,
RTM 이 REQ→SCR→TC 추적성을 연결·검증한다. 빠진 고리였던 **화면(SCR) 생성 + 요건↔화면 연결**을 채운다.

> **착수 결정사항 (2026-06-14 사용자 확정)**:
> 1. 범위: **화면정의서 추가 + 추적성** — source → 화면정의서 + 테스트시나리오 → RTM(REQ→SCR→TC).
>    (요구사항정의서 docx 생성·전체 3종 체인은 이후 증분/백로그)
> 2. 노출: **파이프라인 + CLI 먼저**, 웹 다중 산출물 UI 는 이후.

### P3-1. 화면정의서 LLM 생성 + Screen 스키마 요건 연결
- [x] `Screen` 스키마에 `req_ids: list[ReqId]`(기본 빈 목록, 기존 호환) 추가 — 화면이 실현하는 요건 ID
- [x] `prompts.py` 화면정의서 생성 프롬프트(요건 ID 목록을 받아 화면이 참조하도록 지시) + `pipelines/generate_screen_spec.py` `generate_screen_spec(...)`
- [x] `scripts/eval/eval_screen_spec.py` 평가 스크립트
- **AC**: LLM 모킹 단위 테스트로 생성·검증 통과, 스키마 경계값(SCR/REQ ID 형식) 테스트. 평가 스크립트 end-to-end 출력.
- 메모: `Screen.req_ids` 기본 빈 목록이라 기존 pptx 골든/픽스처(screen_spec_5.json) 무영향. 프롬프트는 [요건 ID 목록]을 주입해 화면이 그 안에서만 req_ids 선택하도록 지시. `generate_screen_spec(on_progress=...)` 콜백(parsing/generating). **e4b 평가 1/1 통과**: 화면 3개, SCR 중복 없음, 화면 참조 요건 ID = 원천(REQ-001/010/030) 정확 일치(유령 참조 없음). 회당 102s. 단위 14건 추가(스키마 경계 + 생성 모킹), 총 147건.

### P3-2. 체인 정합성 + RTM 연결
- [x] `build_rtm_from_chain(scenario, screen_spec)` — req 별 screen_ids 를 화면정의서에서 채움
- [x] `validate_screen_consistency(screen_spec, scenario)` — 화면 req_ids ⊆ 시나리오 요건 ID(없는 REQ 참조 거부)
- **AC**: 골든/단위 테스트 — 정상 체인 통과 + 없는 REQ 참조 화면이 거부됨.
- 메모: `build_rtm_from_chain(scenario, screen_spec=None)` 신설(기존 `build_rtm_from_scenario` 는 이것의 단축형). req→screen_ids 는 화면 순서 유지·중복 제거로 채움, **화면 있는 요건은 stage_reflection.design=True** 로 승격. `validate_screen_consistency` 는 화면 req_ids ⊆ 시나리오 요건(없는 REQ 참조 시 ValidationFailedError). RTM screen_ids ⊆ SCR 집합은 구성상 자동 보장. 테스트 4건(연결/빈칸/정합성/거부), 총 151건.

### P3-3. CLI 체인 오케스트레이션
- [x] 신규 체인 함수 `pipelines/generate_chain.py::generate_chain`: source → 테스트시나리오 + 화면정의서 → RTM(screen_ids 채움) → xlsx 2종 + pptx 렌더링 (목업은 옵션/미생성)
- [x] CLI `si-docgen generate --with-screens`
- **AC**: LLM 모킹 e2e — 입력 → test_scenario.xlsx + rtm.xlsx(screen_ids 채워짐) + screen_spec.pptx 출력.
- 메모: `generate_chain` 이 두 LLM 호출(시나리오/화면) 격리, 사이에 `validate_screen_consistency` + `validate_rtm_consistency` 로 REQ→SCR→TC 검증. 목업(HTML→PNG, Playwright)은 브라우저 의존이라 **기본 미생성**(`render_screen_spec(mockup_images=None)`) — 옵션은 후속. `--with-screens` 없으면 기존 2종 흐름 유지(하위 호환). e2e 3건: 3종 생성·pptx 열림 / RTM 화면 ID 연결(REQ-001→SCR-001, REQ-002→SCR-002) / CLI 종료코드. 모킹 테스트가 실제 pptx 렌더까지 수행. 실제 LLM 체인은 P3-5 게이트. 총 154건.

### P3-4. 로컬/상용 모델 전환
- [x] 단계별 모델 오버라이드 설정(`scenario_model`/`screen_spec_model`) — 미지정 시 `llm_model`. LiteLLM 추상화 활용
- [x] 상용 모델 전환 문서(`.env.example`). 실제 상용 평가는 API 키 확보 후(사용자 확인)
- **AC**: 설정으로 단계별 모델이 분리 적용됨을 모킹 테스트로 확인.
- 메모: `complete_json`/`generate_validated` 에 `model` 인자 추가(미지정 시 `settings.llm_model`). `generate_scenario`→`scenario_model`, `generate_screen_spec`→`screen_spec_model` 전달. 테스트는 complete_json 의 model 인자를 가로채 단계별 분리 적용 확인(미설정 시 None→client 가 기본 모델 사용). **기존 mock 들(complete_json) model kwarg 수용하도록 갱신**(FakeLLM, fake_complete_json 등). `.env.example` 에 단계별 모델 예시(시나리오=로컬, 화면=상용) 추가. 총 156건.

### P3-5. Phase 3 품질 검수 (사람 게이트)
- [x] 실제 원천 문서로 체인 실행 → 화면정의서/테스트시나리오/RTM 의 추적성·품질 판정
- **AC**: 추적성(REQ→SCR→TC) 정확성·생성물 품질 합격 판정, 개선 항목 환원.
- 메모: **2026-06-14 사용자 검수 — 합격**. e4b 체인 산출물(시나리오 7+2 / 화면 3 / RTM 요건 3) 추적성·품질 양호, 개선 요구 없음. Phase 3 종료. 후속/백로그: 화면정의서 목업 이미지(HTML→PNG) 체인 통합, 웹 UI 다중 산출물 노출, 요구사항정의서(docx) 생성.

---

## Phase 4 — React Flow 실행형 캔버스

**Phase 목표**: 역할별 노드(원천 → 시나리오/화면 → RTM)를 캔버스로 보여주고, 노드별 모델 선택 +
실행 + SSE 라이브 상태 + 결과 노드에서 검수·다운로드까지 하는 실행형 캔버스를 만든다.

> **착수 결정사항 (2026-06-14 사용자 확정)**: 실행형 캔버스. 웹 잡에 화면정의서 생성 추가가 선행.
> 신규 의존성(프론트): `@xyflow/react`.

### P4-1. 웹 잡 체인 확장 (백엔드)
- [x] 생성 함수(`generate_scenario`/`generate_screen_spec`)에 잡 단위 `model` 오버라이드 인자 추가
- [x] `Job` 에 `with_screens`(bool), `screen_spec_json`(JSON), `scenario_model`/`screen_spec_model`(str?) 컬럼 + 마이그레이션
- [x] `run_job` 체인 분기(with_screens 시 화면정의서도 생성·저장, 단계별 모델 적용), `POST /jobs` 폼 필드 추가
- [x] 렌더링·다운로드에 화면정의서(pptx) 추가(`render_job_outputs` 확장, download kind `screen_spec`)
- **AC**: LLM 모킹 e2e — with_screens 업로드 → 시나리오+화면 JSON 저장 → 렌더 → pptx 다운로드.
- 메모: `generate_scenario/screen_spec(model=...)` 우선순위 = 인자 > 설정. `with_screens` 는 NOT NULL 이라 **server_default=false() 필요**(SQLite 가 기존 행에 NOT NULL 컬럼 추가 시 default 없으면 실패). 진행값: 비체인=parsing/generating(P2 프론트 호환), 체인=scenario/screens(캔버스용). `render_job_outputs(scenario_json, screen_spec_json=None)` → 화면 있으면 `build_rtm_from_chain` 으로 RTM screen_ids 채우고 pptx 렌더. download kind `screen_spec`(pptx media type). `GET /jobs/{id}/screen-spec` 추가, `JobOut.with_screens`/`RenderOut.screen_count` 추가. e2e 4건(시나리오+화면 저장/화면조회/렌더·pptx다운로드·RTM 연결/비체인 409), 총 160건.

### P4-2. 캔버스 골격
- [x] `@xyflow/react` 도입 + `/canvas` 라우트 + 고정 파이프라인 노드(원천/시나리오/화면/RTM) 레이아웃·엣지
- **AC**: 캔버스가 렌더되고 노드/연결선이 표시됨. lint/build 통과.
- 메모: `@xyflow/react` 12.11. 커스텀 노드 `components/canvas/PipelineNode`(상태 점 idle/running/done/error, LLM 노드 ✦ 강조, target/source Handle). `/canvas` 4노드(원천→시나리오/화면→RTM) + 4엣지(원천→LLM 애니메이션). 헤더에 '캔버스' 내비 추가. **함정**: ReactFlow 부모 컨테이너에 명시적 width/height 필요 — `flex-1`+inline height 충돌로 엣지 0개(error#004) → `flex-1` 제거하고 `width:100% / height:calc(100vh-9rem)` 명시하니 엣지 4개 정상. 프리뷰 스크린샷으로 확인(애니메이션 엣지라 캡처가 가끔 타임아웃 — DOM 검증 병행). 빌드 통과.

### P4-3. 캔버스 실행
- [x] 원천 업로드 노드 + LLM 노드별 모델 선택 + 실행 버튼(잡 생성 with_screens)
- **AC**: 캔버스에서 업로드·실행 → 잡 생성됨.
- 메모: 상호작용 노드 `components/canvas/nodes.tsx`(SourceNode 파일선택 / LlmNode 모델 select 프리셋 / OutputNode). 표지 입력+▶실행은 React Flow `<Panel>`(top-left). `createJob(file, cover, {withScreens, scenarioModel, screenSpecModel})` 로 체인 잡 생성. 노드 내부 입력은 `nodrag` 클래스. → P4-4 와 한 커밋.

### P4-4. 라이브 상태 + 결과 연결
- [x] SSE 로 노드별 진행/완료 표시, 결과 노드 → 검수 화면·다운로드 링크
- **AC**: 실행 시 노드 상태가 갱신되고 완료 후 검수/다운로드 가능.
- 메모: SSE(`eventsUrl`) progress(scenario/screens/done)를 노드 상태(idle/running/done/error)로 매핑. OutputNode 완료 시 '검수 화면으로' + '렌더링하여 다운로드'(renderJob→downloads 링크). **핵심 함정**: 파생 노드를 `nodes` 컨트롤드 + `onNodesChange` no-op 으로 주면 **치수 측정 이벤트가 삼켜져 엣지 0개** → `useNodesState` 로 측정 반영 + 파생 data 는 effect 로 동기화하니 엣지 4개 정상. 프리뷰 스크린샷 확인(노드 4·엣지 4·파일입력·모델 select 2·실행 패널). lint/build 통과. 실제 라이브 실행은 P4-5.

### P4-5. Phase 4 품질 검수 (사람 게이트)
- [x] 캔버스로 업로드~다운로드 전 과정 수행 판정.
- **AC**: 전 흐름 합격 판정, 개선 항목 환원.
- 메모: **2026-06-14 사용자 검수 — 합격**. 캔버스 라이브 실행(업로드→노드 상태 진행→완료→검수/다운로드) 정상, 개선 요구 없음. Phase 4 종료 = 개발 로드맵(Phase 0~4) 전체 완료.

---

## 백로그 작업: 요구사항정의서(docx) 생성 — 체인의 머리

**목표**: 원천 문서 → 요구사항정의서(REQ 확정) → 화면정의서/테스트시나리오 → RTM.
요건정의서가 REQ ID 의 단일 진실 공급원이 되어, P1-5 에 적은 한계(요건명 대체·REQ ID 출처 부재)를 해소한다.

### B1-1. 요건정의서 단독 LLM 생성
- [x] `prompts.py` 요건정의서 생성 프롬프트 + `pipelines/generate_requirement_spec.py` `generate_requirement_spec(...)`
- [x] `config.py` 단계별 모델 `requirement_spec_model` 추가, `scripts/eval/eval_requirement_spec.py` 평가 스크립트
- **AC**: LLM 모킹 단위 테스트(생성·검증·모델 오버라이드·진행 콜백) 통과. 평가 스크립트 end-to-end 출력.
- 메모: 렌더러(`docx_renderer`)·스키마(`requirement_spec.py`)는 P0-5 기존 자산 재사용. 화면정의서(P3-1) 패턴 그대로 — 생성만 담당, 렌더링/체인 연결은 B1-2. doc_no 는 `REQ-SPEC-{year}-001` 형식·최초 개정이력 1건을 LLM 이 채우도록 프롬프트로 지시. **e4b 평가 1/1 통과**(요건 3건, REQ 중복 없음, doc_no 정확, 구분/중요도 분포 정상, 74s). e4b 가 요건을 3건만 생성 — 분량은 상용 모델·검수에서 보강(초안 포지셔닝). 단위 3건 추가, 총 162건.

### B1-2. 체인의 머리로 연결 (CLI/파이프라인)
- [x] `generate_chain(with_requirements=True)` — 요건정의서 생성 → 확정 REQ ID·요건명을 시나리오(요건 목록 주입)·화면(req_ids) 생성에 전달 → RTM 요건명을 요건정의서에서 채움 → docx 포함 4종 렌더
- [x] `validate_requirement_consistency` — 시나리오·화면이 참조하는 REQ ⊆ 요건정의서 REQ(유령 참조 거부, 단방향)
- [x] CLI `--with-requirements`
- **AC**: LLM 모킹 e2e — 4종 생성·RTM 정식 요건명 연결·유령 REQ 거부. 실제 모델 체인 확인.
- 메모: **사용자 결정(2026-06-14): CLI/파이프라인 먼저, 웹은 이후**. 설계: 요건정의서를 REQ 단일 진실 공급원으로 — (1) 시나리오 프롬프트에 `[요건 목록]` 주입(`build_test_scenario_prompt(requirements=...)`), 화면엔 요건정의서 REQ ID 집합 전달. (2) `build_rtm_from_chain(requirement_spec=...)` 이 **요건마다 1행**(TC 없는 요건도 커버리지 공백 행으로 노출) + **정식 요건명** 사용 → P1-5 한계(요건명 대체) 해소. (3) 검증 앵커가 요건정의서로 이동(`validate_requirement_consistency`); `with_requirements` 아닐 땐 기존 `validate_screen_consistency` 유지(하위 호환). 단계반영: `test=bool(tc_ids)`(기존 시나리오 경로는 항상 TC 있어 동작 불변). CLI 3모드: 기본(2종)/`--with-screens`(3종)/`--with-requirements`(4종). **실제 e4b 체인 검증**: 요건 3(REQ-001/010/030 비순차) → 4종 문서 전체에 동일 ID 일관 적용, RTM 정식 요건명·SCR·TC 연결 확인. 단위 8건 추가(총 170건).

### B1-3. 웹 노출
- [x] **백엔드(B1-3a)**: `Job` 에 `with_requirements`/`requirement_spec_json`/`requirement_spec_model` 컬럼 + 마이그레이션. `run_job` 요건 머리 분기(progress: requirements→scenario→screens). `render_job_outputs(requirement_spec_json=)` docx 렌더 + RTM 정식 요건명. `create_job`/`POST /jobs` 폼 필드. `GET /jobs/{id}/requirement-spec`. download kind `requirement_spec`(docx media type). `JobOut.with_requirements`.
- [x] **프론트(B1-3b)**: `api.ts`(Job.with_requirements, CreateJobOptions.withRequirements/requirementSpecModel). 캔버스에 **요구사항정의서 노드를 머리로 추가**(source→요건→시나리오/화면→RTM, 5노드), 단계 상태 매핑(STAGES requirements/scenario/screens), `withRequirements:true` 로 4종 체인 실행. 검수 화면 다운로드 패널을 `render.downloads` 동적 렌더로 변경(요건정의서·화면정의서 자동 노출). nodes.tsx 다운로드 라벨에 요구사항정의서 추가.
- **AC**: LLM 모킹 e2e — with_requirements 업로드 → 요건/시나리오/화면 JSON 저장 → 렌더 → docx 다운로드·RTM 정식 요건명. lint/build 통과.
- 메모: 백엔드 e2e 4건 추가(총 174건), ruff/eslint/next build 통과. **프리뷰 검증 한계**: 캔버스 5노드·요구사항정의서 노드·모델 select 렌더 확인(DOM), 콘솔 런타임 에러 없음. **엣지는 헤드리스 프리뷰에서 미표시** — 원인은 React Flow 가 노드/핸들 측정에 ResizeObserver 를 쓰는데 이 프리뷰 환경에서 ResizeObserver 가 발화하지 않음(+ 초기 error#004). 코드는 엣지가 정상 표시됐던 P4-4 와 동일 패턴·동일 컨테이너 설정이라 실제 브라우저에서는 표시됨. 라이브 실행(실모델 4종 생성·노드 상태 진행) 판정은 사람 게이트(B1-3c).

### B1-3c. 웹 요건 체인 사람 검수 (게이트)
- [x] 캔버스에서 업로드→요건/시나리오/화면 노드 상태 진행→완료→요구사항정의서 docx 포함 4종 다운로드를 실제 브라우저로 수행 판정.
- 메모: **2026-06-14 사용자 검수 — 합격**. 캔버스 라이브 4종 체인(실제 브라우저에서 엣지 정상 표시 포함) 정상. 함께 처리: 캔버스 서브헤더 중복 '홈으로' 제거(전역 헤더 '홈'과 중복). **→ B1(요구사항정의서 CLI~웹) 전체 종료.**

## 백로그 작업: 웹 검수 화면 다중 산출물 편집

**목표**: 검수 화면에서 테스트시나리오뿐 아니라 요구사항정의서·화면정의서도 편집·재검증·재렌더할 수 있게 한다.

### B2-1. 편집 PUT 엔드포인트 (백엔드)
- [x] `PUT /jobs/{id}/screen-spec`, `PUT /jobs/{id}/requirement-spec` — 편집본을 스키마 자동 재검증(위반 422), 미생성 잡 409. 시나리오 PUT 과 동일 패턴(구조 검증만, 요건↔화면 교차 추적성은 render 시점).
- **AC**: 편집 저장·렌더 반영·스키마 위반 422·409 e2e. → 통과(5건, 총 179건).
- 메모: `tests/unit/test_api_edit_specs.py`. 교차 정합성을 PUT 에서 강제하지 않는 이유 = 시나리오 PUT 과 일관성, 그리고 편집 중간 상태(요건만 먼저 저장)를 허용하기 위함. 최종 정합성은 render 의 `validate_requirement_consistency`/`validate_rtm_consistency` 가 보장(실패 시 렌더 422).

### B2-2. 탭형 검수 편집 UI (프론트)
- [x] `api.ts`: RequirementSpec/ScreenSpec 타입 + get/put 4함수. 검수 페이지를 **탭(요구사항정의서/테스트시나리오/화면정의서)** 으로 재구성 — 잡이 가진 산출물만 탭 노출. `저장(재검증)`/`저장 후 렌더링` 은 로드된 산출물 전체를 PUT 후 처리.
- [x] `components/review/RequirementEditor`(요건 표: ID·요건명·구분(datalist)·중요도(select)·설명·비고 + 문서번호), `components/review/ScreenEditor`(화면 카드: ID·화면명·메뉴·연관요건(쉼표)·항목표(번호/명/유형/필수체크/설명)·처리로직 textarea). 시나리오 표는 기존 CaseTable 유지.
- **AC**: lint/build 통과, 브라우저에서 3산출물 편집·저장·렌더·다운로드 동작.
- 메모: 프리뷰 검증(시드 잡 직접 주입) — 3탭 렌더·데이터 채움 확인, 탭 전환 OK, `저장(재검증)` → 3산출물 PUT 성공("검수 내용을 저장했습니다"), `저장 후 렌더링` → 4종 다운로드(요구사항정의서·테스트시나리오·요건추적표·화면정의서) 노출, 콘솔 에러 없음. 라이브 LLM 잡으로의 최종 사람 검수는 후속(원하면 게이트).

### B2-3. 행/항목 추가·삭제
- [x] 공용 `lib/review.ts::nextNumberedId`(기존 ID 에서 다음 순번 자동 생성). 시나리오(케이스 추가/삭제, TC ID 는 단위+통합 전체에서 유일), 요건(요건 추가/삭제, 최소 1건 보장→마지막 삭제 비활성), 화면(화면·항목 추가/삭제, 각 최소 1건 보장).
- **AC**: 추가/삭제 동작 + 추가 행이 백엔드 재검증 통과 + 영속화.
- 메모: 새 행 기본값을 스키마 통과하도록 채움(요건 REQ-00x/기능/중, 케이스 TC-00x·req REQ-001·test_steps 1개·expected 채움, 화면 SCR-00x·항목 1개, 항목 번호 max+1 ≤20). **프리뷰 검증**: 요건 2→3(REQ-003)→2, 케이스 단위 1→2(TC-002), 화면 항목 1→2(no=2)·화면 1→2(SCR-002), `저장(재검증)` 성공 후 GET 으로 TC-002/SCR-002/항목2건 영속 확인, 콘솔 에러 없음. 삭제는 min(요건/화면/항목 1건) 도달 시 버튼 비활성(시나리오 케이스는 0건 허용이라 자유 삭제). → **B2(검수 편집) 전체 완료.**

## 백로그 작업: 신규 산출물 — WBS

**목표(사용자 결정 2026-06-14)**: WBS 부터, **렌더러 PoC 먼저**(Phase 0 방식). 이후 LLM 생성·웹은 다음 라운드.

### B3-1. WBS 렌더러 PoC
- [x] `schemas/wbs.py`(트리 모델 — 입력은 구조·기간·공수·선행만), `renderers/wbs_renderer.py`, `templates/wbs.xlsx`(+ `scripts/templates/build_wbs_template.py`), 골든/경계 테스트.
- **AC**: 하드코딩 JSON 으로 양식 충실 + **계층번호·일정·요약 공수 합산 계산** 골든 검증 + 스키마 경계값.
- 메모: **핵심 — 계층번호(1.1.2)·일정(시작/종료)·요약 공수 합산은 렌더러 코드가 계산**(CLAUDE.md 원칙). 선행은 계층번호가 아닌 안정적 `id` 로 참조 → 렌더러가 id→계층번호로 표시. 일정은 **선행 종료 다음 날부터 기간만큼(달력일, 휴일 미고려 — PoC 한계)**, 요약 태스크는 자식 최소시작~최대종료. 스키마 검증: id 유일·작업태스크 기간≥1·선행은 작업태스크 id 만·자기참조/순환 금지. 8열 단일 헤더(WBS No./태스크명/담당/시작/종료/공수(MD)/선행/산출물), STYLE_ROW=9. 골든 8 + 경계 8 = 16건 추가(총 195건). 샘플 `out/wbs_sample.xlsx`(gitignore). **2026-06-14 사용자 양식 검수 — 합격**.

### B3-2. WBS LLM 생성
- [x] `prompts.py` WBS 프롬프트(2~3단계 트리, id 슬러그, 작업 태스크만 기간/공수, 선행은 작업 id, 계층번호·날짜 미출력) + `pipelines/generate_wbs.py::generate_wbs` + `config.wbs_model` + `scripts/eval/eval_wbs.py`.
- **AC**: 모킹 단위 테스트 + e4b eval. 메모: **e4b eval 1/1 통과**(트리 17/작업 11/선행 사용, 154s — 검증 재시도 루프가 초기 무효 출력 교정). 스키마가 태스크에 날짜 필드를 두지 않아 LLM 이 일정을 출력할 수 없음 → 계층/일정 분리 강제됨. 단위 3건(총 198건).

### B3-3. WBS CLI
- [x] `generate_and_render_wbs`(생성→wbs.xlsx) + CLI `si-docgen wbs --input ... --start-date ...`(체인과 독립 서브커맨드).
- **AC**: 모킹 e2e — 입력 → wbs.xlsx(계층번호·선행 연결 검증), CLI 종료코드. 메모: 단위 3건(총 201건).

### B3-4. WBS 웹 연동
- [x] **백엔드(B3-4a)**: `Job` with_wbs/wbs_json/start_date/wbs_model 컬럼 + 마이그레이션. `run_job` with_wbs 분기(progress wbs, start_date 미지정 시 작성일 보정). `render_job_outputs(wbs_json=)` wbs.xlsx, download kind wbs. `POST /jobs` 폼, `GET /jobs/{id}/wbs`, `JobOut.with_wbs`. e2e 4건(총 205건).
- [x] **프론트(B3-4b)**: `api.ts`(withWbs/startDate/wbsModel). 캔버스에 **WBS 노드 추가**(source→WBS 독립, 6노드), STAGES 에 wbs 추가, 표지 패널에 'WBS 시작일' date 입력, `withWbs:true` 로 실행. 다운로드 라벨에 WBS 추가(검수·캔버스).
- **AC**: lint/build 통과, 캔버스 WBS 노드·시작일 입력 렌더. 메모: 프리뷰 DOM 검증 — 6노드(source/요구사항/시나리오/화면/WBS/RTM)·WBS 노드 모델 select·시작일 입력 확인, 콘솔 에러 없음. 엣지는 헤드리스 미표시(기존과 동일, 실브라우저 표시). WBS 는 시나리오와 독립 생성(REQ 체인과 별개)이라 캔버스에서 source→WBS 로 직접 연결. **2026-06-14 사용자 라이브 검수 — 합격**(캔버스 5종 생성·다운로드 정상). 함께: 렌더링 완료 후 검수 하단 액션 바 숨김. **→ B3(WBS) 전체 종료.**

## 백로그 작업: 신규 산출물 — 테이블정의서

**목표**: WBS 와 동일 흐름(렌더러 PoC → LLM → CLI → 웹). 양식은 목록형(테이블별 컬럼을 행으로 펼침).

### B4-1. 테이블정의서 렌더러 PoC
- [x] `schemas/table_spec.py`(Table/Column, 물리명 유일성), `renderers/table_spec_renderer.py`, `templates/table_spec.xlsx`(+ `scripts/templates/build_table_spec_template.py`), 골든/경계 테스트.
- **AC**: 하드코딩 JSON 으로 양식 충실 + 테이블별 컬럼 펼침·PK/Null/FK 표기·번호 리셋 골든 검증 + 스키마 경계값.
- 메모: **목록형** 11열(No./테이블 논리·물리명/컬럼 논리·물리명/타입/PK/FK 참조/Null/기본값/설명), STYLE_ROW=9. 테이블 논리/물리명은 컬럼마다 반복, 번호는 테이블 내 1부터. PK→"PK", Null→Y/N, FK→참조 문자열. 검증: 테이블 물리명 문서 전체 유일·컬럼 물리명 테이블 내 유일. 골든 8 + 경계 5 = 13건(총 218건). 샘플 `out/table_spec_sample.xlsx`(gitignore). **2026-06-14 사용자 양식 검수 — 합격**.

### B4-2,3. 테이블정의서 LLM 생성 + CLI
- [x] `prompts.py` 테이블정의서 프롬프트(물리명 규약 TB_/대문자, PK/FK, data_type 구체화) + `pipelines/generate_table_spec.py`(`generate_table_spec`/`generate_and_render_table_spec`) + `config.table_spec_model` + `scripts/eval/eval_table_spec.py` + CLI `table-spec` 서브커맨드.
- **AC**: 모킹 단위·CLI e2e + e4b eval. 메모: **e4b eval 1/1 통과**(테이블 4·컬럼 13·PK 3/4 테이블·FK 4, 78s 재시도 없음 — WBS 보다 단순 구조라 안정적). 단위 4건(총 222건).

### B4-4. 테이블정의서 웹 연동
- [x] **백엔드(B4-4a)**: `Job` with_table_spec/table_spec_json/table_spec_model 컬럼 + 마이그레이션. `run_job` with_table_spec 분기(progress table_spec). `render_job_outputs(table_spec_json=)` table_spec.xlsx, download kind table_spec. `POST /jobs` 폼, `GET /jobs/{id}/table-spec`, `JobOut.with_table_spec`. e2e 4건(총 226건).
- [x] **프론트(B4-4b)**: `api.ts`(withTableSpec/tableSpecModel). 캔버스에 **테이블정의서 노드 추가**(source→테이블정의서 독립, 7노드), STAGES 에 table_spec 추가, `withTableSpec:true` 로 실행. 다운로드 라벨 추가(검수·캔버스).
- **AC**: lint/build 통과, 캔버스 7노드 렌더. 메모: 프리뷰 DOM 검증 — 7노드(source/요구사항/시나리오/화면/WBS/테이블정의서/RTM)·노드 모델 select 확인, 콘솔 에러 없음. **라이브 6종 생성 판정은 사람 게이트(후속)**.

## 백로그 작업: 신규 산출물 — 인터페이스정의서

**목표**: WBS·테이블정의서와 동일 흐름(렌더러 PoC → LLM → CLI → 웹). 목록형(인터페이스별 메시지 항목을 행으로 펼침).

### B5-1. 인터페이스정의서 렌더러 PoC
- [x] `schemas/interface_spec.py`(Interface/MessageField, IF ID 형식·유일성), `renderers/interface_spec_renderer.py`, `templates/interface_spec.xlsx`(+ build 스크립트), 골든/경계 테스트.
- **AC**: 하드코딩 JSON 으로 양식 충실 + 인터페이스별 항목 펼침·번호 리셋·연계방식/주기/필수 표기 골든 검증 + 스키마 경계값.
- 메모: **목록형** 11열(No./I/F ID/인터페이스명/송신·수신 시스템/연계 방식/주기/항목명/타입/필수/설명), STYLE_ROW=9, table_spec 와 동일 레이아웃. 인터페이스 메타는 항목마다 반복, 번호는 인터페이스 내 1부터. 필수→Y/N. 검증: IF ID 형식(IF-\\d{3,})·문서 전체 유일·항목명 인터페이스 내 유일. 골든 8 + 경계 6 = 14건(총 240건). 샘플 `out/interface_spec_sample.xlsx`(gitignore). **2026-06-14 사용자 양식 검수 — 합격**.

### B5-2,3. 인터페이스정의서 LLM 생성 + CLI
- [x] `prompts.py` 인터페이스정의서 프롬프트(IF-00x·송수신·연계방식/주기·메시지 항목) + `pipelines/generate_interface_spec.py` + `config.interface_spec_model` + `scripts/eval/eval_interface_spec.py` + CLI `interface-spec` 서브커맨드.
- **AC**: 모킹 단위·CLI e2e + e4b eval. 메모: **e4b eval 1/1 통과**(인터페이스 3·항목 9·IF ID 유일·연계방식 {REST API:2, Web Service:1}, 94.6s). 단위 4건(총 244건).

### B5-4. 인터페이스정의서 웹 연동
- [x] **백엔드(B5-4a)**: `Job` with_interface_spec/interface_spec_json/interface_spec_model 컬럼 + 마이그레이션. `run_job` 분기(progress interface_spec). `render_job_outputs(interface_spec_json=)`, download kind interface_spec. `POST /jobs` 폼, `GET /jobs/{id}/interface-spec`, `JobOut.with_interface_spec`. e2e 4건(총 248건).
- [x] **프론트(B5-4b)**: `api.ts`(withInterfaceSpec/interfaceSpecModel). 캔버스에 **인터페이스정의서 노드 추가**(source→인터페이스정의서 독립, 8노드), STAGES 에 interface_spec 추가, `withInterfaceSpec:true` 로 실행. 다운로드 라벨 추가.
- **AC**: lint/build 통과, 캔버스 8노드 렌더. 메모: 프리뷰 DOM 검증 — 8노드(source/요구사항/시나리오/화면/WBS/테이블/인터페이스/RTM) 렌더·콘솔 에러 없음. **라이브 7종 생성 판정은 사람 게이트(후속)**. → 신규 산출물(B3·B4·B5) 전부 PoC~웹 완료.

## 백로그 작업: 사용자 매뉴얼(docx)

**목표**: 섹션(기능)별 단계 설명 + 화면 캡처가 들어간 사용자 매뉴얼. 캡처는 브라우저 자동화라
절대 원칙(렌더러 순수 함수)·새 의존성과 충돌 → **렌더러 PoC(캡처 무관) → LLM → 캡처(Playwright)** 순서.

### B6-1. 사용자 매뉴얼 렌더러 PoC
- [x] `schemas/user_manual.py`(섹션→단계, 단계는 `screen_ref` 이미지 키로 참조), `renderers/user_manual_renderer.py`(docxtpl + InlineImage, 이미지 맵 주입), `templates/user_manual.docx`(+ build 스크립트, 섹션·단계 중첩 반복 + 이미지 자리), 골든/경계 테스트.
- **AC**: 하드코딩 JSON + 플레이스홀더 PNG 로 양식 충실 + 이미지 삽입/플레이스홀더 분기 골든 검증 + 스키마 경계값.
- 메모: **핵심 설계 — 캡처는 렌더러 밖**. 단계는 `screen_ref`(예: SCR-001)로만 참조하고, 실제 이미지는 렌더 시 `images`(screen_ref→파일경로) 맵으로 전달(절대 원칙: 렌더러는 네트워크 I/O·캡처 안 함). 참조에 이미지 있으면 `InlineImage`(폭 14cm), 없으면 `[화면 캡처: …]` 플레이스홀더, screen_ref 없으면 빈 자리. 섹션·단계 번호는 docxtpl `loop.index`(단계는 섹션마다 1부터). **새 의존성 없음**(docxtpl 이미지 삽입 + zlib 생성 플레이스홀더 PNG `tests/golden/fixtures/manual_screenshot.png`, python-docx 가 PNG 헤더 직접 읽어 pillow 불필요). 골든 6 + 경계 5 = 11건(총 259건). 샘플 `out/user_manual_sample.docx`(gitignore). **2026-06-14 사용자 양식 검수 — 합격**.

### B6-2. 매뉴얼 LLM 생성 + CLI
- [x] `prompts.py` 사용자 매뉴얼 프롬프트(기능별 섹션·단계 행동 지시·screen_ref, 이미지 미출력) + `pipelines/generate_user_manual.py` + `config.user_manual_model` + `scripts/eval/eval_user_manual.py` + CLI `user-manual` 서브커맨드.
- **AC**: 모킹 단위·CLI e2e + e4b eval. 메모: 캡처 전이라 화면 자리는 플레이스홀더로 렌더(`generate_and_render_user_manual(images=None)`). **e4b eval 1/1 통과**(섹션 3·단계 5·screen_ref 3/5, 43s). 단위 4건(총 263건).

### B6-3. 화면 캡처 (방식 결정 대기 — 2026-06-14)
- [ ] **사용자 결정 필요**: (1) 수동 이미지 폴더(`--images-dir`, `{screen_ref}.png`, 새 의존성 없음) (2) 자동 캡처-우리 생성 화면(HTML→PNG, Playwright) (3) 자동 캡처-고객 실제 앱 URL(Playwright, 앱별 네비게이션). 렌더러는 이미 `images` 맵을 받으므로, 캡처 파이프라인(렌더러 밖)이 맵을 채워 전달.

## 백로그 (Phase 미배정)

- [x] ~~화면정의서 목업 이미지(HTML→PNG)~~ → **편집 가능한 PPT 도형 목업**으로 구현(2026-06-14). `pptx_renderer._draw_mockup`(번호 배지·라벨·유형별 컨트롤), HTML/Playwright/pillow 의존 제거. 골든 테스트 `tests/golden/test_pptx_mockup.py`.
- [x] ~~웹 검수 화면에 화면정의서/요구사항정의서 편집 UI~~ → 위 'B2' 섹션에서 구현
- [x] ~~검수 화면 행/항목 추가·삭제~~ → B2-3 에서 구현
- [x] 요구사항정의서(docx) 생성 — 위 'B1' 섹션(B1-1·B1-2·B1-3) 완료, 사람 게이트(B1-3c)만 대기
- [~] 사용자 매뉴얼(docx) 생성 — 위 'B6' 섹션(렌더러 PoC 완료, LLM·캡처 후속)
- [ ] 양식 온보딩 반자동화: 고객사 양식 분석 → 플레이스홀더 위치 제안 도구
- [ ] HWP(hwpx) 출력 지원 검토
- [x] WBS 산출물 — 위 'B3' 섹션(렌더러 PoC·LLM·CLI·웹 완료, 라이브 사람 게이트만 후속)
- [x] 테이블정의서 — 위 'B4' 섹션(렌더러·LLM·CLI·웹 완료, 라이브 사람 게이트만 후속)
- [x] 인터페이스정의서 — 위 'B5' 섹션(렌더러·LLM·CLI·웹 완료, 라이브 사람 게이트만 후속)

---

## 의사결정 기록 (ADR 요약)

| 날짜 | 결정 | 사유 |
|---|---|---|
| 2026-06-13 | LLM은 JSON만 생성, 렌더링은 결정론적 코드 | 양식 충실도를 LLM 능력과 분리 |
| 2026-06-13 | 템플릿 보존 + 값 주입 방식 (코드로 서식 재생성 금지) | 고객사 양식 100% 보존 |
| 2026-06-13 | ~~PPT 목업은 HTML → Playwright 캡처 → PNG 삽입~~ (2026-06-14 폐기) | LLM의 HTML 생성 품질 > PPT 도형 조작 품질 |
| 2026-06-14 | PPT 목업을 편집 가능한 도형으로 렌더(이미지·Playwright 폐기) | 사용자가 PowerPoint에서 위치·크기·텍스트 직접 수정 가능. 이미지는 간단 수정에도 교체 필요해 불편 |
| 2026-06-13 | 개발 도구는 Claude Code 단일 사용 | 컨텍스트 일관성, 도구 교체 오버헤드 제거 |
| 2026-06-14 | 기본 LLM 모델 ollama/gemma4:e4b | 12b 는 구조화 출력 추론이 너무 느림(타임아웃). e4b 로 평가 3/3 통과 |
| 2026-06-14 | RTM 은 시나리오에서 결정론적 파생(LLM 미사용) | ID 정합성 자동 보장, 별도 프롬프트·평가 불필요 |
| 2026-06-14 | 추적성(REQ→SCR→TC)은 RTM 을 조인 테이블로 | 화면은 req_ids 로 요건 참조, TC 스키마 불변 유지 |
| 2026-06-14 | 단계별 모델 오버라이드(scenario/screen) | 산출물별 로컬·상용 모델 분리 운용 가능 |
| 2026-06-14 | 요구사항정의서를 체인의 머리로(REQ 단일 진실 공급원) | 시나리오·화면·RTM 의 REQ ID 출처 일원화, RTM 정식 요건명 |
| 2026-06-14 | RTM 은 요건정의서 요건마다 1행(TC 없는 요건도 노출) | RTM 을 커버리지 매트릭스로 — 미커버 요건이 공백 행으로 보임 |
