import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Info } from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useAnalytics } from "@/hooks/use-analytics";
import { formatNumber } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip as UITooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";

const COLORS = ["#1e3a8a", "#1e40af", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#f59e0b", "#10b981"];
const STATUS_COLORS: Record<string, string> = {
  FILLED: "#10b981",
  FINISHED: "#1e3a8a",
  FAILED: "#ef4444",
  CREATED: "#9ca3af",
};

type Period = "1M" | "3M" | "6M" | "1Y" | "All";

function periodCutoff(period: Period): string | null {
  const now = new Date();
if (period === "1M") { now.setMonth(now.getMonth() - 1); return now.toISOString().slice(0, 10); }
  if (period === "3M") { now.setMonth(now.getMonth() - 3); return now.toISOString().slice(0, 10); }
  if (period === "6M") { now.setMonth(now.getMonth() - 6); return now.toISOString().slice(0, 10); }
  if (period === "1Y") { now.setFullYear(now.getFullYear() - 1); return now.toISOString().slice(0, 10); }
  return null;
}

export function Analytics() {
  usePageTitle("Analytics");
  const {
    runs,
    status,
    profitLoss,
    portfolioHistory,
    strategyComparison,
    holdingsRatio,
    loading,
    profitLossLoading,
    portfolioHistoryLoading,
    strategyComparisonLoading,
    holdingsRatioLoading,
    error,
  } = useAnalytics();

  const [period, setPeriod] = useState<Period>("All");

  if (error) return <p className="text-red-600 p-6">Failed to load data.</p>;

  const cutoff = periodCutoff(period);
  const filteredComparison = strategyComparison
    ? cutoff ? strategyComparison.filter((d) => d.date >= cutoff) : strategyComparison
    : null;

  const lastPoint = filteredComparison?.at(-1) ?? null;
  const strategyDelta =
    lastPoint && lastPoint.baseline_value > 0
      ? ((lastPoint.actual_value - lastPoint.baseline_value) / lastPoint.baseline_value) * 100
      : null;

  const gainPositive = (profitLoss?.gain_czk ?? 0) >= 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Analytics</h1>

      {/* Section 1 — Stats row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-sm text-primary">Filled Runs</CardTitle>
          </CardHeader>
          <CardContent className="pt-3">
            {profitLossLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <p className="text-2xl font-bold">{profitLoss?.filled_run_count ?? "—"}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-sm text-primary">Total Invested</CardTitle>
          </CardHeader>
          <CardContent className="pt-3">
            {profitLossLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-bold">
                {profitLoss ? `${formatNumber(profitLoss.total_invested_czk)} CZK` : "—"}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-sm text-primary">Portfolio Value</CardTitle>
          </CardHeader>
          <CardContent className="pt-3">
            {profitLossLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <p className="text-2xl font-bold">
                {profitLoss ? `${formatNumber(profitLoss.current_value_czk)} CZK` : "—"}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-sm text-primary">Gain / Loss</CardTitle>
          </CardHeader>
          <CardContent className="pt-3">
            {profitLossLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : profitLoss ? (
              <p className={`text-2xl font-bold ${gainPositive ? "text-emerald-600" : "text-red-600"}`}>
                {gainPositive ? "+" : ""}{formatNumber(profitLoss.gain_czk)} CZK
                <span className="text-base font-normal ml-1">
                  ({gainPositive ? "+" : ""}{profitLoss.gain_pct}%)
                </span>
              </p>
            ) : (
              <p className="text-2xl font-bold">—</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Section 2 — Portfolio Value Over Time */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Portfolio Value Over Time (CZK)</CardTitle>
        </CardHeader>
        <CardContent>
          {portfolioHistoryLoading ? (
            <Skeleton className="h-[240px] w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={portfolioHistory ?? []} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v: number) => [`${formatNumber(v)} CZK`, "Portfolio Value"]} />
                <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Section 3 — Strategy Comparison */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <div className="flex items-center justify-between gap-2">
            <div className="inline-flex items-center gap-1">
              <CardTitle className="text-base text-primary">Strategy Comparison</CardTitle>
              <TooltipProvider>
                <UITooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs text-xs">
                    Compares your actual portfolio (using the ATH drop multiplier) against what the same invested amounts would be worth under fixed weights. A positive delta means the ATH strategy has outperformed equal-weight allocation.
                  </TooltipContent>
                </UITooltip>
              </TooltipProvider>
            </div>
            {strategyComparisonLoading ? (
              <Skeleton className="h-5 w-24" />
            ) : (
              <span className={`text-sm font-semibold ${strategyDelta === null ? "text-muted-foreground" : strategyDelta >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                ATH {strategyDelta === null ? "—" : `${strategyDelta >= 0 ? "+" : ""}${strategyDelta.toFixed(1)}%`} vs Fixed Weights
              </span>
            )}
            <div className="flex gap-1">
              {(["1M", "3M", "6M", "1Y", "All"] as Period[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2 py-0.5 text-xs rounded ${period === p ? "bg-primary text-white" : "bg-muted text-muted-foreground hover:bg-muted/70"}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {strategyComparisonLoading ? (
            <Skeleton className="h-[240px] w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={filteredComparison ?? []} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v: number, name: string) => [`${formatNumber(v)} CZK`, name]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line
                  type="monotone"
                  dataKey="actual_value"
                  name="ATH Strategy"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="baseline_value"
                  name="Fixed Weights"
                  stroke="#9ca3af"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Section 4 — Holdings composition + Run Status */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Holdings Composition</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            {holdingsRatioLoading ? (
              <Skeleton className="h-[220px] w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={holdingsRatio ?? []}
                    dataKey="ratio_pct"
                    nameKey="ticker"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ ticker, ratio_pct }) => `${ticker} (${ratio_pct}%)`}
                    labelLine
                  >
                    {(holdingsRatio ?? []).map((entry, i) => (
                      <Cell key={entry.ticker} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [`${v}%`, "Ratio"]} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Run Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            {loading ? (
              <Skeleton className="h-[220px] w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={(status ?? []).filter((d) => d.count > 0)}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ status: s, count }) => `${s} (${count})`}
                    labelLine
                  >
                    {(status ?? []).filter((d) => d.count > 0).map((entry) => (
                      <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? "#9ca3af"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Section 5 — Existing charts */}
      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">CZK Invested per Run</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-[220px] w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={(runs ?? []).slice().reverse()} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="czk" fill="#1e3a8a" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
