"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, createJob, eventsUrl, type CoverInfo, type ProgressEvent } from "@/lib/api";

const STEPS = [
  { key: "parsing", label: "원천 문서 분석" },
  { key: "generating", label: "AI 시나리오 생성" },
  { key: "done", label: "생성 완료" },
];

function stepIndex(progress: string | null, status: string): number {
  if (status === "succeeded") return 2;
  if (progress === "generating") return 1;
  if (progress === "parsing" || progress === "queued") return 0;
  return 0;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function HomePage() {
  const [jobId, setJobId] = useState<string | null>(null);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-6 py-12">
      <header className="space-y-1.5">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
          산출물 생성
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          원천 문서로 산출물 초안 만들기
        </h1>
        <p className="text-sm text-slate-500">
          요구사항정의서 등 원천 문서를 올리면 테스트시나리오와 요건추적표(RTM) 초안을 생성합니다.
          생성 후 검수 화면에서 편집·다운로드할 수 있습니다.
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
    <div>
      <label className="field-label">{label}</label>
      <input
        type={type}
        value={cover[key]}
        onChange={(e) => setCover({ ...cover, [key]: e.target.value })}
        className="field-input"
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="card flex flex-col gap-6 p-6">
      <div>
        <label className="field-label">원천 문서</label>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center transition-colors hover:border-indigo-400 hover:bg-indigo-50/40">
          <svg
            className="h-7 w-7 text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
            />
          </svg>
          <span className="text-sm font-medium text-slate-700">
            {file ? file.name : "클릭하여 파일 선택"}
          </span>
          <span className="text-xs text-slate-400">.docx · .pdf · .md · .txt</span>
          <input
            type="file"
            accept=".docx,.pdf,.md,.markdown,.txt"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="hidden"
          />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {field("프로젝트명", "project_name")}
        {field("시스템명", "system_name")}
        {field("작성자", "author")}
        {field("작성일", "written_date", "date")}
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <button type="submit" disabled={submitting} className="btn-primary">
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
    source.addEventListener("error", () => source.close());
    return () => source.close();
  }, [jobId]);

  const status = state?.status ?? "pending";
  const active = stepIndex(state?.progress ?? null, status);
  const failed = status === "failed";
  const done = status === "succeeded";

  return (
    <div className="card flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-400">잡 ID</p>
          <p className="font-mono text-sm text-slate-600">{jobId}</p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${
            done
              ? "bg-emerald-50 text-emerald-700"
              : failed
                ? "bg-red-50 text-red-700"
                : "bg-indigo-50 text-indigo-700"
          }`}
        >
          {done ? "완료" : failed ? "실패" : "진행 중"}
        </span>
      </div>

      {!failed && (
        <ol className="flex items-center">
          {STEPS.map((step, i) => {
            const reached = i < active || (i === active && done) || i < active;
            const current = i === active && !done;
            return (
              <li key={step.key} className="flex flex-1 items-center last:flex-none">
                <div className="flex flex-col items-center gap-1.5">
                  <span
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${
                      i < active || done
                        ? "bg-indigo-600 text-white"
                        : current
                          ? "border-2 border-indigo-600 bg-white text-indigo-600"
                          : "border-2 border-slate-200 bg-white text-slate-400"
                    }`}
                  >
                    {i < active || (done && i <= active) ? "✓" : i + 1}
                  </span>
                  <span
                    className={`whitespace-nowrap text-xs ${
                      reached || current ? "font-medium text-slate-700" : "text-slate-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <span
                    className={`mx-2 mb-5 h-0.5 flex-1 ${
                      i < active || done ? "bg-indigo-600" : "bg-slate-200"
                    }`}
                  />
                )}
              </li>
            );
          })}
        </ol>
      )}

      {!done && !failed && (
        <p className="flex items-center gap-2 text-sm text-slate-600">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-600" />
          {active === 1 ? "AI가 시나리오를 생성하고 있습니다… (1~2분)" : "원천 문서를 분석하고 있습니다…"}
        </p>
      )}

      {done && (
        <div className="flex flex-col gap-4 rounded-lg bg-emerald-50 p-4">
          <p className="text-sm font-medium text-emerald-800">
            생성이 완료되었습니다. 검수 화면에서 내용을 확인·편집한 뒤 다운로드하세요.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href={`/jobs/${jobId}`} className="btn-primary">
              검수 화면으로 →
            </Link>
            <button onClick={onReset} className="btn-secondary">
              새 문서 생성
            </button>
          </div>
        </div>
      )}

      {failed && (
        <div className="flex flex-col gap-4 rounded-lg bg-red-50 p-4">
          <p className="text-sm text-red-700">생성 실패: {state?.error ?? "알 수 없는 오류"}</p>
          <button onClick={onReset} className="btn-secondary self-start">
            다시 시도
          </button>
        </div>
      )}
    </div>
  );
}
