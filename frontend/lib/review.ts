// 검수 편집기 공용 헬퍼.

// 기존 ID 목록에서 다음 순번 ID 를 만든다 (예: ["REQ-001","REQ-010"] → "REQ-011").
// prefix 는 "REQ-"/"SCR-"/"TC-" 처럼 하이픈까지 포함한다.
export function nextNumberedId(existing: string[], prefix: string, pad = 3): string {
  let max = 0;
  const re = new RegExp(`^${prefix}(\\d+)$`);
  for (const id of existing) {
    const m = re.exec(id);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  return `${prefix}${String(max + 1).padStart(pad, "0")}`;
}
