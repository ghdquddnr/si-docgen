"use client";

import { usePathname } from "next/navigation";

import { getMenu } from "@/lib/menus";

function titleFor(pathname: string): string {
  if (pathname === "/") return "대시보드";
  if (pathname.startsWith("/generate/")) {
    const key = pathname.split("/")[2] ?? "";
    return getMenu(key)?.title ?? "문서 생성";
  }
  if (pathname.startsWith("/jobs/")) return "검수";
  return "si-docgen";
}

export default function Topbar() {
  const pathname = usePathname();
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white/90 px-6 backdrop-blur">
      <h1 className="text-sm font-semibold tracking-tight text-slate-900">{titleFor(pathname)}</h1>
      <a
        href="https://github.com"
        target="_blank"
        rel="noreferrer"
        className="text-xs text-slate-400 transition-colors hover:text-slate-600"
      >
        문서 자동 생성 워크스페이스
      </a>
    </header>
  );
}
