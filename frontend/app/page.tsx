"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listJobs, type Job } from "@/lib/api";

function jobLabel(job: Job): string {
  const parts: string[] = [];
  if (job.with_proposal) parts.push("제안서");
  if (job.with_requirements) parts.push("요구사항정의서");
  if (job.with_screens) parts.push("테스트 설계");
  if (job.with_table_spec) parts.push("테이블정의서");
  if (job.with_interface_spec) parts.push("인터페이스정의서");
  if (job.with_wbs) parts.push("WBS");
  if (job.with_user_manual) parts.push("사용자 매뉴얼");
  return parts.join(", ") || "—";
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(
    d.getMinutes(),
  ).padStart(2, "0")}`;
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[] | null>(null);

  useEffect(() => {
    listJobs(20)
      .then(setJobs)
      .catch(() => setJobs([]));
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-8">
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">대시보드</h2>
        <p className="text-sm text-slate-500">
          왼쪽 메뉴에서 생성할 문서를 선택하세요. 최근 생성한 산출물은 아래에서 검수·다운로드할 수
          있습니다.
        </p>
      </div>

      <section>
        <h3 className="mb-3 text-sm font-semibold text-slate-500">최근 생성 이력</h3>
        <RecentJobs jobs={jobs} />
      </section>
    </div>
  );
}

function StatusBadge({ status }: { status: Job["status"] }) {
  const map: Record<Job["status"], string> = {
    succeeded: "bg-emerald-50 text-emerald-700",
    failed: "bg-red-50 text-red-700",
    running: "bg-indigo-50 text-indigo-700",
    pending: "bg-slate-100 text-slate-500",
  };
  const label: Record<Job["status"], string> = {
    succeeded: "완료",
    failed: "실패",
    running: "진행 중",
    pending: "대기",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${map[status]}`}>
      {label[status]}
    </span>
  );
}

function RecentJobs({ jobs }: { jobs: Job[] | null }) {
  if (jobs === null) {
    return (
      <div className="card flex items-center gap-2 p-5 text-sm text-slate-400">
        <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-600" />
        이력을 불러오는 중…
      </div>
    );
  }
  if (jobs.length === 0) {
    return (
      <div className="card p-5 text-center text-sm text-slate-400">
        아직 생성한 문서가 없습니다. 왼쪽 메뉴에서 문서를 선택해 시작하세요.
      </div>
    );
  }
  return (
    <div className="card overflow-hidden">
      <table className="min-w-full border-collapse text-sm">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-4 py-2.5 font-medium">문서</th>
            <th className="px-4 py-2.5 font-medium">프로젝트</th>
            <th className="px-4 py-2.5 font-medium">생성일</th>
            <th className="px-4 py-2.5 font-medium">상태</th>
            <th className="px-4 py-2.5" />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-t border-slate-100">
              <td className="px-4 py-2.5 font-medium text-slate-700">{jobLabel(job)}</td>
              <td className="px-4 py-2.5 text-slate-500">{job.project_name || "—"}</td>
              <td className="px-4 py-2.5 text-slate-500">{formatDate(job.created_at)}</td>
              <td className="px-4 py-2.5">
                <StatusBadge status={job.status} />
              </td>
              <td className="px-4 py-2.5 text-right">
                {job.status === "succeeded" && (
                  <Link
                    href={`/jobs/${job.id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
                  >
                    검수 →
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
