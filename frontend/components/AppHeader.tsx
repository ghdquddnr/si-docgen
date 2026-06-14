import Link from "next/link";

export default function AppHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-sm font-bold text-white">
            S
          </span>
          <span className="flex items-baseline gap-2">
            <span className="text-sm font-semibold tracking-tight text-slate-900">si-docgen</span>
            <span className="hidden text-xs text-slate-400 sm:inline">SI 산출물 생성기</span>
          </span>
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/" className="text-slate-500 transition-colors hover:text-slate-900">
            홈
          </Link>
          <Link href="/canvas" className="text-slate-500 transition-colors hover:text-slate-900">
            캔버스
          </Link>
        </nav>
      </div>
    </header>
  );
}
