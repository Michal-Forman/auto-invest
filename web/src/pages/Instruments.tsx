import { useState } from "react";
import { Info } from "lucide-react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useHoldings } from "@/hooks/use-holdings";
import { useInstruments } from "@/hooks/use-instruments";
import { formatNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { CapType, Instrument } from "@/types";

type SortKey = keyof Instrument | "holding_czk";

type SortOption = {
  value: string;
  label: string;
  key: SortKey;
  asc: boolean;
};

const SORT_OPTIONS: SortOption[] = [
  { value: "ticker|asc",        label: "Ticker: A → Z",          key: "ticker",        asc: true  },
  { value: "ticker|desc",       label: "Ticker: Z → A",          key: "ticker",        asc: false },
  { value: "drop_pct|desc",     label: "Drop: High → Low",       key: "drop_pct",      asc: false },
  { value: "drop_pct|asc",      label: "Drop: Low → High",       key: "drop_pct",      asc: true  },
  { value: "multiplier|desc",   label: "Multiplier: High → Low", key: "multiplier",    asc: false },
  { value: "multiplier|asc",    label: "Multiplier: Low → High", key: "multiplier",    asc: true  },
  { value: "next_czk|desc",     label: "Next CZK: High → Low",   key: "next_czk",      asc: false },
  { value: "next_czk|asc",      label: "Next CZK: Low → High",   key: "next_czk",      asc: true  },
  { value: "holding_czk|desc",  label: "Holdings: High → Low",   key: "holding_czk",   asc: false },
  { value: "holding_czk|asc",   label: "Holdings: Low → High",   key: "holding_czk",   asc: true  },
];

function dropColor(drop: number) {
  if (drop < 20) return "text-green-700";
  if (drop < 50) return "text-yellow-700";
  return "text-red-700";
}

const capVariants: Record<CapType, string> = {
  none: "bg-gray-100 text-gray-700 border-gray-200",
  soft: "bg-blue-100 text-blue-700 border-blue-200",
  hard: "bg-purple-100 text-purple-700 border-purple-200",
};

export function Instruments() {
  usePageTitle("Instruments");
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [asc, setAsc] = useState(true);

  const { data: instruments, loading, error } = useInstruments();
  const { data: holdings, loading: holdingsLoading } = useHoldings();

  if (error) return <p className="text-red-600 p-6">Failed to load data.</p>;

  const holdingsMap = Object.fromEntries((holdings ?? []).map((h) => [h.ticker, h.value_czk]));

  function handleSort(key: SortKey) {
    if (key === sortKey) setAsc(!asc);
    else { setSortKey(key); setAsc(true); }
  }

  const currentSortValue = `${sortKey}|${asc ? "asc" : "desc"}`;
  const currentSortLabel = SORT_OPTIONS.find((o) => o.value === currentSortValue)?.label
    ?? `${sortKey} ${asc ? "↑" : "↓"}`;

  function handleSortSelect(value: string | null) {
    const opt = SORT_OPTIONS.find((o) => o.value === value);
    if (opt) { setSortKey(opt.key); setAsc(opt.asc); }
  }

  const sorted = [...(instruments ?? [])].sort((a, b) => {
    const va = sortKey === "holding_czk" ? (holdingsMap[a.ticker] ?? 0) : a[sortKey as keyof Instrument];
    const vb = sortKey === "holding_czk" ? (holdingsMap[b.ticker] ?? 0) : b[sortKey as keyof Instrument];
    if (typeof va === "number" && typeof vb === "number") return asc ? va - vb : vb - va;
    return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });

  function SortHeader({ label, col, tooltip }: { label: string; col: SortKey; tooltip?: string; }) {
    return (
      <TableHead
        className="cursor-pointer select-none hover:bg-primary/10 text-primary"
        onClick={() => handleSort(col)}
      >
        <span className="inline-flex items-center gap-1">
          {label}
          {tooltip && (
            <Tooltip>
              <TooltipTrigger onClick={(e) => e.stopPropagation()}>
                <Info className="h-3.5 w-3.5 text-muted-foreground/60 cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs text-xs">
                {tooltip}
              </TooltipContent>
            </Tooltip>
          )}
          {sortKey === col ? (asc ? " ↑" : " ↓") : ""}
        </span>
      </TableHead>
    );
  }

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-primary">Instruments</h1>

        <div className="flex justify-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground font-medium">Sort by</label>
            <Select value={currentSortValue} onValueChange={handleSortSelect}>
              <SelectTrigger className="w-52">
                <SelectValue>{currentSortLabel}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Card>
          <CardContent className="p-0 overflow-auto -mt-4">
            {loading || holdingsLoading ? (
              <div className="p-4 space-y-2">
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-primary/5 hover:bg-primary/5">
                  <SortHeader label="Ticker" col="ticker" />
                  <SortHeader label="Exchange" col="exchange" />
                  <SortHeader
                    label="Cap"
                    col="cap_type"
                    tooltip="Boost cap strategy applied when the price is far below ATH. None = unlimited boost; Soft = capped at 75% drop; Hard = resets to 1× if drop reaches 90%."
                  />
                  <SortHeader label="Weight %" col="target_weight" />
                  <SortHeader
                    label="ATH"
                    col="ath_price"
                    tooltip="All-time high price in the instrument's native currency."
                  />
                  <SortHeader
                    label="Current"
                    col="current_price"
                    tooltip="Current market price in the instrument's native currency."
                  />
                  <SortHeader label="Drop %" col="drop_pct" />
                  <SortHeader
                    label="Multiplier"
                    col="multiplier"
                    tooltip="How much this instrument's base allocation is boosted based on its drop from ATH. A multiplier of 2× means it receives twice its normal share."
                  />
                  <SortHeader
                    label="Next CZK"
                    col="next_czk"
                    tooltip="Estimated CZK amount to be invested in the next scheduled run, after applying the multiplier and normalising across all instruments."
                  />
                  <SortHeader
                    label="Holdings CZK"
                    col="holding_czk"
                    tooltip="Current value of holdings in this instrument, converted to CZK at latest prices."
                  />
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((inst) => (
                  <TableRow key={inst.ticker}>
                    <TableCell>
                      <div className="font-medium">{inst.ticker}</div>
                      <div className="text-xs text-muted-foreground">{inst.display_name}</div>
                    </TableCell>
                    <TableCell>{inst.exchange}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={capVariants[inst.cap_type]}>
                        {inst.cap_type}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatNumber(inst.target_weight * 100, 1)}%</TableCell>
                    <TableCell>{formatNumber(inst.ath_price)}</TableCell>
                    <TableCell>{formatNumber(inst.current_price)}</TableCell>
                    <TableCell className={`font-medium ${dropColor(inst.drop_pct)}`}>
                      {inst.drop_pct.toFixed(1)}%
                    </TableCell>
                    <TableCell>{inst.multiplier.toFixed(2)}×</TableCell>
                    <TableCell className="font-medium">{formatNumber(inst.next_czk)}</TableCell>
                    <TableCell className="font-medium">
                      {holdingsMap[inst.ticker] != null ? formatNumber(holdingsMap[inst.ticker]) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  );
}
