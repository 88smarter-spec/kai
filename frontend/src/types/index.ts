export type Row = Record<string, unknown>;
export interface Dataset {
  id: string;
  name: string;
  row_count: number;
  column_count: number;
  cleaning: {
    warnings: string[];
    total_candidates: number;
    removed_rows: number;
    removed_columns: number;
    header_start?: number;
    encoding?: string;
  };
}
export interface ColumnProfile {
  name: string;
  dtype: string;
  unique: number;
  null_count: number;
  null_ratio: number;
  min: unknown;
  max: unknown;
  mean: number | null;
  median: number | null;
  std: number | null;
  top_values: { value: unknown; count: number }[];
}
export interface Profile {
  row_count: number;
  column_count: number;
  duplicates: number;
  null_count: number;
  numeric_columns: string[];
  categorical_columns: string[];
  date_columns: string[];
  columns: ColumnProfile[];
}
export interface CleanOptions {
  empty_rows: boolean;
  empty_columns: boolean;
  exclude_totals: boolean;
  numbers: boolean;
  dates: boolean;
  percentages: boolean;
}
export const defaultOptions: CleanOptions = {
  empty_rows: true,
  empty_columns: true,
  exclude_totals: false,
  numbers: true,
  dates: true,
  percentages: true,
};
export type Operation =
  | "describe"
  | "groupby"
  | "aggregate"
  | "pivot"
  | "filter"
  | "sort"
  | "top_n"
  | "bottom_n"
  | "difference"
  | "ratio"
  | "growth_rate"
  | "moving_average"
  | "correlation"
  | "outliers"
  | "trend"
  | "join"
  | "missing"
  | "duplicates"
  | "regression";
export interface Plan {
  dataset: string;
  operation: Operation;
  columns?: string[];
  group_by?: string[];
  metrics?: Record<string, string>;
  filters?: { column: string; operator: string; value?: unknown }[];
  n?: number;
  ascending?: boolean;
  time_column?: string | null;
  pivot_column?: string | null;
  window?: number;
  other_dataset?: string | null;
  join_keys?: string[];
  join_how?: string;
  outlier_method?: string;
}
export interface Recommendation {
  title: string;
  plan: Plan;
}
export interface Detail extends Dataset {
  preview: Row[];
  columns: string[];
  preview_total: number;
  profile: Profile;
  recommendations: Recommendation[];
}
export interface AnalysisResult {
  operation: Operation;
  plan: Plan;
  rows: Row[];
  columns: string[];
  total_rows: number;
  truncated: boolean;
  details: Record<string, unknown>;
  warnings: string[];
  chart: {
    data: Partial<Plotly.PlotData>[];
    layout: Partial<Plotly.Layout>;
  } | null;
}
export interface AutoResult {
  summary: string[];
  analyses: { title: string; result: AnalysisResult }[];
  skipped: { title: string; reason: string }[];
  notes: string[];
}
export interface Settings {
  url: string;
  model: string;
  temperature: number;
  max_tokens: number;
}
export const defaultSettings: Settings = {
  url: "http://127.0.0.1:8080/v1",
  model: "",
  temperature: 0.2,
  max_tokens: 2048,
};
