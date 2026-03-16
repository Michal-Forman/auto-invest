import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useConfig } from "@/hooks/use-config";
import { usePreview } from "@/hooks/use-preview";
import { formatNumber } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export function Preview() {
  usePageTitle("Preview");
  const { data: config } = useConfig();
  const defaultAmount = config?.invest_amount ?? 5000;
  const [inputValue, setInputValue] = useState<string>("");

  const effectiveAmount = inputValue === "" ? defaultAmount : Math.max(0, parseFloat(inputValue) || 0);
  const { data: preview, loading, error } = usePreview(effectiveAmount);

  const total = preview?.reduce((s, i) => s + i.czk_amount, 0) ?? 0;

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
            value={inputValue === "" ? "" : inputValue}
            placeholder={String(defaultAmount)}
            onChange={(e) => setInputValue(e.target.value)}
            className="max-w-xs [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            min={0}
          />
          <span className="text-muted-foreground text-sm">CZK</span>
        </CardContent>
      </Card>

      {loading && !preview && (
        <Card>
          <CardContent className="p-0 overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableHead key={j}><Skeleton className="h-4 w-full" /></TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array.from({ length: 8 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((__, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      {error && <p className="text-red-600 p-2">Failed to load preview.</p>}

      {preview && (
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
                      <div className="text-xs text-muted-foreground">{inst.display_name}</div>
                    </TableCell>
                    <TableCell className="text-right">{(inst.target_weight * 100).toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{inst.drop_pct.toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{inst.multiplier.toFixed(2)}×</TableCell>
                    <TableCell className="text-right">
                      {inst.note !== "dropped" ? (inst.adjusted_weight * 100).toFixed(1) + "%" : "—"}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {inst.czk_amount > 0 ? formatNumber(inst.czk_amount) : "—"}
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
      )}
    </div>
  );
}
