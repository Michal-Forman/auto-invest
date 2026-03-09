import { useNavigate } from "react-router-dom";
import { usePageTitle } from "@/hooks/use-page-title";
import { mockConfig, mockRuns } from "@/data/mock";
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

export function Overview() {
  usePageTitle("Overview");
  const navigate = useNavigate();
  const lastRun = mockRuns[0];
  const filled = mockRuns.filter((r) => r.status === "FILLED").length;
  const failed = mockRuns.filter((r) => r.status === "FAILED").length;
  const totalInvested = mockRuns.filter((r) => r.total_czk > 0).reduce((s, r) => s + r.total_czk, 0);
  const recent = mockRuns.slice(0, 5);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Overview</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Total Invested</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{totalInvested.toLocaleString()} CZK</div>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Last Run Status</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge status={lastRun.status} />
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Completed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{filled}</div>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">Failed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{failed}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b bg-primary/5">
            <CardTitle className="text-base text-primary">Next Run</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="text-sm text-muted-foreground">{parseCron(mockConfig.cron)}</div>
            <div className="font-medium">{getNextRunDate(mockConfig.cron)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="border-b bg-primary/5">
            <CardTitle className="text-base text-primary">Exchange Health</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-6">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm">Trading 212</span>
              <span className="text-xs text-muted-foreground">OK</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-sm">Coinmate</span>
              <span className="text-xs text-muted-foreground">OK</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b bg-primary/5">
          <CardTitle className="text-base text-primary">Recent Runs</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="bg-primary/5 hover:bg-primary/5">
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
                  <TableCell className="text-right">{run.total_czk > 0 ? run.total_czk.toLocaleString() : "—"}</TableCell>
                  <TableCell className="text-right">{run.order_count || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
