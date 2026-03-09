import { usePageTitle } from "@/hooks/use-page-title";
import { mockConfig, mockInstruments } from "@/data/mock";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CapType } from "@/types";

const capVariants: Record<CapType, string> = {
  none: "bg-gray-100 text-gray-700 border-gray-200",
  soft: "bg-blue-100 text-blue-700 border-blue-200",
  hard: "bg-purple-100 text-purple-700 border-purple-200",
};

function parseCron(cron: string): string {
  const parts = cron.split(" ");
  if (parts.length !== 5) return cron;
  const [minute, hour, , , dow] = parts;
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const dayLabel = dow === "*" ? "every day" : `every ${days[parseInt(dow)] ?? dow}`;
  return `${dayLabel} at ${hour.padStart(2, "0")}:${minute.padStart(2, "0")} UTC`;
}

export function Config() {
  usePageTitle("Config");
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Configuration</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">INVEST_AMOUNT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockConfig.invest_amount.toLocaleString()} CZK</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">T212_WEIGHT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(mockConfig.t212_weight * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">BTC_WEIGHT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(mockConfig.btc_weight * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Schedule</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <div className="font-mono text-sm text-muted-foreground">{mockConfig.cron}</div>
          <div className="font-medium">{parseCron(mockConfig.cron)}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Environment</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge variant="outline" className={mockConfig.environment === "prod"
            ? "bg-green-100 text-green-800 border-green-200"
            : "bg-yellow-100 text-yellow-800 border-yellow-200"
          }>
            {mockConfig.environment.toUpperCase()}
          </Badge>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Instrument Registry</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead>Display Name</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead>Cap Type</TableHead>
                <TableHead className="text-right">Target Weight</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockInstruments.map((inst) => (
                <TableRow key={inst.ticker}>
                  <TableCell className="font-mono text-sm font-medium">{inst.ticker}</TableCell>
                  <TableCell>{inst.display_name}</TableCell>
                  <TableCell>{inst.exchange}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={capVariants[inst.cap_type]}>
                      {inst.cap_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{(inst.target_weight * 100).toFixed(1)}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
