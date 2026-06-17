"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import {
  ApiError,
  deleteManualImage,
  downloadUrl,
  getJob,
  getProposal,
  getRequirementSpec,
  getScenario,
  getScreenSpec,
  getUserManual,
  listManualImages,
  putProposal,
  putRequirementSpec,
  putScenario,
  putScreenSpec,
  putUserManual,
  renderJob,
  uploadManualImage,
  type CaseListKey,
  type Job,
  type ManualImageStatus,
  type Proposal,
  type RenderResult,
  type RequirementSpec,
  type Scenario,
  type ScreenSpec,
  type TestCase,
  type UserManual,
} from "@/lib/api";
import { ManualEditor } from "@/components/review/ManualEditor";
import { ProposalEditor } from "@/components/review/ProposalEditor";
import { RequirementEditor } from "@/components/review/RequirementEditor";
import { ScreenEditor } from "@/components/review/ScreenEditor";
import { nextNumberedId } from "@/lib/review";
import { VersionSelector } from "@/components/review/VersionSelector";

type TabKey = "proposal" | "requirement" | "scenario" | "screen" | "manual";

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [requirementSpec, setRequirementSpec] = useState<RequirementSpec | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [screenSpec, setScreenSpec] = useState<ScreenSpec | null>(null);
  const [userManual, setUserManual] = useState<UserManual | null>(null);
  const [manualImages, setManualImages] = useState<ManualImageStatus>({});
  const [useMockupImages, setUseMockupImages] = useState(false);
  const [tab, setTab] = useState<TabKey | null>(null);
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
          j.with_proposal ? getProposal(id).then(setProposal) : null,
          j.with_screens ? getScenario(id).then(setScenario) : null,
          j.with_requirements ? getRequirementSpec(id).then(setRequirementSpec) : null,
          j.with_screens ? getScreenSpec(id).then(setScreenSpec) : null,
          j.with_user_manual ? getUserManual(id).then(setUserManual) : null,
          j.with_user_manual ? listManualImages(id).then(setManualImages) : null,
        ]);
        // 잡이 가진 산출물 중 첫 편집 탭을 활성화
        const first: TabKey | null = j.with_proposal
          ? "proposal"
          : j.with_requirements
            ? "requirement"
            : j.with_screens
              ? "scenario"
              : j.with_user_manual
                ? "manual"
                : null;
        setTab(first);
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
    if (proposal) await putProposal(id, proposal);
    if (requirementSpec) await putRequirementSpec(id, requirementSpec);
    if (scenario) await putScenario(id, scenario);
    if (screenSpec) await putScreenSpec(id, screenSpec);
    if (userManual) await putUserManual(id, userManual);
  }

  async function handleUploadImage(screenRef: string, file: File) {
    setSaveErr(null);
    setSaveMsg(null);
    try {
      await uploadManualImage(id, screenRef, file);
      setManualImages(await listManualImages(id));
      setRender(null);
    } catch (e) {
      setSaveErr(
        e instanceof ApiError
          ? `업로드 실패: ${e.message}`
          : "이미지 업로드에 실패했습니다.",
      );
    }
  }

  async function handleDeleteImage(screenRef: string) {
    setSaveErr(null);
    setSaveMsg(null);
    try {
      await deleteManualImage(id, screenRef);
      setManualImages(await listManualImages(id));
      setRender(null);
    } catch (e) {
      setSaveErr(e instanceof ApiError ? e.message : "이미지 삭제에 실패했습니다.");
    }
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
      setRender(await renderJob(id, useMockupImages));
      setSaveMsg("렌더링이 완료되었습니다. 아래에서 다운로드하세요.");
    } catch (e) {
      setSaveErr(e instanceof ApiError ? `검증 실패: ${e.message}` : "렌더링에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRollbackSuccess(nextJob: Job, specType: TabKey) {
    setJob(nextJob);
    setRender(null);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      if (specType === "proposal") {
        setProposal(await getProposal(id));
      } else if (specType === "requirement") {
        setRequirementSpec(await getRequirementSpec(id));
      } else if (specType === "scenario") {
        setScenario(await getScenario(id));
      } else if (specType === "screen") {
        setScreenSpec(await getScreenSpec(id));
      } else if (specType === "manual") {
        setUserManual(await getUserManual(id));
      }
    } catch (e) {
      console.error("롤백 후 데이터 로드 실패:", e);
      setSaveErr("롤백 반영 중 오류가 발생했습니다. 새로고침을 시도하세요.");
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
  if (!job) {
    return (
      <Centered>
        <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-600" />
        <p className="text-sm text-slate-500">검수 데이터를 불러오는 중…</p>
      </Centered>
    );
  }

  const tabs: { key: TabKey; label: string }[] = [
    proposal ? { key: "proposal" as const, label: "제안서" } : null,
    requirementSpec ? { key: "requirement" as const, label: "요구사항정의서" } : null,
    scenario ? { key: "scenario" as const, label: "테스트시나리오" } : null,
    screenSpec ? { key: "screen" as const, label: "화면정의서" } : null,
    userManual ? { key: "manual" as const, label: "사용자 매뉴얼" } : null,
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
              {job.project_name || "산출물 검수"}
            </h1>
          </div>
          <dl className="flex gap-6 text-xs text-slate-500">
            <div>
              <dt className="text-slate-400">시스템</dt>
              <dd className="font-medium text-slate-700">{job.system_name || "-"}</dd>
            </div>
            <div>
              <dt className="text-slate-400">{job.with_proposal ? "제안사" : "작성자"}</dt>
              <dd className="font-medium text-slate-700">{job.author || "-"}</dd>
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

      {tabs.length === 0 && (
        <div className="card p-6 text-sm text-slate-600">
          이 산출물은 편집 화면 없이 생성됩니다. 아래 <b>저장 후 렌더링</b>으로 파일을 만들어
          다운로드하세요.
        </div>
      )}

      {tab === "proposal" && proposal && (
        <div className="flex flex-col gap-4">
          <VersionSelector jobId={id} specType="proposal" onRollback={(j) => handleRollbackSuccess(j, "proposal")} />
          <ProposalEditor proposal={proposal} onChange={edited(setProposal)} />
        </div>
      )}

      {tab === "requirement" && requirementSpec && (
        <div className="flex flex-col gap-4">
          <VersionSelector jobId={id} specType="requirement_spec" onRollback={(j) => handleRollbackSuccess(j, "requirement")} />
          <RequirementEditor spec={requirementSpec} onChange={edited(setRequirementSpec)} />
        </div>
      )}

      {tab === "scenario" && scenario && (
        <div className="flex flex-col gap-4">
          <VersionSelector jobId={id} specType="scenario" onRollback={(j) => handleRollbackSuccess(j, "scenario")} />
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
        </div>
      )}

      {tab === "screen" && screenSpec && (
        <div className="flex flex-col gap-4">
          <VersionSelector jobId={id} specType="screen_spec" onRollback={(j) => handleRollbackSuccess(j, "screen")} />
          <ScreenEditor spec={screenSpec} onChange={edited(setScreenSpec)} />
        </div>
      )}

      {tab === "manual" && userManual && (
        <div className="flex flex-col gap-4">
          <VersionSelector jobId={id} specType="user_manual" onRollback={(j) => handleRollbackSuccess(j, "manual")} />
          <ManualEditor
            manual={userManual}
            onChange={edited(setUserManual)}
            images={manualImages}
            onUpload={handleUploadImage}
            onDelete={handleDeleteImage}
            useMockupImages={useMockupImages}
            onUseMockupImagesChange={setUseMockupImages}
          />
        </div>
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
            {Object.keys(render.downloads)
              .filter((kind) => kind !== "user-manual-pdf")
              .map((kind) => (
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
  proposal: "제안서",
  requirement_spec: "요구사항정의서",
  test_scenario: "테스트시나리오",
  rtm: "요건추적표(RTM)",
  screen_spec: "화면정의서",
  wbs: "WBS",
  table_spec: "테이블정의서",
  interface_spec: "인터페이스정의서",
  user_manual: "사용자 매뉴얼",
  "user-manual-pdf": "사용자 매뉴얼 (PDF)",
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
