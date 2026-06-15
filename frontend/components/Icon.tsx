import type { IconName } from "@/lib/menus";

// 의존성 없는 라인 아이콘 세트 (stroke=currentColor). 크기는 className 으로 지정.
const PATHS: Record<IconName | "download" | "back", React.ReactNode> = {
  dashboard: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25A2.25 2.25 0 0 1 8.25 10.5H6A2.25 2.25 0 0 1 3.75 8.25V6Zm0 9.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 8.25 20.25H6A2.25 2.25 0 0 1 3.75 18v-2.25Zm9.75-9.75A2.25 2.25 0 0 1 15.75 3.75H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25A2.25 2.25 0 0 1 13.5 8.25V6Zm0 9.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"
    />
  ),
  proposal: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.75 3.75h16.5M4.5 3.75v9a2.25 2.25 0 0 0 2.25 2.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-9M12 15v5.25m0 0-2.25-1.5m2.25 1.5 2.25-1.5M8.25 8.25l2.25 2.25 4.5-4.5"
    />
  ),
  requirement: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 12h6m-6 3.75h6M9 8.25h6M6.75 3.75h10.5A1.5 1.5 0 0 1 18.75 5.25v13.5a1.5 1.5 0 0 1-1.5 1.5H6.75a1.5 1.5 0 0 1-1.5-1.5V5.25a1.5 1.5 0 0 1 1.5-1.5Z"
    />
  ),
  test: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m9 12.75 1.5 1.5 3-3.75M6.75 3.75h10.5a1.5 1.5 0 0 1 1.5 1.5v13.5a1.5 1.5 0 0 1-1.5 1.5H6.75a1.5 1.5 0 0 1-1.5-1.5V5.25a1.5 1.5 0 0 1 1.5-1.5Z"
    />
  ),
  wbs: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M6.75 3v2.25M17.25 3v2.25M3.75 8.25h16.5M5.25 5.25h13.5a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5v-12a1.5 1.5 0 0 1 1.5-1.5Zm3 6h7.5m-7.5 3.75h4.5"
    />
  ),
  table: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3.75 9h16.5M3.75 14.25h16.5M9 4.5v15M5.25 4.5h13.5a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5v-12a1.5 1.5 0 0 1 1.5-1.5Z"
    />
  ),
  interface: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8.25 7.5 4.5 11.25l3.75 3.75M15.75 7.5l3.75 3.75-3.75 3.75M13.5 5.25l-3 13.5"
    />
  ),
  manual: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 6.75c-1.5-1.125-3.75-1.5-5.25-1.5-.621 0-1.125.504-1.125 1.125v10.5c1.5 0 3.75.375 6.375 1.875M12 6.75c1.5-1.125 3.75-1.5 5.25-1.5.621 0 1.125.504 1.125 1.125v10.5c-1.5 0-3.75.375-6.375 1.875M12 6.75v12"
    />
  ),
  download: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5"
    />
  ),
  back: <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />,
};

export function Icon({
  name,
  className = "h-5 w-5",
}: {
  name: IconName | "download" | "back";
  className?: string;
}) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.6}
      stroke="currentColor"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
