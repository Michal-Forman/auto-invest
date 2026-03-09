import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { mockInstruments, mockConfig } from "@/data/mock";
import { formatNumber } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

const MIN_ORDER = 25;
const DROP_THRESHOLD = 12.5;

function computePreview(instruments: typeof mockInstruments, totalCzk: number) {
  // Scale adjusted weights to sum to 1 then multiply by total
  const sumAdj = instruments.reduce((s, i) => s + i.adjusted_weight, 0);
  const raw = instruments.map((inst) => ({
    ...inst,
    raw_czk: (inst.adjusted_weight / sumAdj) * totalCzk,
  }));

  // Apply drop/bump rules
  const result = raw.map((inst) => {
    let czk = inst.raw_czk;
    let note: "normal" | "dropped" | "bumped" = "normal";
    if (czk < DROP_THRESHOLD) {
      czk = 0;
      note = "dropped";
    } else if (czk < MIN_ORDER) {
      czk = MIN_ORDER;
      note = "bumped";
    }
    return { ...inst, final_czk: czk, note };
  });

  // Renormalize excluding dropped
  const active = result.filter((r) => r.note !== "dropped");
  const allocatedFixed = active.filter((r) => r.note === "bumped").reduce((s, r) => s + r.final_czk, 0);
  const remaining = totalCzk - allocatedFixed;
  const sumNormal = active.filter((r) => r.note === "normal").reduce((s, r) => s + r.adjusted_weight, 0);

  return result.map((inst) => {
    if (inst.note === "dropped") return { ...inst, final_czk: 0 };
    if (inst.note === "bumped") return inst;
    return { ...inst, final_czk: ((inst.adjusted_weight / sumNormal) * remaining) };
  });
}

export function Preview() {
  usePageTitle("Preview");
  const [amount, setAmount] = useState(String(mockConfig.invest_amount));
  const totalCzk = Math.max(0, parseFloat(amount) || 0);
  const preview = computePreview(mockInstruments, totalCzk);
  const total = preview.reduce((s, i) => s + i.final_czk, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Next Run Preview</h1>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Invest Amount</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-3">
          <Input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="max-w-xs"
            min={0}
          />
          <span className="text-muted-foreground text-sm">CZK</span>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ticker</TableHead>
                <TableHead className="text-right">Base Weight %</TableHead>
                <TableHead className="text-right">Drop %</TableHead>
                <TableHead className="text-right">Multiplier</TableHead>
                <TableHead className="text-right">Adj %</TableHead>
                <TableHead className="text-right">CZK</TableHead>
                <TableHead>Note</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {preview.map((inst) => (
                <TableRow
                  key={inst.ticker}
                  className={inst.note === "dropped" ? "opacity-40" : ""}
                >
                  <TableCell>
                    <div className="font-medium">{inst.ticker}</div>
                    <div className="text-xs text-muted-foreground">{inst.name}</div>
                  </TableCell>
                  <TableCell className="text-right">{(inst.target_weight * 100).toFixed(1)}%</TableCell>
                  <TableCell className="text-right">{inst.drop_pct.toFixed(1)}%</TableCell>
                  <TableCell className="text-right">{inst.multiplier.toFixed(2)}×</TableCell>
                  <TableCell className="text-right">
                    {inst.note !== "dropped" ? (inst.adjusted_weight * 100).toFixed(1) + "%" : "—"}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {inst.final_czk > 0 ? formatNumber(inst.final_czk) : "—"}
                  </TableCell>
                  <TableCell>
                    {inst.note === "bumped" && (
                      <Badge variant="outline" className="bg-yellow-100 text-yellow-800 border-yellow-200 text-xs">
                        bumped to min
                      </Badge>
                    )}
                    {inst.note === "dropped" && (
                      <Badge variant="outline" className="bg-red-100 text-red-800 border-red-200 text-xs">
                        dropped
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              <TableRow className="border-t-2 font-semibold bg-primary/10 text-primary">
                <TableCell colSpan={5}>Total</TableCell>
                <TableCell className="text-right">{formatNumber(total)}</TableCell>
                <TableCell />
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
