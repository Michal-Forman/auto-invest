import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useConfig } from "@/hooks/use-config";
import { usePreview } from "@/hooks/use-preview";
import { formatNumber } from "@/lib/utils";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Info } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";

export function Invest() {
  usePageTitle("Invest");
  const { data: config } = useConfig();
  const defaultAmount = config?.invest_amount ?? 5000;
  const [inputValue, setInputValue] = useState<string>("");

  const effectiveAmount = inputValue === "" ? defaultAmount : Math.max(0, parseFloat(inputValue) || 0);
  const { data: preview, loading, error } = usePreview(effectiveAmount);

  const total = preview?.reduce((s, i) => s + i.czk_amount, 0) ?? 0;

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [placing, setPlacing] = useState(false);
  const [investResult, setInvestResult] = useState<{ run_id: string; total_czk: number } | null>(null);
  const [investError, setInvestError] = useState<string | null>(null);

  async function handlePlaceInvestment() {
    setPlacing(true);
    setInvestResult(null);
    setInvestError(null);
    try {
      const result = await api.placeInvestment(effectiveAmount);
      setInvestResult(result);
    } catch {
      setInvestError("Failed to place investment. Please try again.");
    } finally {
      setPlacing(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Invest</h1>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Invest Amount</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <Input
              type="number"
              value={inputValue === "" ? "" : inputValue}
              placeholder={String(defaultAmount)}
              onChange={(e) => setInputValue(e.target.value)}
              className="max-w-xs [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
              min={0}
            />
            <span className="text-muted-foreground text-sm">CZK</span>
            <Button onClick={() => setConfirmOpen(true)} disabled={placing || effectiveAmount <= 0} className="ml-4">
              {placing ? "Placing..." : "Place Investment"}
            </Button>
          </div>
          <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <DialogContent showCloseButton={false}>
              <DialogHeader>
                <DialogTitle>Confirm Investment</DialogTitle>
                <DialogDescription>
                  Place a one-time investment of <strong>{formatNumber(effectiveAmount)} CZK</strong>?
                  This will place real orders immediately.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
                <Button onClick={() => { setConfirmOpen(false); handlePlaceInvestment(); }}>
                  Confirm
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          {investResult && (
            <p className="text-sm text-green-700">
              Investment placed! {formatNumber(investResult.total_czk)} CZK
            </p>
          )}
          {investError && <p className="text-sm text-red-600">{investError}</p>}
        </CardContent>
      </Card>

      {loading && !preview && (
        <Card className="pb-0">
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Investment Preview</CardTitle>
          </CardHeader>
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
        <Card className="pb-0">
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Investment Preview</CardTitle>
          </CardHeader>
          <CardContent className="p-0 overflow-auto">
            <Table>
              <TableHeader>
                <TooltipProvider>
                  <TableRow>
                    <TableHead className="pl-4">Ticker</TableHead>
                    <TableHead className="text-right">
                      <span className="inline-flex items-center justify-end gap-1">
                        Base Weight %
                        <Tooltip>
                          <TooltipTrigger><Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" /></TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs text-xs">Target allocation from the T212 pie, before drop adjustments</TooltipContent>
                        </Tooltip>
                      </span>
                    </TableHead>
                    <TableHead className="text-right">
                      <span className="inline-flex items-center justify-end gap-1">
                        Drop %
                        <Tooltip>
                          <TooltipTrigger><Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" /></TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs text-xs">How far the current price is below the all-time high</TooltipContent>
                        </Tooltip>
                      </span>
                    </TableHead>
                    <TableHead className="text-right">
                      <span className="inline-flex items-center justify-end gap-1">
                        Multiplier
                        <Tooltip>
                          <TooltipTrigger><Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" /></TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs text-xs">Boost factor derived from the drop — higher drop means more allocation</TooltipContent>
                        </Tooltip>
                      </span>
                    </TableHead>
                    <TableHead className="text-right">
                      <span className="inline-flex items-center justify-end gap-1">
                        Adj %
                        <Tooltip>
                          <TooltipTrigger><Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" /></TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs text-xs">Final share of the investment after applying the drop multiplier and normalizing</TooltipContent>
                        </Tooltip>
                      </span>
                    </TableHead>
                    <TableHead className="text-right pr-4">CZK</TableHead>
                  </TableRow>
                </TooltipProvider>
              </TableHeader>
              <TableBody>
                {preview.map((inst) => (
                  <TableRow
                    key={inst.ticker}
                    className={inst.note === "dropped" ? "opacity-40" : ""}
                  >
                    <TableCell className="pl-4">
                      <div className="font-medium">{inst.ticker}</div>
                      <div className="text-xs text-muted-foreground">{inst.display_name}</div>
                    </TableCell>
                    <TableCell className="text-right">{(inst.target_weight * 100).toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{inst.drop_pct.toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{inst.multiplier.toFixed(2)}×</TableCell>
                    <TableCell className="text-right">
                      {inst.note !== "dropped" ? (inst.adjusted_weight * 100).toFixed(1) + "%" : "—"}
                    </TableCell>
                    <TableCell className="text-right font-medium pr-4">
                      {inst.czk_amount > 0 ? formatNumber(inst.czk_amount) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="border-t-2 font-semibold bg-primary/10 text-primary">
                  <TableCell colSpan={5} className="pl-4">Total</TableCell>
                  <TableCell className="text-right pr-4">{formatNumber(total)}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
