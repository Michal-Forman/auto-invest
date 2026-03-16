import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useInstruments } from "@/hooks/use-instruments";
import { formatNumber } from "@/lib/utils";
import type { CapType } from "@/types";

const capVariants: Record<CapType, string> = {
  none: "bg-gray-100 text-gray-700 border-gray-200",
  soft: "bg-blue-100 text-blue-700 border-blue-200",
  hard: "bg-purple-100 text-purple-700 border-purple-200",
};

export function InstrumentsSection() {
  const { data: instruments, loading } = useInstruments();

  return (
    <Card>
      <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
        <CardTitle className="text-base text-primary">Instrument Registry</CardTitle>
      </CardHeader>
      <CardContent className="p-0 -mt-4">
        {loading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : !instruments || instruments.length === 0 ? (
          <p className="p-6 text-sm text-muted-foreground text-center">
            No instruments found. Configure your T212 pie to see instruments here.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Ticker</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead>Cap Type</TableHead>
                <TableHead className="text-right">Weight</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {instruments.map((inst) => (
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
                  <TableCell className="text-right font-mono text-sm">
                    {formatNumber(inst.target_weight * 100, 1)}%
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
