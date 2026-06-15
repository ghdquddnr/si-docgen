"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { use } from "react";

import GenerateFlow from "@/components/generate/GenerateFlow";
import { getMenu } from "@/lib/menus";

export default function GeneratePage({ params }: { params: Promise<{ key: string }> }) {
  const { key } = use(params);
  const menu = getMenu(key);
  if (!menu) notFound();

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6 px-6 py-8">
      <div className="space-y-1.5">
        <Link href="/" className="text-xs text-slate-400 transition-colors hover:text-slate-600">
          ← 대시보드
        </Link>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">{menu.title}</h2>
        <p className="text-sm text-slate-500">
          {menu.input}을(를) 업로드하면 {menu.output} 초안을 생성합니다. 생성 후 검수 화면에서
          편집·다운로드할 수 있습니다.
        </p>
      </div>
      <GenerateFlow menu={menu} />
    </div>
  );
}
