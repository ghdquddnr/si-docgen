"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import { listJobs, type Job } from "@/lib/api";
import { MENU_GROUPS, MENUS, type DocMenu } from "@/lib/menus";

function jobLabel(job: Job): string {
  const parts: string[] = [];
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
    listJobs(8)
      .then(setJobs)
      .catch(() => setJobs([]));
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-8">
      <section>
        <h2 className="mb-1 text-sm font-semibold text-slate-500">문서 생성</h2>
        <p className="mb-4 text-xs text-slate-400">
          SI 단계에 맞는 문서를 선택해 원천 문서를 올리면 초안이 생성됩니다.
        </p>
        <div className="flex flex-col gap-5">
          {MENU_GROUPS.map((group) => {
            const items = MENUS.filter((m) => m.group === group);
            if (items.length === 0) return null;
            return (
              <div key={group}>
                <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-400">
                  {group}
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {items.map((m) => (
                    <MenuCard key={m.key} menu={m} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-500">최근 생성 이력</h2>
        <RecentJobs jobs={jobs} />
      </section>
    </div>
  );
}

function MenuCard({ menu }: { menu: DocMenu }) {
  return (
    <Link
      href={`/generate/${menu.key}`}
      className={`group flex flex-col gap-3 rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50/30 ${
        menu.available ? "border-slate-200" : "border-dashed border-slate-200"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 text-slate-600 group-hover:bg-indigo-600 group-hover:text-white">
          <Icon name={menu.icon} className="h-5 w-5" />
        </span>
        {!menu.available && (
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
            준비 중
          </span>
        )}
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-800">{menu.title}</p>
        <p className="mt-0.5 text-xs text-slate-500">{menu.output}</p>
      </div>
    </Link>
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
        아직 생성한 문서가 없습니다. 위에서 문서를 선택해 시작하세요.
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
