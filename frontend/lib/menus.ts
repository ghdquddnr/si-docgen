// 문서별 생성 메뉴 카탈로그 — 사이드바·대시보드·생성 화면이 공유하는 단일 정의.

import type { CreateJobOptions } from "./api";

export const MODEL_PRESETS = [
  { value: "", label: "기본 (설정값)" },
  { value: "ollama/gemma4:e4b", label: "gemma4:e4b (로컬)" },
  { value: "ollama/gemma4:12b", label: "gemma4:12b (로컬)" },
  { value: "ollama/qwen3:14b", label: "qwen3:14b (로컬)" },
  { value: "anthropic/claude-sonnet-4-6", label: "claude-sonnet (상용)" },
];

export type IconName =
  | "dashboard"
  | "proposal"
  | "requirement"
  | "test"
  | "wbs"
  | "table"
  | "interface"
  | "manual";

export type MenuKey =
  | "proposal"
  | "requirement"
  | "test-design"
  | "wbs"
  | "table-spec"
  | "interface-spec"
  | "user-manual";

export interface DocMenu {
  key: MenuKey;
  title: string;
  group: string; // SI 단계 그룹
  input: string; // 입력 문서 안내
  output: string; // 산출물 설명
  icon: IconName;
  needsStartDate?: boolean;
  available: boolean; // 제안서는 C4 에서 제공 → false 면 '준비 중'
  build: (model: string, startDate: string) => CreateJobOptions;
}

// 사이드바 그룹 표시 순서
export const MENU_GROUPS = ["제안", "분석", "설계", "계획", "인도"] as const;

export const MENUS: DocMenu[] = [
  {
    key: "proposal",
    title: "제안서",
    group: "제안",
    input: "RFP(제안요청서)",
    output: "제안서 PPTX 초안",
    icon: "proposal",
    available: false,
    build: () => ({}),
  },
  {
    key: "requirement",
    title: "요구사항정의서",
    group: "분석",
    input: "RFP · 회의록 등 원천 문서",
    output: "요구사항정의서 docx",
    icon: "requirement",
    available: true,
    build: (model) => ({ withRequirements: true, requirementSpecModel: model }),
  },
  {
    key: "test-design",
    title: "테스트 설계",
    group: "설계",
    input: "요구사항정의서",
    output: "화면정의서 + 테스트시나리오 + RTM (추적성)",
    icon: "test",
    available: true,
    build: (model) => ({
      withScreens: true,
      scenarioModel: model,
      screenSpecModel: model,
    }),
  },
  {
    key: "table-spec",
    title: "테이블정의서",
    group: "설계",
    input: "요구사항정의서",
    output: "테이블정의서 xlsx",
    icon: "table",
    available: true,
    build: (model) => ({ withTableSpec: true, tableSpecModel: model }),
  },
  {
    key: "interface-spec",
    title: "인터페이스정의서",
    group: "설계",
    input: "요구사항정의서",
    output: "인터페이스정의서 xlsx",
    icon: "interface",
    available: true,
    build: (model) => ({ withInterfaceSpec: true, interfaceSpecModel: model }),
  },
  {
    key: "wbs",
    title: "WBS",
    group: "계획",
    input: "요구사항정의서",
    output: "WBS xlsx (일정·공수)",
    icon: "wbs",
    needsStartDate: true,
    available: true,
    build: (model, startDate) => ({ withWbs: true, wbsModel: model, startDate }),
  },
  {
    key: "user-manual",
    title: "사용자 매뉴얼",
    group: "인도",
    input: "요구사항정의서 · 화면정의서",
    output: "사용자 매뉴얼 docx (화면 캡처 삽입)",
    icon: "manual",
    available: true,
    build: (model) => ({ withUserManual: true, userManualModel: model }),
  },
];

export function getMenu(key: string): DocMenu | undefined {
  return MENUS.find((m) => m.key === key);
}
