import { usePageTitle } from "@/hooks/use-page-title";
import { useConfig } from "@/hooks/use-config";
import { formatNumber } from "@/lib/utils";
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
  const { data: config, loading, error } = useConfig();

  if (loading) return <p className="text-muted-foreground p-6">Loading…</p>;
  if (error || !config) return <p className="text-red-600 p-6">Failed to load data.</p>;

  const totalWeight = config.t212_weight + config.btc_weight;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Configuration</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">INVEST_AMOUNT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{formatNumber(config.invest_amount)} CZK</div>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">T212_WEIGHT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{(config.t212_weight / totalWeight * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-primary">
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-muted-foreground font-normal">BTC_WEIGHT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{(config.btc_weight / totalWeight * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Schedule</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <div className="font-mono text-sm text-muted-foreground">{config.invest_interval}</div>
          <div className="font-medium">{parseCron(config.invest_interval)}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Environment</CardTitle>
        </CardHeader>
        <CardContent>
          <Badge variant="outline" className={config.environment === "prod"
            ? "bg-green-100 text-green-800 border-green-200"
            : "bg-yellow-100 text-yellow-800 border-yellow-200"
          }>
            {config.environment.toUpperCase()}
          </Badge>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Instrument Registry</CardTitle>
        </CardHeader>
        <CardContent className="p-0 -mt-4">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Ticker</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead>Cap Type</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {config.instruments.map((inst) => (
                <TableRow key={inst.ticker}>
                  <TableCell className="font-mono text-sm font-medium">{inst.ticker}</TableCell>
                  <TableCell>{inst.display_name}</TableCell>
                  <TableCell>{inst.instrument_type}</TableCell>
                  <TableCell>{inst.currency}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={capVariants[inst.cap_type]}>
                      {inst.cap_type}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
