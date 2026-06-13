"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, createJob, eventsUrl, type CoverInfo, type ProgressEvent } from "@/lib/api";

const PROGRESS_LABEL: Record<string, string> = {
  queued: "대기 중",
  parsing: "원천 문서 분석 중",
  generating: "AI 시나리오 생성 중",
  done: "생성 완료",
  error: "실패",
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function HomePage() {
  const [jobId, setJobId] = useState<string | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-12">
      <header>
        <h1 className="text-2xl font-bold">SI 산출물 생성기</h1>
        <p className="mt-1 text-sm text-gray-500">
          요구사항정의서 등 원천 문서를 올리면 테스트시나리오와 요건추적표(RTM) 초안을 생성합니다.
        </p>
      </header>

      {jobId === null ? (
        <UploadForm onCreated={setJobId} />
      ) : (
        <JobTracker jobId={jobId} onReset={() => setJobId(null)} />
      )}
    </main>
  );
}

function UploadForm({ onCreated }: { onCreated: (jobId: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [cover, setCover] = useState<CoverInfo>({
    project_name: "",
    system_name: "",
    author: "",
    written_date: today(),
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("원천 문서를 선택하세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const job = await createJob(file, cover);
      onCreated(job.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "업로드에 실패했습니다.");
      setSubmitting(false);
    }
  }

  const field = (label: string, key: keyof CoverInfo, type = "text") => (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-gray-600">{label}</span>
      <input
        type={type}
        value={cover[key]}
        onChange={(e) => setCover({ ...cover, [key]: e.target.value })}
        className="rounded border border-gray-300 px-3 py-2 outline-none focus:border-gray-900"
      />
    </label>
  );

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <label className="flex flex-col gap-1 text-sm">
        <span className="text-gray-600">원천 문서 (.docx / .pdf / .md / .txt)</span>
        <input
          type="file"
          accept=".docx,.pdf,.md,.markdown,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="rounded border border-gray-300 px-3 py-2 file:mr-3 file:rounded file:border-0 file:bg-gray-100 file:px-3 file:py-1"
        />
      </label>

      <div className="grid grid-cols-2 gap-4">
        {field("프로젝트명", "project_name")}
        {field("시스템명", "system_name")}
        {field("작성자", "author")}
        {field("작성일", "written_date", "date")}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-gray-900 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-50"
      >
        {submitting ? "업로드 중…" : "생성 시작"}
      </button>
    </form>
  );
}

function JobTracker({ jobId, onReset }: { jobId: string; onReset: () => void }) {
  const [state, setState] = useState<ProgressEvent | null>(null);

  useEffect(() => {
    const source = new EventSource(eventsUrl(jobId));
    source.addEventListener("progress", (e) => {
      const data = JSON.parse((e as MessageEvent).data) as ProgressEvent;
      setState(data);
      if (data.terminal) source.close();
    });
    source.addEventListener("error", () => {
      // 스트림 정상 종료를 포함해 연결이 끊기면 EventSource 가 error 를 발생시킨다
      source.close();
    });
    return () => source.close();
  }, [jobId]);

  const status = state?.status ?? "pending";
  const label = state?.progress ? (PROGRESS_LABEL[state.progress] ?? state.progress) : "연결 중…";

  return (
    <section className="flex flex-col gap-5 rounded-lg border border-gray-200 p-6">
      <div>
        <p className="text-xs text-gray-400">잡 ID</p>
        <p className="font-mono text-sm">{jobId}</p>
      </div>

      {status !== "succeeded" && status !== "failed" && (
        <p className="flex items-center gap-2 text-sm text-gray-700">
          <span className="h-2 w-2 animate-pulse rounded-full bg-gray-900" />
          {label}
        </p>
      )}

      {status === "succeeded" && (
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-green-700">
            생성 완료 — 검수 후 다운로드할 수 있습니다.
          </p>
          <Link
            href={`/jobs/${jobId}`}
            className="self-start rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white"
          >
            검수 화면으로
          </Link>
        </div>
      )}

      {status === "failed" && (
        <p className="text-sm text-red-600">생성 실패: {state?.error ?? "알 수 없는 오류"}</p>
      )}

      <button onClick={onReset} className="self-start text-sm text-gray-500 underline">
        새 문서로 다시 시작
      </button>
    </section>
  );
}
