"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Icon } from "@/components/Icon";
import { MENU_GROUPS, MENUS } from "@/lib/menus";

export default function Sidebar() {
  const pathname = usePathname();
  const dashboardActive = pathname === "/";

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      <Link href="/" className="flex items-center gap-2.5 px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
          S
        </span>
        <span className="flex flex-col leading-tight">
          <span className="text-sm font-semibold tracking-tight text-slate-900">si-docgen</span>
          <span className="text-[11px] text-slate-400">SI 산출물 생성기</span>
        </span>
      </Link>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        <Link
          href="/"
          className={`mb-1 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
            dashboardActive
              ? "bg-indigo-50 font-medium text-indigo-700"
              : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
          }`}
        >
          <Icon name="dashboard" className="h-[18px] w-[18px]" />
          대시보드
        </Link>

        {MENU_GROUPS.map((group) => {
          const items = MENUS.filter((m) => m.group === group);
          if (items.length === 0) return null;
          return (
            <div key={group} className="mt-4">
              <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-wider text-slate-400">
                {group}
              </p>
              {items.map((m) => {
                const active = pathname === `/generate/${m.key}`;
                return (
                  <Link
                    key={m.key}
                    href={`/generate/${m.key}`}
                    className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                      active
                        ? "bg-indigo-50 font-medium text-indigo-700"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    }`}
                  >
                    <Icon name={m.icon} className="h-[18px] w-[18px]" />
                    <span className="flex-1 truncate">{m.title}</span>
                    {!m.available && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-400">
                        준비 중
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          );
        })}
        <div className="mt-4 border-t border-slate-100 pt-3">
          <Link
            href="/templates"
            className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
              pathname === "/templates"
                ? "bg-indigo-50 font-medium text-indigo-700"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <Icon name="table" className="h-[18px] w-[18px]" />
            양식 보관함
          </Link>
        </div>
      </nav>

      <div className="border-t border-slate-200 px-5 py-3">
        <p className="text-[11px] text-slate-400">AI 초안 생성 + 사람 검수</p>
        <p className="text-[11px] text-slate-400">생성물은 검수 후 사용하세요</p>
      </div>
    </aside>
  );
}
