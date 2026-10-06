import { useState, useEffect } from "react";
import { Play } from "lucide-react";
import type { Detail, Dataset, Operation, Plan } from "../types";
export const operationLabels: Record<Operation, string> = {
  describe: "기초 통계 (Describe)",
  groupby: "범주별 집계 (Groupby)",
  aggregate: "전체 집계",
  pivot: "피벗 테이블",
  filter: "필터",
  sort: "정렬",
  top_n: "상위 N",
  bottom_n: "하위 N",
  difference: "차이 / GAP",
  ratio: "비율",
  growth_rate: "증감률",
  moving_average: "이동평균",
  correlation: "상관관계",
  outliers: "이상치 탐지",
  trend: "추세",
  join: "데이터셋 JOIN",
  missing: "결측값 분석",
  duplicates: "중복 행 분석",
  regression: "단순 회귀",
};
export function AnalysisTools({
  detail,
  datasets,
  onRun,
  busy,
}: {
  detail: Detail;
  datasets: Dataset[];
  onRun: (p: Plan) => void;
  busy: boolean;
}) {
  const [op, setOp] = useState<Operation>("groupby"),
    [a, setA] = useState(""),
    [b, setB] = useState(""),
    [group, setGroup] = useState(""),
    [time, setTime] = useState(""),
    [agg, setAgg] = useState("sum"),
    [other, setOther] = useState(""),
    [joinKeys, setJoinKeys] = useState(""),
    [joinHow, setJoinHow] = useState("inner"),
    [n, setN] = useState(10),
    [window, setWindow] = useState(3),
    [value, setValue] = useState(""),
    [filterOp, setFilterOp] = useState("eq"),
    [filterCol, setFilterCol] = useState(""),
    [ascending, setAscending] = useState(false),
    [outlier, setOutlier] = useState("iqr");
  const cols = detail.columns,
    nums = detail.profile.numeric_columns;
  useEffect(() => {
    setA(nums[0] || cols[0] || "");
    setB(nums[1] || cols[1] || "");
    setGroup(detail.profile.categorical_columns[0] || cols[0] || "");
    setTime(
      detail.profile.date_columns[0] ||
        cols.find((c) => c.includes("월")) ||
        cols[0] ||
        "",
    );
    setFilterCol(cols[0] || "");
    setJoinKeys("");
    setOther("");
  }, [detail.id]);
  const pair = ["difference", "ratio", "correlation", "regression"].includes(
      op,
    ),
    one = [
      "groupby",
      "aggregate",
      "pivot",
      "sort",
      "top_n",
      "bottom_n",
      "growth_rate",
      "moving_average",
      "outliers",
      "trend",
    ].includes(op),
    grouped = [
      "groupby",
      "pivot",
      "trend",
      "growth_rate",
      "moving_average",
    ].includes(op),
    timed = ["trend", "growth_rate", "moving_average"].includes(op);
  function run() {
    const p: Plan = { dataset: detail.id, operation: op };
    if (pair) p.columns = [a, b];
    else if (one) p.columns = [a];
    if (grouped && group) p.group_by = [group];
    if (["groupby", "aggregate", "pivot"].includes(op))
      p.metrics = { [a]: agg };
    if (timed) p.time_column = time;
    if (op === "pivot") p.pivot_column = time;
    if (["top_n", "bottom_n"].includes(op)) p.n = n;
    if (op === "sort") p.ascending = ascending;
    if (op === "moving_average") p.window = window;
    if (op === "outliers") p.outlier_method = outlier;
    if (op === "join") {
      p.other_dataset = other;
      p.join_keys = joinKeys
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      p.join_how = joinHow;
    }
    if (op === "filter" && filterCol) {
      const numeric = nums.includes(filterCol);
      p.filters = [
        {
          column: filterCol,
          operator: filterOp,
          value:
            filterOp === "in"
              ? value.split(",").map((x) => (numeric ? Number(x) : x.trim()))
              : numeric && value !== ""
                ? Number(value)
                : value,
        },
      ];
    }
    onRun(p);
  }
  const colSelect = (
    label: string,
    val: string,
    set: (v: string) => void,
    empty = false,
  ) => (
    <label className="field">
      {label}
      <select value={val} onChange={(e) => set(e.target.value)}>
        {empty && <option value="">그룹 없음</option>}
        {cols.map((c) => (
          <option key={c}>{c}</option>
        ))}
      </select>
    </label>
  );
  return (
    <div className="tool-panel">
      <div className="tool-grid">
        <label className="field">
          분석 도구
          <select
            value={op}
            onChange={(e) => setOp(e.target.value as Operation)}
          >
            {Object.entries(operationLabels).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {(one || pair) &&
          colSelect(pair ? "첫 번째 컬럼" : "분석 컬럼", a, setA)}
        {pair && colSelect("두 번째 컬럼", b, setB)}
        {grouped && colSelect("그룹 기준", group, setGroup, true)}
        {(timed || op === "pivot") &&
          colSelect(
            op === "pivot" ? "피벗 열 기준" : "시간 기준",
            time,
            setTime,
          )}
        {["groupby", "aggregate", "pivot"].includes(op) && (
          <label className="field">
            집계 함수
            <select value={agg} onChange={(e) => setAgg(e.target.value)}>
              {["sum", "mean", "median", "min", "max", "count", "std"].map(
                (x) => (
                  <option key={x}>{x}</option>
                ),
              )}
            </select>
          </label>
        )}
        {["top_n", "bottom_n"].includes(op) && (
          <label className="field">
            N
            <input
              type="number"
              min="1"
              max="500"
              value={n}
              onChange={(e) => setN(Number(e.target.value))}
            />
          </label>
        )}
        {op === "moving_average" && (
          <label className="field">
            이동평균 구간
            <input
              type="number"
              min="1"
              max="100"
              value={window}
              onChange={(e) => setWindow(Number(e.target.value))}
            />
          </label>
        )}
        {op === "sort" && (
          <label className="field">
            정렬 방향
            <select
              value={String(ascending)}
              onChange={(e) => setAscending(e.target.value === "true")}
            >
              <option value="false">내림차순</option>
              <option value="true">오름차순</option>
            </select>
          </label>
        )}
        {op === "outliers" && (
          <label className="field">
            방법
            <select
              value={outlier}
              onChange={(e) => setOutlier(e.target.value)}
            >
              <option value="iqr">IQR (1.5×)</option>
              <option value="zscore">Z-score (3σ)</option>
            </select>
          </label>
        )}
        {op === "filter" && (
          <>
            {colSelect("필터 컬럼", filterCol, setFilterCol)}
            <label className="field">
              조건
              <select
                value={filterOp}
                onChange={(e) => setFilterOp(e.target.value)}
              >
                {[
                  "eq",
                  "ne",
                  "gt",
                  "ge",
                  "lt",
                  "le",
                  "contains",
                  "in",
                  "is_null",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label className="field">
              필터 값
              <input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="값 / in은 쉼표 목록"
              />
            </label>
          </>
        )}
        {op === "join" && (
          <>
            <label className="field">
              결합할 데이터셋
              <select value={other} onChange={(e) => setOther(e.target.value)}>
                <option value="">선택하세요</option>
                {datasets
                  .filter((d) => d.id !== detail.id)
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field">
              JOIN KEY (쉼표 구분)
              <input
                value={joinKeys}
                onChange={(e) => setJoinKeys(e.target.value)}
                placeholder="사업, 월"
              />
            </label>
            <label className="field">
              JOIN 방식
              <select
                value={joinHow}
                onChange={(e) => setJoinHow(e.target.value)}
              >
                <option value="inner">Inner</option>
                <option value="left">Left</option>
                <option value="outer">Outer</option>
              </select>
            </label>
          </>
        )}
      </div>
      {pair && ["difference", "ratio"].includes(op) && (
        <p className="muted small">
          계산식: {a} {op === "difference" ? "−" : "÷"} {b}
          {op === "ratio" ? " (비율, % 아님)" : ""}
        </p>
      )}
      {op === "join" && (
        <p className="notice">
          실행할 JOIN KEY: {joinKeys || "아직 선택하지 않음"} · 중복 키로 행이
          증가할 수 있습니다.
        </p>
      )}
      <button className="button primary" onClick={run} disabled={busy}>
        <Play size={15} />
        {busy ? "분석 중…" : "분석 실행"}
      </button>
    </div>
  );
}
