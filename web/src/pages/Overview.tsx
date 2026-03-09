import { useNavigate } from "react-router-dom";
import { usePageTitle } from "@/hooks/use-page-title";
import { useHealth } from "@/hooks/use-health";
import { useRuns } from "@/hooks/use-runs";
import { useConfig } from "@/hooks/use-config";
import { formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function parseCron(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return cron;
  const [minute, hour, dom, month, dow] = parts;
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const dayLabel = dow === "*" ? "every day" : `every ${days[parseInt(dow)] ?? dow}`;
  if (dom === "*" && month === "*") {
    return `${dayLabel} at ${hour.padStart(2, "0")}:${minute.padStart(2, "0")} UTC`;
  }
  return cron;
}

function getNextRunDate(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return "Unknown";
  const dow = parseInt(parts[4]);
  const hour = parseInt(parts[1]);
  const now = new Date();
  const dayDiff = (dow - now.getUTCDay() + 7) % 7 || 7;
  const next = new Date(now);
  next.setUTCDate(now.getUTCDate() + dayDiff);
  next.setUTCHours(hour, 0, 0, 0);
  return next.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}

type DotStatus = "ok" | "error" | "unknown" | "loading";

function StatusDot({ status, label }: { status: DotStatus; label: string }) {
  const dotClass =
    status === "ok"
      ? "bg-green-500"
      : status === "error"
        ? "bg-red-500"
        : status === "loading"
          ? "bg-yellow-400 animate-pulse"
          : "bg-muted-foreground/40";
  const hint =
    status === "ok" ? "OK" : status === "error" ? "Error" : status === "loading" ? "…" : "Unknown";
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

  const lastRun = runs?.[0] ?? null;
  const filled = runs?.filter((r) => r.status === "FILLED").length ?? 0;
  const failed = runs?.filter((r) => r.status === "FAILED").length ?? 0;
  const totalInvested = runs?.filter((r) => r.total_czk > 0).reduce((s, r) => s + r.total_czk, 0) ?? 0;
  const recent = runs?.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Overview</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Total Invested</CardTitle>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="text-muted-foreground text-sm">Loading…</div>
            ) : (
              <div className="text-2xl font-bold text-primary">{formatNumber(totalInvested)} CZK</div>
            )}
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Last Run Status</CardTitle>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="text-muted-foreground text-sm">Loading…</div>
            ) : lastRun ? (
              <StatusBadge status={lastRun.status} />
            ) : (
              <div className="text-muted-foreground text-sm">—</div>
            )}
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Completed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="text-muted-foreground text-sm">Loading…</div>
            ) : (
              <div className="text-2xl font-bold text-primary">{filled}</div>
            )}
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Failed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="text-muted-foreground text-sm">Loading…</div>
            ) : (
              <div className="text-2xl font-bold text-red-600">{failed}</div>
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
                <div className="text-sm text-muted-foreground">{parseCron(config.invest_interval)}</div>
                <div className="font-medium">{getNextRunDate(config.invest_interval)}</div>
              </>
            ) : (
              <div className="text-muted-foreground text-sm">Loading…</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Exchange Health</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <StatusDot status={health.api} label="API" />
            <StatusDot status={health.t212} label="Trading 212" />
            <StatusDot status={health.coinmate} label="Coinmate" />
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
              {recent.map((run) => (
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
              ))}
              {!runsLoading && recent.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-6">No runs yet.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
