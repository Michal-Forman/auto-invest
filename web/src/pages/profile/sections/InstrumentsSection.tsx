import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CapType, Config } from "@/types";

const capVariants: Record<CapType, string> = {
  none: "bg-gray-100 text-gray-700 border-gray-200",
  soft: "bg-blue-100 text-blue-700 border-blue-200",
  hard: "bg-purple-100 text-purple-700 border-purple-200",
};

export function InstrumentsSection({ config }: { config: Config | null }) {
  if (!config) return null;

  return (
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
  );
}
