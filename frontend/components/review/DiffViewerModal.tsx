"use client";

import { useEffect, useState } from "react";
import { getJobVersionDetail, getJobVersions } from "@/lib/api";

interface DiffViewerModalProps {
  jobId: string;
  specType: string;
  compareVersion: number;
  onClose: () => void;
}

export function DiffViewerModal({ jobId, specType, compareVersion, onClose }: DiffViewerModalProps) {
  const [oldData, setOldData] = useState<any>(null);
  const [newData, setNewData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const list = await getJobVersions(jobId, specType);
        const maxVer = list.length > 0 ? Math.max(...list.map((v) => v.version)) : 1;

        // 과거 버전 상세와 최신 버전 상세를 비동기로 동시 로드
        const [oldVal, newVal] = await Promise.all([
          getJobVersionDetail(jobId, compareVersion, specType),
          getJobVersionDetail(jobId, maxVer, specType),
        ]);
        setOldData(oldVal);
        setNewData(newVal);
      } catch (e) {
        console.error("Diff 데이터 로드 실패:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, [jobId, specType, compareVersion]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="flex h-full max-h-[85vh] w-full max-w-5xl flex-col rounded-xl bg-white shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">버전 비교 (Diff Viewer)</h2>
            <p className="mt-1 text-xs text-slate-500">
              버전 {compareVersion} (과거) 대비 최신 버전(현재)의 변경 내역을 대조합니다.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            ✕
          </button>
        </div>

        {/* 본문 콘텐츠 */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex h-40 items-center justify-center gap-2 text-xs text-slate-500">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-indigo-600" />
              데이터 비교 중…
            </div>
          ) : !oldData || !newData ? (
            <div className="text-center text-xs text-red-500 py-10">비교 데이터를 가져오지 못했습니다.</div>
          ) : (
            <DiffContent specType={specType} oldVal={oldData} newVal={newData} />
          )}
        </div>

        {/* 푸터 */}
        <div className="flex justify-end border-t border-slate-200 px-6 py-3 bg-slate-50 rounded-b-xl">
          <button onClick={onClose} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}

function DiffContent({ specType, oldVal, newVal }: { specType: string; oldVal: any; newVal: any }) {
  if (specType === "requirement_spec") {
    return <RequirementDiff oldSpec={oldVal} newSpec={newVal} />;
  }
  if (specType === "scenario") {
    return <ScenarioDiff oldSpec={oldVal} newSpec={newVal} />;
  }
  if (specType === "screen_spec") {
    return <ScreenSpecDiff oldSpec={oldVal} newSpec={newVal} />;
  }
  return <GenericJsonDiff oldSpec={oldVal} newSpec={newVal} />;
}

/* ───────────────── 요구사항정의서 Diff ───────────────── */
function RequirementDiff({ oldSpec, newSpec }: { oldSpec: any; newSpec: any }) {
  const oldReqs = oldSpec.requirements || [];
  const newReqs = newSpec.requirements || [];

  const allIds = Array.from(
    new Set([...oldReqs.map((r: any) => r.req_id), ...newReqs.map((r: any) => r.req_id)]),
  ).sort();

  return (
    <div className="flex flex-col gap-3 text-xs">
      <table className="w-full border-collapse border border-slate-200">
        <thead>
          <tr className="bg-slate-100 text-left text-slate-700 font-semibold">
            <th className="border border-slate-200 px-3 py-2 w-24">요건 ID</th>
            <th className="border border-slate-200 px-3 py-2 w-40">요구사항명 (이전 → 현재)</th>
            <th className="border border-slate-200 px-3 py-2">세부 내용 / 설명 (이전 → 현재)</th>
            <th className="border border-slate-200 px-3 py-2 w-16">우선순위</th>
          </tr>
        </thead>
        <tbody>
          {allIds.map((id) => {
            const oldR = oldReqs.find((r: any) => r.req_id === id);
            const newR = newReqs.find((r: any) => r.req_id === id);

            if (!oldR) {
              // 신규 추가
              return (
                <tr key={id} className="bg-emerald-50 text-emerald-800">
                  <td className="border border-slate-200 px-3 py-2 font-mono font-bold">{id}</td>
                  <td className="border border-slate-200 px-3 py-2 font-bold">{newR.name} [추가됨]</td>
                  <td className="border border-slate-200 px-3 py-2">{newR.description}</td>
                  <td className="border border-slate-200 px-3 py-2 text-center">{newR.priority}</td>
                </tr>
              );
            }
            if (!newR) {
              // 삭제됨
              return (
                <tr key={id} className="bg-red-50 text-red-800 line-through">
                  <td className="border border-slate-200 px-3 py-2 font-mono">{id}</td>
                  <td className="border border-slate-200 px-3 py-2">{oldR.name} [삭제됨]</td>
                  <td className="border border-slate-200 px-3 py-2">{oldR.description}</td>
                  <td className="border border-slate-200 px-3 py-2 text-center">{oldR.priority}</td>
                </tr>
              );
            }

            const nameChanged = oldR.name !== newR.name;
            const descChanged = oldR.description !== newR.description;
            const priorityChanged = oldR.priority !== newR.priority;
            const changed = nameChanged || descChanged || priorityChanged;

            return (
              <tr key={id} className={changed ? "bg-amber-50/40" : ""}>
                <td className="border border-slate-200 px-3 py-2 font-mono text-slate-500">{id}</td>
                <td className="border border-slate-200 px-3 py-2">
                  {nameChanged ? (
                    <div>
                      <span className="text-red-600 line-through mr-1.5">{oldR.name}</span>
                      <span className="text-emerald-700 font-bold">{newR.name}</span>
                    </div>
                  ) : (
                    newR.name
                  )}
                </td>
                <td className="border border-slate-200 px-3 py-2">
                  {descChanged ? (
                    <div className="flex flex-col gap-1">
                      <span className="text-red-600 line-through">{oldR.description}</span>
                      <span className="text-emerald-700 font-medium">{newR.description}</span>
                    </div>
                  ) : (
                    newR.description
                  )}
                </td>
                <td className="border border-slate-200 px-3 py-2 text-center">
                  {priorityChanged ? (
                    <div>
                      <span className="text-red-500 line-through mr-1">{oldR.priority}</span>
                      <span className="text-emerald-700 font-semibold">{newR.priority}</span>
                    </div>
                  ) : (
                    newR.priority
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ───────────────── 테스트시나리오 Diff ───────────────── */
function ScenarioDiff({ oldSpec, newSpec }: { oldSpec: any; newSpec: any }) {
  const getCases = (spec: any) => [
    ...(spec.unit_test_cases || []).map((c: any) => ({ ...c, type: "단위" })),
    ...(spec.integration_test_cases || []).map((c: any) => ({ ...c, type: "통합" })),
  ];

  const oldCases = getCases(oldSpec);
  const newCases = getCases(newSpec);

  const allIds = Array.from(
    new Set([...oldCases.map((c: any) => c.tc_id), ...newCases.map((c: any) => c.tc_id)]),
  ).sort();

  return (
    <div className="flex flex-col gap-3 text-xs">
      <table className="w-full border-collapse border border-slate-200">
        <thead>
          <tr className="bg-slate-100 text-left text-slate-700 font-semibold">
            <th className="border border-slate-200 px-3 py-2 w-24">TC ID</th>
            <th className="border border-slate-200 px-3 py-2 w-16">구분</th>
            <th className="border border-slate-200 px-3 py-2 w-24">연관 REQ</th>
            <th className="border border-slate-200 px-3 py-2">시나리오명 (이전 → 현재)</th>
            <th className="border border-slate-200 px-3 py-2">기대 결과 (이전 → 현재)</th>
          </tr>
        </thead>
        <tbody>
          {allIds.map((id) => {
            const oldC = oldCases.find((c: any) => c.tc_id === id);
            const newC = newCases.find((c: any) => c.tc_id === id);

            if (!oldC) {
              return (
                <tr key={id} className="bg-emerald-50 text-emerald-800">
                  <td className="border border-slate-200 px-3 py-2 font-mono font-bold">{id}</td>
                  <td className="border border-slate-200 px-3 py-2">{newC.type}</td>
                  <td className="border border-slate-200 px-3 py-2 font-mono">{newC.req_id}</td>
                  <td className="border border-slate-200 px-3 py-2 font-bold">{newC.scenario_name} [추가]</td>
                  <td className="border border-slate-200 px-3 py-2">{newC.expected_result}</td>
                </tr>
              );
            }
            if (!newC) {
              return (
                <tr key={id} className="bg-red-50 text-red-800 line-through">
                  <td className="border border-slate-200 px-3 py-2 font-mono">{id}</td>
                  <td className="border border-slate-200 px-3 py-2">{oldC.type}</td>
                  <td className="border border-slate-200 px-3 py-2 font-mono">{oldC.req_id}</td>
                  <td className="border border-slate-200 px-3 py-2">{oldC.scenario_name} [삭제]</td>
                  <td className="border border-slate-200 px-3 py-2">{oldC.expected_result}</td>
                </tr>
              );
            }

            const nameChanged = oldC.scenario_name !== newC.scenario_name;
            const resChanged = oldC.expected_result !== newC.expected_result;
            const reqChanged = oldC.req_id !== newC.req_id;
            const changed = nameChanged || resChanged || reqChanged;

            return (
              <tr key={id} className={changed ? "bg-amber-50/40" : ""}>
                <td className="border border-slate-200 px-3 py-2 font-mono text-slate-500">{id}</td>
                <td className="border border-slate-200 px-3 py-2 text-slate-500">{newC.type}</td>
                <td className="border border-slate-200 px-3 py-2 font-mono">
                  {reqChanged ? (
                    <div>
                      <span className="text-red-500 line-through mr-1">{oldC.req_id}</span>
                      <span className="text-emerald-700 font-bold">{newC.req_id}</span>
                    </div>
                  ) : (
                    newC.req_id
                  )}
                </td>
                <td className="border border-slate-200 px-3 py-2">
                  {nameChanged ? (
                    <div>
                      <span className="text-red-600 line-through mr-1.5">{oldC.scenario_name}</span>
                      <span className="text-emerald-700 font-bold">{newC.scenario_name}</span>
                    </div>
                  ) : (
                    newC.scenario_name
                  )}
                </td>
                <td className="border border-slate-200 px-3 py-2">
                  {resChanged ? (
                    <div className="flex flex-col gap-1">
                      <span className="text-red-600 line-through">{oldC.expected_result}</span>
                      <span className="text-emerald-700 font-medium">{newC.expected_result}</span>
                    </div>
                  ) : (
                    newC.expected_result
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ───────────────── 화면정의서 Diff ───────────────── */
function ScreenSpecDiff({ oldSpec, newSpec }: { oldSpec: any; newSpec: any }) {
  const oldScreens = oldSpec.screens || [];
  const newScreens = newSpec.screens || [];

  const allIds = Array.from(
    new Set([...oldScreens.map((s: any) => s.screen_id), ...newScreens.map((s: any) => s.screen_id)]),
  ).sort();

  return (
    <div className="flex flex-col gap-3 text-xs">
      <table className="w-full border-collapse border border-slate-200">
        <thead>
          <tr className="bg-slate-100 text-left text-slate-700 font-semibold">
            <th className="border border-slate-200 px-3 py-2 w-28">화면 ID</th>
            <th className="border border-slate-200 px-3 py-2 w-44">화면명 (이전 → 현재)</th>
            <th className="border border-slate-200 px-3 py-2 w-40">메뉴 경로 (이전 → 현재)</th>
            <th className="border border-slate-200 px-3 py-2">항목 및 로직 라인 수 비교</th>
          </tr>
        </thead>
        <tbody>
          {allIds.map((id) => {
            const oldS = oldScreens.find((s: any) => s.screen_id === id);
            const newS = newScreens.find((s: any) => s.screen_id === id);

            if (!oldS) {
              return (
                <tr key={id} className="bg-emerald-50 text-emerald-800">
                  <td className="border border-slate-200 px-3 py-2 font-mono font-bold">{id}</td>
                  <td className="border border-slate-200 px-3 py-2 font-bold">{newS.screen_name} [추가]</td>
                  <td className="border border-slate-200 px-3 py-2">{newS.menu_path}</td>
                  <td className="border border-slate-200 px-3 py-2">
                    항목정의: {newS.fields?.length || 0}개 · 처리로직: {newS.logic?.length || 0}줄
                  </td>
                </tr>
              );
            }
            if (!newS) {
              return (
                <tr key={id} className="bg-red-50 text-red-800 line-through">
                  <td className="border border-slate-200 px-3 py-2 font-mono">{id}</td>
                  <td className="border border-slate-200 px-3 py-2">{oldS.screen_name} [삭제]</td>
                  <td className="border border-slate-200 px-3 py-2">{oldS.menu_path}</td>
                  <td className="border border-slate-200 px-3 py-2">
                    항목정의: {oldS.fields?.length || 0}개 · 처리로직: {oldS.logic?.length || 0}줄
                  </td>
                </tr>
              );
            }

            const nameChanged = oldS.screen_name !== newS.screen_name;
            const pathChanged = oldS.menu_path !== newS.menu_path;
            const fieldsCountChanged = (oldS.fields?.length || 0) !== (newS.fields?.length || 0);
            const logicCountChanged = (oldS.logic?.length || 0) !== (newS.logic?.length || 0);
            const changed = nameChanged || pathChanged || fieldsCountChanged || logicCountChanged;

            return (
              <tr key={id} className={changed ? "bg-amber-50/40" : ""}>
                <td className="border border-slate-200 px-3 py-2 font-mono text-slate-500">{id}</td>
                <td className="border border-slate-200 px-3 py-2">
                  {nameChanged ? (
                    <div>
                      <span className="text-red-600 line-through mr-1.5">{oldS.screen_name}</span>
                      <span className="text-emerald-700 font-bold">{newS.screen_name}</span>
                    </div>
                  ) : (
                    newS.screen_name
                  )}
                </td>
                <td className="border border-slate-200 px-3 py-2">
                  {pathChanged ? (
                    <div>
                      <span className="text-red-600 line-through mr-1.5">{oldS.menu_path}</span>
                      <span className="text-emerald-700 font-medium">{newS.menu_path}</span>
                    </div>
                  ) : (
                    newS.menu_path
                  )}
                </td>
                <td className="border border-slate-200 px-3 py-2">
                  <div className="flex flex-col gap-0.5">
                    <span>
                      항목정의:{" "}
                      {fieldsCountChanged ? (
                        <>
                          <span className="text-red-500 line-through mr-1">
                            {oldS.fields?.length || 0}
                          </span>
                          <span className="text-emerald-700 font-semibold">
                            {newS.fields?.length || 0}
                          </span>
                        </>
                      ) : (
                        newS.fields?.length || 0
                      )}
                      개
                    </span>
                    <span>
                      처리로직:{" "}
                      {logicCountChanged ? (
                        <>
                          <span className="text-red-500 line-through mr-1">
                            {oldS.logic?.length || 0}
                          </span>
                          <span className="text-emerald-700 font-semibold">
                            {newS.logic?.length || 0}
                          </span>
                        </>
                      ) : (
                        newS.logic?.length || 0
                      )}
                      줄
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ───────────────── 일반 JSON 원본 비교 (Proposal/Manual용) ───────────────── */
function GenericJsonDiff({ oldSpec, newSpec }: { oldSpec: any; newSpec: any }) {
  const oldStr = JSON.stringify(oldSpec, null, 2);
  const newStr = JSON.stringify(newSpec, null, 2);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
      <div className="flex flex-col gap-1 border border-slate-200 rounded p-2 bg-slate-50">
        <span className="font-semibold text-slate-500">버전 비교 대상 (과거)</span>
        <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap text-[10px] text-red-800 bg-red-50/50 p-2 border border-red-100 rounded">
          {oldStr}
        </pre>
      </div>
      <div className="flex flex-col gap-1 border border-slate-200 rounded p-2 bg-slate-50">
        <span className="font-semibold text-slate-500">최신 버전 (현재)</span>
        <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap text-[10px] text-emerald-800 bg-emerald-50/50 p-2 border border-emerald-100 rounded">
          {newStr}
        </pre>
      </div>
    </div>
  );
}
