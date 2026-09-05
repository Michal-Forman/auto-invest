import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useConfig } from "@/hooks/use-config";
import { usePreview } from "@/hooks/use-preview";
import { usePendingInvestment } from "@/hooks/use-pending-investment";
import { formatNumber } from "@/lib/utils";
import { api } from "@/lib/api";
import type { ExchangeFundingItem, FundingCheckResponse } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Info } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";

function FundingExchangeCards({ exchanges }: { exchanges: ExchangeFundingItem[] }) {
  return (
    <div className="flex flex-col gap-4">
      {exchanges.filter((e) => e.is_short).map((e) => (
        <div key={e.exchange} className="flex gap-4 rounded-md border bg-primary/5 p-4">
          {e.qr_data_uri && (
            <img src={e.qr_data_uri} alt={`QR code for ${e.exchange}`} className="h-28 w-28 shrink-0" />
          )}
          <div className="flex flex-col gap-1 text-sm">
            <div className="font-semibold text-primary">{e.exchange}</div>
            <div className="text-muted-foreground">
              Available: {formatNumber(e.available_czk)} CZK · Needed: {formatNumber(e.needed_czk)} CZK
            </div>
            <div className="text-muted-foreground">
              Includes {formatNumber(e.dca_reserve_czk)} CZK reserved for the next DCA run
            </div>
            {e.account ? (
              <>
                <div><span className="text-muted-foreground">Account:</span> {e.account}</div>
                <div><span className="text-muted-foreground">Variable symbol:</span> {e.vs}</div>
                <div className="font-medium">
                  Suggested top-up: {formatNumber(e.suggested_topup_czk ?? 0)} CZK
                </div>
              </>
            ) : (
              <div className="text-amber-600">
                No deposit account configured for {e.exchange} in your profile.
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function daysUntil(iso: string): number {
  const ms = new Date(iso).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

export function Invest() {
  usePageTitle("Invest");
  const { data: config } = useConfig();
  const defaultAmount = config?.invest_amount ?? 5000;
  const [inputValue, setInputValue] = useState<string>("");

  const effectiveAmount = inputValue === "" ? defaultAmount : Math.max(0, parseFloat(inputValue) || 0);
  const { data: preview, loading, error } = usePreview(effectiveAmount);

  const total = preview?.reduce((s, i) => s + i.czk_amount, 0) ?? 0;

  const {
    data: pending,
    loading: pendingLoading,
    registerPending,
    registering,
    cancelPending,
    cancelling,
  } = usePendingInvestment();

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [placing, setPlacing] = useState(false);
  const [investResult, setInvestResult] = useState<{ run_id: string; total_czk: number } | null>(null);
  const [investError, setInvestError] = useState<string | null>(null);

  const [checkingFunding, setCheckingFunding] = useState(false);
  const [fundingResult, setFundingResult] = useState<FundingCheckResponse | null>(null);
  const [topUpOpen, setTopUpOpen] = useState(false);

  async function runFundingCheck(): Promise<FundingCheckResponse | null> {
    setCheckingFunding(true);
    setInvestError(null);
    try {
      const result = await api.checkFunding(effectiveAmount);
      setFundingResult(result);
      return result;
    } catch {
      setInvestError("Failed to check exchange balances. Please try again.");
      return null;
    } finally {
      setCheckingFunding(false);
    }
  }

  async function handlePlaceInvestmentClick() {
    const result = await runFundingCheck();
    if (!result) return;
    if (result.sufficient) {
      setConfirmOpen(true);
    } else {
      setTopUpOpen(true);
    }
  }

  async function handleSentTheMoney() {
    setInvestError(null);
    try {
      const result = await registerPending(effectiveAmount);
      setTopUpOpen(false);
      if (result.placed && result.invest) {
        setInvestResult(result.invest);
      }
      // When not placed yet, the pending panel below takes over automatically.
    } catch {
      setInvestError("Failed to register the pending investment. Please try again.");
    }
  }

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

      {pending && (
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Investment Pending</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Waiting for <strong>{formatNumber(pending.amount_czk)} CZK</strong> to clear. We'll place the
              investment automatically and email you once the funds arrive — expires in{" "}
              {daysUntil(pending.expires_at)} day{daysUntil(pending.expires_at) === 1 ? "" : "s"} if not funded.
            </p>
            <FundingExchangeCards exchanges={pending.funding.exchanges} />
            <div>
              <Button variant="outline" onClick={() => cancelPending()} disabled={cancelling}>
                {cancelling ? "Cancelling..." : "Cancel"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!pending && !pendingLoading && (
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
              <Button
                onClick={handlePlaceInvestmentClick}
                disabled={placing || checkingFunding || effectiveAmount <= 0}
                className="ml-4"
              >
                {checkingFunding ? "Checking balances..." : placing ? "Placing..." : "Place Investment"}
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
            <Dialog open={topUpOpen} onOpenChange={setTopUpOpen}>
              <DialogContent showCloseButton={false} className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Top Up Required</DialogTitle>
                  <DialogDescription>
                    One or more exchanges don't hold enough cash for this investment plus a
                    reserve for your next scheduled DCA run. Top up the amounts below, then let us know.
                  </DialogDescription>
                </DialogHeader>
                {fundingResult && <FundingExchangeCards exchanges={fundingResult.exchanges} />}
                <DialogFooter>
                  <DialogClose render={<Button variant="outline" />}>Close</DialogClose>
                  <Button onClick={handleSentTheMoney} disabled={registering}>
                    {registering ? "Checking..." : "I've sent the money"}
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
      )}

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
