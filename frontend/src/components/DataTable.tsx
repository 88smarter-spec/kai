import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Row } from "../types";
export function format(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number")
    return value.toLocaleString("ko-KR", { maximumFractionDigits: 4 });
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
export function DataTable({
  rows,
  columns,
  total,
  offset = 0,
  onPage,
}: {
  rows: Row[];
  columns: string[];
  total?: number;
  offset?: number;
  onPage?: (offset: number) => void;
}) {
  const [local, setLocal] = useState(0);
  useEffect(() => setLocal(0), [rows]);
  const start = onPage ? offset : local;
  const shown = onPage ? rows : rows.slice(local, local + 50);
  const count = total ?? rows.length;
  const change = (next: number) => (onPage ? onPage(next) : setLocal(next));
  const max = onPage ? count : rows.length;
  return (
    <div className="table-wrap">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col" className="row-index">
                #
              </th>
              {columns.map((c) => (
                <th scope="col" key={c}>
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((row, i) => (
              <tr key={i}>
                <td className="row-index">{start + i + 1}</td>
                {columns.map((c) => (
                  <td
                    key={c}
                    className={typeof row[c] === "number" ? "numeric" : ""}
                  >
                    {format(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {!shown.length && (
          <div className="empty-table">해당하는 행이 없습니다.</div>
        )}
      </div>
      <div className="table-footer">
        <span>
          {count.toLocaleString()}행 중{" "}
          {shown.length ? `${start + 1}–${start + shown.length}` : "0"}행 표시
          {!onPage && count > rows.length ? " · 결과 상위 500행만 제공" : ""}
        </span>
        <div className="page-controls">
          <button
            aria-label="이전 페이지"
            disabled={start === 0}
            onClick={() => change(Math.max(0, start - 50))}
          >
            <ChevronLeft size={16} />
          </button>
          <span>{Math.floor(start / 50) + 1}</span>
          <button
            aria-label="다음 페이지"
            disabled={start + 50 >= max}
            onClick={() => change(start + 50)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
