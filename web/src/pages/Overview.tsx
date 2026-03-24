import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, TriangleAlert } from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useHealth } from "@/hooks/use-health";
import { useRuns } from "@/hooks/use-runs";
import { useConfig } from "@/hooks/use-config";
import { useAnalytics } from "@/hooks/use-analytics";
import { formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { WarningItem } from "@/types";

const CRON_HOUR = import.meta.env.VITE_INVEST_CRON?.split(" ")[1] ?? null;


function withEnvTime(cron: string): string {
  if (!CRON_HOUR) return cron;
  const envParts = import.meta.env.VITE_INVEST_CRON.split(" ");
  const parts = cron.split(" ");
  if (parts.length !== 5) return cron;
  parts[0] = envParts[0]; // minute
  parts[1] = envParts[1]; // hour
  return parts.join(" ");
}

function parseCron(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return cron;
  const [minute, hour, dom, month, dow] = parts;
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const dayLabel = dow === "*" ? "every day" : `every ${days[parseInt(dow)] ?? dow}`;
  if (dom === "*" && month === "*") {
    const h = hour === "*" ? "*" : hour.padStart(2, "0");
    const m = minute === "*" ? "*" : minute.padStart(2, "0");
    return `${dayLabel} at ${h}:${m} UTC`;
  }
  return cron;
}

function getNextRunDate(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return "Unknown";
  const dow = parseInt(parts[4]);
  if (isNaN(dow)) return "Unknown";
  const hourRaw = parseInt(parts[1]);
  const hour = isNaN(hourRaw) ? 0 : hourRaw;
  const now = new Date();
  const dayDiff = (dow - now.getUTCDay() + 7) % 7 || 7;
  const next = new Date(now);
  next.setUTCDate(now.getUTCDate() + dayDiff);
  next.setUTCHours(hour, 0, 0, 0);
  return next.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}

function StatusDot({ ok, loading, label }: { ok: boolean; loading: boolean; label: string }) {
  const dotClass = loading ? "bg-yellow-400 animate-pulse" : ok ? "bg-green-500" : "bg-red-500";
  const hint = loading ? "…" : ok ? "OK" : "Error";
  return (
    <div className="flex items-center gap-2">
      <div className={`h-2 w-2 rounded-full ${dotClass}`} />
      <span className="text-sm">{label}</span>
      <span className="text-xs text-muted-foreground">{hint}</span>
    </div>
  );
}

export function Overview() {
  usePageTitle("Overview");
  const navigate = useNavigate();
  const health = useHealth();
  const { data: runs, loading: runsLoading, error: runsError } = useRuns();
  const { data: config } = useConfig();
  const { portfolioValue, warnings } = useAnalytics();
  const [warningsOpen, setWarningsOpen] = useState<boolean>(false);

  const filled = runs?.filter((r) => r.status === "FILLED").length ?? 0;
  const finished = runs?.filter((r) => r.status === "FINISHED").length ?? 0;
  const failed = runs?.filter((r) => r.status === "FAILED").length ?? 0;
  const completed = filled + finished + failed;
  const totalInvested = runs?.filter((r) => r.status === "FILLED" && r.total_czk > 0).reduce((s, r) => s + r.total_czk, 0) ?? 0;
  const recent = runs?.slice(0, 5) ?? [];

  const currentValue = portfolioValue?.length ? portfolioValue[portfolioValue.length - 1].value : null;
  const totalGain: number | null =
    currentValue !== null && totalInvested > 0
      ? ((currentValue - totalInvested) / totalInvested) * 100
      : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Overview</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Portfolio Value</CardTitle>
          </CardHeader>
          <CardContent>
            {currentValue === null ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <div>
                <div className="text-2xl font-bold text-primary">{formatNumber(currentValue)} CZK</div>
                {runsLoading ? (
                  <Skeleton className="h-3 w-24 mt-1" />
                ) : (
                  <div className="text-xs text-muted-foreground mt-1">
                    Total invested: {formatNumber(totalInvested)} CZK
                    {totalGain !== null && (
                      <span className={`ml-1.5 font-medium ${totalGain >= 0 ? "text-green-600" : "text-red-500"}`}>
                        ({totalGain >= 0 ? "+" : ""}{formatNumber(totalGain, 2)}%)
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Completed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <Skeleton className="h-8 w-28" />
            ) : (
              <div>
                <div className="text-2xl font-bold text-primary">{completed}</div>
                {finished > 0 && <div className="text-xs text-yellow-600 mt-0.5">{finished} pending fill</div>}
                {failed > 0 && (
                  <div className="text-xs text-red-500 mt-0.5">{failed} failed</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {runsError && <p className="text-red-600 p-2">Failed to load run data.</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Next Run</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            {config ? (
              <>
                <div className="text-sm text-muted-foreground">{parseCron(withEnvTime(config.invest_interval))}</div>
                <div className="font-medium">{getNextRunDate(withEnvTime(config.invest_interval))}</div>
              </>
            ) : (
              <div className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-5 w-48" />
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Exchange Health</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <StatusDot ok={health.api} loading={health.loading} label="API" />
            <StatusDot ok={health.t212} loading={health.loading} label="Trading 212" />
            <StatusDot ok={health.coinmate} loading={health.loading} label="Coinmate" />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Recent Runs</CardTitle>
        </CardHeader>
        <CardContent className="p-0 -mt-4">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">CZK</TableHead>
                <TableHead className="text-right">Orders</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runsLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-full" /></TableCell>
                    </TableRow>
                  ))
                : recent.map((run) => (
                    <TableRow
                      key={run.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/runs/${run.id}`)}
                    >
                      <TableCell>{new Date(run.created_at).toLocaleDateString("en-GB")}</TableCell>
                      <TableCell><StatusBadge status={run.status} /></TableCell>
                      <TableCell className="text-right">{run.total_czk > 0 ? formatNumber(run.total_czk) : "—"}</TableCell>
                      <TableCell className="text-right">{run.order_count || "—"}</TableCell>
                    </TableRow>
                  ))
              }
              {!runsLoading && recent.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-6">No runs yet.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {warnings && warnings.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30">
          <button
            className="flex w-full items-center gap-3 px-4 py-3 text-sm"
            onClick={() => setWarningsOpen((o) => !o)}
          >
            <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" />
            <span className="flex-1 text-left font-medium text-amber-900 dark:text-amber-200">
              {warnings.length} warning{warnings.length !== 1 ? "s" : ""} in last 30 days
            </span>
            {warningsOpen ? (
              <ChevronUp className="h-4 w-4 text-amber-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-amber-500" />
            )}
          </button>
          {warningsOpen && (
            <div className="border-t border-amber-200 dark:border-amber-800">
              {warnings.map((w: WarningItem, i: number) => (
                <div key={i} className="flex items-center gap-3 px-4 py-2 text-sm">
                  <span className="font-medium text-amber-900 dark:text-amber-200">{w.ticker}</span>
                  <Badge variant="outline" className="border-amber-300 text-amber-700 dark:border-amber-700 dark:text-amber-300 text-xs">
                    {w.type}
                  </Badge>
                  <span className="text-amber-800 dark:text-amber-300">{w.detail}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
