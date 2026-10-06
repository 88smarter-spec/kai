import { useEffect, useRef, useState } from "react";
import Plotly from "plotly.js-dist-min";
import type { AnalysisResult } from "../types";
const colors = [
  "#0c8c82",
  "#4285c5",
  "#e5a948",
  "#8b72ba",
  "#d57376",
  "#4d9fa8",
  "#99aa6b",
  "#6379b3",
];
export function Chart({ result }: { result: AnalysisResult }) {
  const ref = useRef<HTMLDivElement>(null);
  const [kind, setKind] = useState("auto");
  const [error, setError] = useState("");
  useEffect(() => setKind("auto"), [result]);
  useEffect(() => {
    if (!ref.current || !result.chart) return;
    const node = ref.current;
    let data: Partial<Plotly.PlotData>[] = result.chart.data.map(
      (trace, i) => ({
        ...trace,
        marker: { color: colors[i % colors.length] },
      }),
    );
    const layout: Partial<Plotly.Layout> = {
      ...result.chart.layout,
      autosize: true,
      height: 340,
      paper_bgcolor: "white",
      plot_bgcolor: "white",
      colorway: colors,
      font: {
        family: "Segoe UI, Malgun Gothic, sans-serif",
        size: 12,
        color: "#536174",
      },
      margin: { l: 60, r: 24, t: 50, b: 60 },
      legend: { orientation: "h", y: 1.12 },
      xaxis: { ...result.chart.layout.xaxis, gridcolor: "#f0f3f6" },
      yaxis: { gridcolor: "#eef1f5", zerolinecolor: "#d6dfe7" },
    };
    if (kind !== "auto") {
      if (kind === "heatmap") {
        const numeric = result.columns.filter((c) =>
          result.rows.some((r) => typeof r[c] === "number"),
        );
        data = [
          {
            type: "heatmap",
            x: numeric,
            y: result.rows.slice(0, 100).map((_, i) => i + 1),
            z: result.rows
              .slice(0, 100)
              .map((r) => numeric.map((c) => r[c] as number)),
            colorscale: "Teal",
          },
        ];
      } else if (kind === "scatter") {
        const cols = result.columns.filter((c) =>
          result.rows.some((r) => typeof r[c] === "number"),
        );
        data = [
          {
            type: "scatter",
            mode: "markers",
            x: result.rows.map((r) => r[cols[0]] as number),
            y: result.rows.map((r) => r[cols[1] || cols[0]] as number),
            name: cols.slice(0, 2).join(" / "),
            marker: { color: colors[0] },
          },
        ];
      } else
        data = data.map((t) =>
          kind === "histogram"
            ? { type: "histogram", x: t.y, name: t.name }
            : kind === "box"
              ? { type: "box", y: t.y, name: t.name }
              : {
                  ...t,
                  type: kind === "line" ? "scatter" : "bar",
                  mode: kind === "line" ? "lines+markers" : undefined,
                },
        );
      layout.barmode = kind === "stacked" ? "stack" : "group";
    }
    setError("");
    Plotly.react(node, data, layout, {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ["sendDataToCloud"] as never,
    }).catch(() =>
      setError(
        "이 결과를 해당 차트로 표시할 수 없습니다. 다른 차트를 선택해주세요.",
      ),
    );
    const observer = new ResizeObserver(() => Plotly.Plots.resize(node));
    observer.observe(node);
    return () => {
      observer.disconnect();
      Plotly.purge(node);
    };
  }, [result, kind]);
  if (!result.chart)
    return (
      <div className="chart-empty">표시할 숫자형 차트 데이터가 없습니다.</div>
    );
  return (
    <div className="chart-card">
      <div className="chart-toolbar">
        <span>Interactive chart</span>
        <select
          aria-label="차트 종류"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="auto">자동 추천</option>
          <option value="line">Line</option>
          <option value="bar">Bar / Grouped bar</option>
          <option value="stacked">Stacked bar</option>
          <option value="scatter">Scatter</option>
          <option value="histogram">Histogram</option>
          <option value="box">Box plot</option>
          <option value="heatmap">Heatmap</option>
        </select>
      </div>
      {error && <div className="error">{error}</div>}
      <div ref={ref} />
      <p className="muted small chart-note">
        차트는 최대 200점 표시 · 확대/축소 및 이미지 저장 가능
      </p>
    </div>
  );
}
