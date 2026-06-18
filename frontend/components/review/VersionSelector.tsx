/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useCallback, useEffect, useState } from "react";
import { getJobVersions, rollbackJobSpec, type Job, type JobVersion } from "@/lib/api";
import { DiffViewerModal } from "./DiffViewerModal";

interface VersionSelectorProps {
  jobId: string;
  specType: string;
  onRollback: (nextJob: Job) => void;
}

export function VersionSelector({ jobId, specType, onRollback }: VersionSelectorProps) {
  const [versions, setVersions] = useState<JobVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | "">("");
  const [isDiffOpen, setIsDiffOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchVersions = useCallback(async () => {
    try {
      const list = await getJobVersions(jobId, specType);
      setVersions(list);
      if (list.length > 0) {
        // 드롭다운의 기본값은 항상 가장 최신 버전(첫 번째 요소)
        setSelectedVersion(list[0].version);
      }
    } catch (e) {
      console.error("버전 리스트 획득 실패:", e);
    }
  }, [jobId, specType]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  const maxVersion = versions.length > 0 ? Math.max(...versions.map((v) => v.version)) : 1;
  const showActions = selectedVersion !== "" && selectedVersion !== maxVersion;

  async function handleRollback() {
    if (selectedVersion === "" || !confirm(`정말 버전 ${selectedVersion} 상태로 복구하시겠습니까?`)) {
      return;
    }
    setLoading(true);
    try {
      const nextJob = await rollbackJobSpec(jobId, Number(selectedVersion), specType);
      alert("성공적으로 복구되었습니다.");
      onRollback(nextJob);
      // 복구 후 버전 리스트 다시 불러오기
      await fetchVersions();
    } catch (e) {
      alert(e instanceof Error ? `복구 실패: ${e.message}` : "복구에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-700">
      <div className="flex items-center gap-1.5">
        <span className="font-semibold text-slate-500">버전 내역:</span>
        <select
          value={selectedVersion}
          onChange={(e) => setSelectedVersion(Number(e.target.value))}
          className="rounded border border-slate-300 bg-white px-2 py-1 focus:border-indigo-500 focus:outline-none"
        >
          {versions.map((v) => (
            <option key={v.version} value={v.version}>
              버전 {v.version} ({new Date(v.created_at).toLocaleString()} - {v.updated_by}) {v.version === maxVersion ? "(현재)" : ""}
            </option>
          ))}
        </select>
      </div>

      {showActions && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsDiffOpen(true)}
            className="rounded border border-slate-300 bg-white px-2.5 py-1 font-semibold text-slate-600 hover:bg-slate-100"
          >
            현재 버전과 비교 (Diff)
          </button>
          <button
            onClick={handleRollback}
            disabled={loading}
            className="rounded bg-indigo-600 px-2.5 py-1 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "복구 중..." : "이 버전으로 복구"}
          </button>
        </div>
      )}

      {isDiffOpen && selectedVersion !== "" && (
        <DiffViewerModal
          jobId={jobId}
          specType={specType}
          compareVersion={Number(selectedVersion)}
          onClose={() => setIsDiffOpen(false)}
        />
      )}
    </div>
  );
}
