"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import {
  ApiError,
  downloadUrl,
  getJob,
  getRequirementSpec,
  getScenario,
  getScreenSpec,
  putRequirementSpec,
  putScenario,
  putScreenSpec,
  renderJob,
  type CaseListKey,
  type Job,
  type RenderResult,
  type RequirementSpec,
  type Scenario,
  type ScreenSpec,
  type TestCase,
} from "@/lib/api";
import { RequirementEditor } from "@/components/review/RequirementEditor";
import { ScreenEditor } from "@/components/review/ScreenEditor";
import { nextNumberedId } from "@/lib/review";

type TabKey = "requirement" | "scenario" | "screen";

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [requirementSpec, setRequirementSpec] = useState<RequirementSpec | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [screenSpec, setScreenSpec] = useState<ScreenSpec | null>(null);
  const [tab, setTab] = useState<TabKey>("scenario");
  const [loadError, setLoadError] = useState<string | null>(null);

  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [render, setRender] = useState<RenderResult | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const j = await getJob(id);
        setJob(j);
        await Promise.all([
          getScenario(id).then(setScenario),
          j.with_requirements ? getRequirementSpec(id).then(setRequirementSpec) : null,
          j.with_screens || j.with_requirements ? getScreenSpec(id).then(setScreenSpec) : null,
        ]);
        if (j.with_requirements) setTab("requirement");
      } catch (e) {
        setLoadError(e instanceof ApiError ? e.message : "검수 데이터를 불러오지 못했습니다.");
      }
    })();
  }, [id]);

  function edited<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v);
      setRender(null);
      setSaveMsg(null);
    };
  }

  function updateCase(list: CaseListKey, index: number, field: keyof TestCase, value: unknown) {
    setScenario((prev) => {
      if (!prev) return prev;
      const cases = [...prev[list]];
      cases[index] = { ...cases[index], [field]: value };
      return { ...prev, [list]: cases };
    });
    setRender(null);
    setSaveMsg(null);
  }

  function addCase(list: CaseListKey) {
    setScenario((prev) => {
      if (!prev) return prev;
      const allIds = [...prev.unit_test_cases, ...prev.integration_test_cases].map((c) => c.tc_id);
      const newCase: TestCase = {
        tc_id: nextNumberedId(allIds, "TC-"),
        req_id: "REQ-001",
        category_major: "분류",
        category_minor: "세부",
        scenario_name: "신규 시나리오",
        precondition: "",
        test_steps: ["단계"],
        expected_result: "기대 결과",
        result: null,
        note: "",
      };
      return { ...prev, [list]: [...prev[list], newCase] };
    });
    setRender(null);
    setSaveMsg(null);
  }

  function deleteCase(list: CaseListKey, index: number) {
    setScenario((prev) => {
      if (!prev) return prev;
      return { ...prev, [list]: prev[list].filter((_, i) => i !== index) };
    });
    setRender(null);
    setSaveMsg(null);
  }

  // 화면에 로드된(존재하는) 산출물을 모두 재검증·저장한다
  async function saveAll() {
    if (requirementSpec) await putRequirementSpec(id, requirementSpec);
    if (scenario) await putScenario(id, scenario);
    if (screenSpec) await putScreenSpec(id, screenSpec);
  }

  async function handleSave() {
    setBusy(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      await saveAll();
      setSaveMsg("검수 내용을 저장했습니다.");
    } catch (e) {
      setSaveErr(e instanceof ApiError ? `검증 실패: ${e.message}` : "저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRender() {
    setBusy(true);
    setSaveErr(null);
    setSaveMsg(null);
    try {
      await saveAll();
      setRender(await renderJob(id));
      setSaveMsg("렌더링이 완료되었습니다. 아래에서 다운로드하세요.");
    } catch (e) {
      setSaveErr(e instanceof ApiError ? `검증 실패: ${e.message}` : "렌더링에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <Centered>
        <p className="text-sm text-red-600">{loadError}</p>
        <Link href="/" className="btn-secondary">
          홈으로
        </Link>
      </Centered>
    );
  }
  if (!scenario || !job) {
    return (
      <Centered>
        <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-600" />
        <p className="text-sm text-slate-500">검수 데이터를 불러오는 중…</p>
      </Centered>
    );
  }

  const tabs: { key: TabKey; label: string }[] = [
    requirementSpec ? { key: "requirement" as const, label: "요구사항정의서" } : null,
    { key: "scenario" as const, label: "테스트시나리오" },
    screenSpec ? { key: "screen" as const, label: "화면정의서" } : null,
  ].filter((t): t is { key: TabKey; label: string } => t !== null);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-8">
      <div className="flex flex-col gap-3">
        <Link href="/" className="w-fit text-xs text-slate-400 hover:text-slate-600">
          ← 홈으로
        </Link>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">검수</p>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              {scenario.project_name || "산출물 검수"}
            </h1>
          </div>
          <dl className="flex gap-6 text-xs text-slate-500">
            <div>
              <dt className="text-slate-400">시스템</dt>
              <dd className="font-medium text-slate-700">{scenario.system_name || "-"}</dd>
            </div>
            <div>
              <dt className="text-slate-400">작성자</dt>
              <dd className="font-medium text-slate-700">{scenario.author || "-"}</dd>
            </div>
          </dl>
        </div>
      </div>

      {tabs.length > 1 && (
        <div className="flex gap-1 border-b border-slate-200">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
                tab === t.key
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {tab === "requirement" && requirementSpec && (
        <RequirementEditor spec={requirementSpec} onChange={edited(setRequirementSpec)} />
      )}

      {tab === "scenario" && (
        <div className="flex flex-col gap-6">
          <CaseTable
            title="단위 테스트"
            cases={scenario.unit_test_cases}
            onChange={(i, f, v) => updateCase("unit_test_cases", i, f, v)}
            onAdd={() => addCase("unit_test_cases")}
            onDelete={(i) => deleteCase("unit_test_cases", i)}
          />
          <CaseTable
            title="통합 테스트"
            cases={scenario.integration_test_cases}
            onChange={(i, f, v) => updateCase("integration_test_cases", i, f, v)}
            onAdd={() => addCase("integration_test_cases")}
            onDelete={(i) => deleteCase("integration_test_cases", i)}
          />
        </div>
      )}

      {tab === "screen" && screenSpec && (
        <ScreenEditor spec={screenSpec} onChange={edited(setScreenSpec)} />
      )}

      {render && (
        <div className="card flex flex-wrap items-center justify-between gap-4 border-emerald-200 bg-emerald-50 p-5">
          <div className="text-sm">
            <p className="font-medium text-emerald-800">산출물이 준비되었습니다.</p>
            <p className="text-emerald-700">
              단위 {render.unit_count} · 통합 {render.integration_count} · 요건{" "}
              {render.requirement_count}건
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.keys(render.downloads).map((kind) => (
              <a key={kind} href={downloadUrl(id, kind)} className="btn-success">
                ↓ {DOWNLOAD_LABEL[kind] ?? kind}
              </a>
            ))}
            <Link href="/" className="btn-secondary">
              홈으로
            </Link>
          </div>
        </div>
      )}

      {!render && (
        <div className="sticky bottom-0 -mx-6 mt-2 border-t border-slate-200 bg-slate-50/95 px-6 py-3 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-h-5 text-sm">
              {saveErr && <span className="text-red-600">{saveErr}</span>}
              {saveMsg && <span className="text-emerald-700">{saveMsg}</span>}
            </div>
            <div className="flex gap-3">
              <button onClick={handleSave} disabled={busy} className="btn-secondary">
                저장(재검증)
              </button>
              <button onClick={handleRender} disabled={busy} className="btn-primary">
                {busy ? "처리 중…" : "저장 후 렌더링"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

const DOWNLOAD_LABEL: Record<string, string> = {
  requirement_spec: "요구사항정의서",
  test_scenario: "테스트시나리오",
  rtm: "요건추적표(RTM)",
  screen_spec: "화면정의서",
  wbs: "WBS",
  table_spec: "테이블정의서",
  interface_spec: "인터페이스정의서",
};

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-20">
      {children}
    </main>
  );
}

const TEXT_FIELDS: { key: keyof TestCase; label: string; width: string }[] = [
  { key: "tc_id", label: "TC ID", width: "w-24" },
  { key: "req_id", label: "요건 ID", width: "w-24" },
  { key: "category_major", label: "대분류", width: "w-28" },
  { key: "category_minor", label: "중분류", width: "w-28" },
  { key: "scenario_name", label: "시나리오명", width: "w-56" },
  { key: "precondition", label: "사전조건", width: "w-48" },
  { key: "expected_result", label: "기대 결과", width: "w-56" },
  { key: "note", label: "비고", width: "w-32" },
];

function CaseTable({
  title,
  cases,
  onChange,
  onAdd,
  onDelete,
}: {
  title: string;
  cases: TestCase[];
  onChange: (index: number, field: keyof TestCase, value: unknown) => void;
  onAdd: () => void;
  onDelete: (index: number) => void;
}) {
  return (
    <section className="flex flex-col gap-2.5">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        {title}
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-500">
          {cases.length}건
        </span>
      </h2>
      {cases.length === 0 ? (
        <p className="card p-5 text-center text-sm text-slate-400">케이스 없음</p>
      ) : (
        <div className="card overflow-x-auto">
          <table className="min-w-full border-collapse text-xs">
            <thead className="sticky top-14 bg-slate-50">
              <tr className="text-left text-slate-500">
                {TEXT_FIELDS.map((f) => (
                  <th key={f.key} className="border-b border-slate-200 px-3 py-2 font-medium">
                    {f.label}
                  </th>
                ))}
                <th className="border-b border-slate-200 px-3 py-2 font-medium">테스트 절차</th>
                <th className="border-b border-slate-200 px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              {cases.map((c, i) => (
                <tr key={i} className="align-top odd:bg-white even:bg-slate-50/50">
                  {TEXT_FIELDS.map((f) => (
                    <td key={f.key} className="border-b border-slate-100 px-2 py-1.5">
                      <input
                        value={c[f.key] as string}
                        onChange={(e) => onChange(i, f.key, e.target.value)}
                        className={`${f.width} rounded border border-transparent bg-transparent px-1.5 py-1 hover:border-slate-200 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100`}
                      />
                    </td>
                  ))}
                  <td className="border-b border-slate-100 px-2 py-1.5">
                    <textarea
                      value={c.test_steps.join("\n")}
                      onChange={(e) =>
                        onChange(
                          i,
                          "test_steps",
                          e.target.value.split("\n").filter((s) => s.length > 0),
                        )
                      }
                      rows={Math.max(2, c.test_steps.length)}
                      className="w-72 rounded border border-transparent bg-transparent px-1.5 py-1 hover:border-slate-200 focus:border-indigo-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100"
                    />
                  </td>
                  <td className="border-b border-slate-100 px-2 py-1.5 text-center">
                    <button
                      onClick={() => onDelete(i)}
                      title="케이스 삭제"
                      className="rounded px-1.5 py-0.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button
        onClick={onAdd}
        className="w-fit rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600"
      >
        + 케이스 추가
      </button>
    </section>
  );
}
