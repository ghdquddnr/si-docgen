"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import {
  ApiError,
  createJob,
  eventsUrl,
  getTemplateLibrary,
  type CoverInfo,
  type ProgressEvent,
  type TemplateLibrary,
} from "@/lib/api";
import { MODEL_PRESETS, type DocMenu } from "@/lib/menus";

const STAGE_LABELS: Record<string, string> = {
  queued: "대기 중",
  parsing: "원천 문서 분석",
  proposal: "제안서 생성",
  requirements: "요구사항정의서 생성",
  scenario: "테스트시나리오 생성",
  screens: "화면정의서 생성",
  wbs: "WBS 생성",
  table_spec: "테이블정의서 생성",
  interface_spec: "인터페이스정의서 생성",
  user_manual: "사용자 매뉴얼 생성",
  done: "완료",
  error: "실패",
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function GenerateFlow({ menu }: { menu: DocMenu }) {
  const [jobId, setJobId] = useState<string | null>(null);

  if (!menu.available) {
    return (
      <div className="card flex flex-col items-start gap-3 p-6">
        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
          준비 중
        </span>
        <p className="text-sm text-slate-600">
          {menu.title} 생성 기능은 곧 제공될 예정입니다. ({menu.input} → {menu.output})
        </p>
        <Link href="/" className="btn-secondary">
          대시보드로
        </Link>
      </div>
    );
  }

  return jobId === null ? (
    <UploadForm menu={menu} onCreated={setJobId} />
  ) : (
    <JobTracker menu={menu} jobId={jobId} onReset={() => setJobId(null)} />
  );
}

function UploadForm({ menu, onCreated }: { menu: DocMenu; onCreated: (id: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [cover, setCover] = useState<CoverInfo>({
    project_name: "",
    system_name: "",
    author: "",
    written_date: today(),
    client: "",
  });
  const [model, setModel] = useState("");
  const [startDate, setStartDate] = useState(today());
  const [library, setLibrary] = useState<TemplateLibrary | null>(null);
  const [templateIds, setTemplateIds] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTemplateLibrary()
      .then(setLibrary)
      .catch(() => setLibrary(null));
  }, []);

  // 이 메뉴가 만드는 종류 중 양식 보관함이 지원하는 것만 (라벨 포함)
  const pickerKinds = (library?.kinds ?? []).filter((k) => menu.kinds.includes(k.kind));

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("원천 문서를 선택하세요.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const selected = Object.fromEntries(
        Object.entries(templateIds).filter(([, v]) => v),
      );
      const job = await createJob(file, cover, {
        ...menu.build(model, startDate),
        templateIds: selected,
      });
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
        value={cover[key] ?? ""}
        onChange={(e) => setCover({ ...cover, [key]: e.target.value })}
        className="field-input"
      />
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="card flex flex-col gap-6 p-6">
      <div className="flex items-start gap-3 rounded-lg bg-slate-50 p-4">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white">
          <Icon name={menu.icon} className="h-5 w-5" />
        </span>
        <div className="text-sm">
          <p className="font-medium text-slate-800">{menu.title}</p>
          <p className="text-slate-500">
            입력: {menu.input} · 산출물: {menu.output}
          </p>
        </div>
      </div>

      <div>
        <label className="field-label">원천 문서</label>
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center transition-colors hover:border-indigo-400 hover:bg-indigo-50/40">
          <Icon name="requirement" className="h-7 w-7 text-slate-400" />
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
        {field(menu.needsClient ? "제안사" : "작성자", "author")}
        {field("작성일", "written_date", "date")}
        {menu.needsClient && field("발주처", "client")}
        {menu.needsStartDate && (
          <div>
            <label className="field-label">WBS 시작일</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="field-input"
            />
          </div>
        )}
        <div>
          <label className="field-label">생성 모델</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="field-input"
          >
            {MODEL_PRESETS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {pickerKinds.length > 0 && (
        <div className="flex flex-col gap-3 rounded-lg border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-600">양식 선택</p>
            <Link href="/templates" className="text-xs text-indigo-600 hover:text-indigo-700">
              양식 보관함 관리 →
            </Link>
          </div>
          {pickerKinds.map((k) => {
            const options = (library?.templates ?? []).filter((t) => t.kind === k.kind);
            return (
              <label key={k.kind} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-500">{k.label}</span>
                <select
                  value={templateIds[k.kind] ?? ""}
                  onChange={(e) =>
                    setTemplateIds((s) => ({ ...s, [k.kind]: e.target.value }))
                  }
                  className="w-56 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-100"
                >
                  <option value="">기본 양식</option>
                  {options.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
            );
          })}
        </div>
      )}

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <button type="submit" disabled={submitting} className="btn-primary">
        {submitting ? "업로드 중…" : "생성 시작"}
      </button>
    </form>
  );
}

function JobTracker({
  menu,
  jobId,
  onReset,
}: {
  menu: DocMenu;
  jobId: string;
  onReset: () => void;
}) {
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
  const failed = status === "failed";
  const done = status === "succeeded";
  const stage = state?.progress ?? "queued";

  return (
    <div className="card flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-400">{menu.title} · 잡 ID</p>
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

      {!done && !failed && (
        <p className="flex items-center gap-2 text-sm text-slate-600">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-600" />
          {STAGE_LABELS[stage] ?? "생성 중"}… (로컬 모델은 단계당 1~2분 걸릴 수 있습니다)
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
              새로 생성
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
