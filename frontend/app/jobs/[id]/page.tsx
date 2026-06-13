"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import {
  ApiError,
  downloadUrl,
  getScenario,
  putScenario,
  renderJob,
  type CaseListKey,
  type RenderResult,
  type Scenario,
  type TestCase,
} from "@/lib/api";

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [render, setRender] = useState<RenderResult | null>(null);

  useEffect(() => {
    getScenario(id)
      .then(setScenario)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.message : "시나리오를 불러오지 못했습니다."),
      );
  }, [id]);

  function updateCase(list: CaseListKey, index: number, field: keyof TestCase, value: unknown) {
    setScenario((prev) => {
      if (!prev) return prev;
      const cases = [...prev[list]];
      cases[index] = { ...cases[index], [field]: value };
      return { ...prev, [list]: cases };
    });
    setRender(null); // 편집되면 이전 렌더 결과는 무효
  }

  async function handleSave() {
    if (!scenario) return;
    setBusy(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      await putScenario(id, scenario);
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
    try {
      await putScenario(id, scenario!); // 최신 편집본 저장 후 렌더링
      setRender(await renderJob(id));
      setSaveMsg("렌더링 완료 — 아래에서 다운로드하세요.");
    } catch (e) {
      setSaveErr(e instanceof ApiError ? `검증 실패: ${e.message}` : "렌더링에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return <Centered>{loadError}</Centered>;
  }
  if (!scenario) {
    return <Centered>불러오는 중…</Centered>;
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">검수 — {scenario.project_name}</h1>
        <Link href="/" className="text-sm text-gray-500 underline">
          새 문서
        </Link>
      </div>

      <CaseTable
        title="단위 테스트"
        cases={scenario.unit_test_cases}
        onChange={(i, f, v) => updateCase("unit_test_cases", i, f, v)}
      />
      <CaseTable
        title="통합 테스트"
        cases={scenario.integration_test_cases}
        onChange={(i, f, v) => updateCase("integration_test_cases", i, f, v)}
      />

      {saveErr && <p className="text-sm text-red-600">{saveErr}</p>}
      {saveMsg && <p className="text-sm text-green-700">{saveMsg}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handleSave}
          disabled={busy}
          className="rounded border border-gray-300 px-4 py-2 text-sm disabled:opacity-50"
        >
          저장(재검증)
        </button>
        <button
          onClick={handleRender}
          disabled={busy}
          className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          저장 후 렌더링
        </button>
        {render && (
          <div className="flex gap-3">
            <a
              href={downloadUrl(id, "test_scenario")}
              className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white"
            >
              테스트시나리오 다운로드
            </a>
            <a
              href={downloadUrl(id, "rtm")}
              className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white"
            >
              RTM 다운로드
            </a>
          </div>
        )}
      </div>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-20 text-sm text-gray-500">
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
}: {
  title: string;
  cases: TestCase[];
  onChange: (index: number, field: keyof TestCase, value: unknown) => void;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold text-gray-700">
        {title} <span className="text-gray-400">({cases.length}건)</span>
      </h2>
      {cases.length === 0 ? (
        <p className="text-sm text-gray-400">케이스 없음</p>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-200">
          <table className="min-w-full border-collapse text-xs">
            <thead className="bg-gray-50">
              <tr>
                {TEXT_FIELDS.map((f) => (
                  <th key={f.key} className="border-b px-2 py-1.5 text-left font-medium">
                    {f.label}
                  </th>
                ))}
                <th className="border-b px-2 py-1.5 text-left font-medium">테스트 절차</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c, i) => (
                <tr key={i} className="align-top">
                  {TEXT_FIELDS.map((f) => (
                    <td key={f.key} className="border-b px-1 py-1">
                      <input
                        value={c[f.key] as string}
                        onChange={(e) => onChange(i, f.key, e.target.value)}
                        className={`${f.width} rounded border border-transparent px-1.5 py-1 hover:border-gray-200 focus:border-gray-400 focus:outline-none`}
                      />
                    </td>
                  ))}
                  <td className="border-b px-1 py-1">
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
                      className="w-72 rounded border border-transparent px-1.5 py-1 hover:border-gray-200 focus:border-gray-400 focus:outline-none"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
