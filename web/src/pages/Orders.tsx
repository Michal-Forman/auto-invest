import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { useOrders } from "@/hooks/use-orders";
import { useRuns } from "@/hooks/use-runs";
import { formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Exchange, Order, OrderStatus } from "@/types";

const ALL = "ALL";

type OrderColKey = "date" | "ticker" | "exchange" | "czk_amount" | "quantity" | "fill_price" | "status";

const SORT_OPTIONS = [
  { value: "date|desc",       label: "Date: Newest first", col: "date"       as OrderColKey, asc: false },
  { value: "date|asc",        label: "Date: Oldest first", col: "date"       as OrderColKey, asc: true  },
  { value: "ticker|asc",      label: "Ticker: A → Z",      col: "ticker"     as OrderColKey, asc: true  },
  { value: "ticker|desc",     label: "Ticker: Z → A",      col: "ticker"     as OrderColKey, asc: false },
  { value: "czk_amount|desc", label: "CZK: High → Low",    col: "czk_amount" as OrderColKey, asc: false },
  { value: "czk_amount|asc",  label: "CZK: Low → High",    col: "czk_amount" as OrderColKey, asc: true  },
];

function compareOrders(a: Order, b: Order, col: OrderColKey, runDateMap: Record<string, string>): number {
  switch (col) {
    case "date":       return (runDateMap[a.run_id] ?? "").localeCompare(runDateMap[b.run_id] ?? "");
    case "ticker":     return a.ticker.localeCompare(b.ticker);
    case "exchange":   return a.exchange.localeCompare(b.exchange);
    case "czk_amount": return a.czk_amount - b.czk_amount;
    case "quantity":   return (a.quantity ?? -1) - (b.quantity ?? -1);
    case "fill_price": return (a.fill_price ?? -1) - (b.fill_price ?? -1);
    case "status":     return a.status.localeCompare(b.status);
  }
}

export function Orders() {
  usePageTitle("Orders");
  const [search, setSearch] = useState("");
  const [exchange, setExchange] = useState<Exchange | typeof ALL>(ALL);
  const [status, setStatus] = useState<OrderStatus | typeof ALL>(ALL);
  const [sortCol, setSortCol] = useState<OrderColKey>("date");
  const [sortAsc, setSortAsc] = useState(false);

  const { data: orders, loading: ordersLoading, error: ordersError } = useOrders();
  const { data: runs } = useRuns();

  if (ordersError) return <p className="text-red-600 p-6">Failed to load data.</p>;

  const runDateMap = Object.fromEntries((runs ?? []).map((r) => [r.id, r.created_at.slice(0, 10)]));

  const filtered = (orders ?? [])
    .filter((o) => {
      const matchSearch =
        search === "" ||
        o.ticker.toLowerCase().includes(search.toLowerCase()) ||
        o.display_name.toLowerCase().includes(search.toLowerCase());
      const matchExchange = exchange === ALL || o.exchange === exchange;
      const matchStatus = status === ALL || o.status === status;
      return matchSearch && matchExchange && matchStatus;
    })
    .sort((a, b) => {
      const diff = compareOrders(a, b, sortCol, runDateMap);
      return sortAsc ? diff : -diff;
    });

  function handleColSort(col: OrderColKey) {
    if (col === sortCol) setSortAsc(!sortAsc);
    else { setSortCol(col); setSortAsc(true); }
  }

  function handleDropdownSort(value: string) {
    const opt = SORT_OPTIONS.find((o) => o.value === value);
    if (opt) { setSortCol(opt.col); setSortAsc(opt.asc); }
  }

  const dropdownValue = `${sortCol}|${sortAsc ? "asc" : "desc"}`;
  const dropdownLabel = SORT_OPTIONS.find((o) => o.value === dropdownValue)?.label
    ?? `${sortCol} ${sortAsc ? "↑" : "↓"}`;

  function SortHeader({ label, col, className }: { label: string; col: OrderColKey; className?: string }) {
    return (
      <TableHead
        className={`cursor-pointer select-none hover:bg-primary/10 text-primary ${className ?? ""}`}
        onClick={() => handleColSort(col)}
      >
        {label}{sortCol === col ? (sortAsc ? " ↑" : " ↓") : ""}
      </TableHead>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Orders</h1>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground font-medium">Search</label>
            <Input
              placeholder="Search ticker..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-xs"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground font-medium">Exchange</label>
            <Select value={exchange} onValueChange={(v) => setExchange(v as Exchange | typeof ALL)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Exchange" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All Exchanges</SelectItem>
                <SelectItem value="T212">T212</SelectItem>
                <SelectItem value="Coinmate">Coinmate</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground font-medium">Status</label>
            <Select value={status} onValueChange={(v) => setStatus(v as OrderStatus | typeof ALL)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All Statuses</SelectItem>
                <SelectItem value="FILLED">Filled</SelectItem>
                <SelectItem value="SUBMITTED">Submitted</SelectItem>
                <SelectItem value="FAILED">Failed</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted-foreground font-medium">Sort by</label>
          <Select value={dropdownValue} onValueChange={handleDropdownSort}>
            <SelectTrigger className="w-48">
              <SelectValue>{dropdownLabel}</SelectValue>
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
          <Table>
            <TableHeader>
              <TableRow className="bg-primary/5 hover:bg-primary/5">
                <SortHeader label="Date"       col="date" />
                <SortHeader label="Ticker"     col="ticker" />
                <SortHeader label="Exchange"   col="exchange" />
                <SortHeader label="CZK"        col="czk_amount" className="text-right" />
                <SortHeader label="Qty"        col="quantity"   className="text-right" />
                <SortHeader label="Fill Price" col="fill_price" className="text-right" />
                <SortHeader label="Status"     col="status" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {ordersLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 7 }).map((__, j) => (
                        <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                : filtered.map((order) => (
                    <TableRow key={order.id}>
                      <TableCell className="text-muted-foreground text-sm">
                        {runDateMap[order.run_id] ?? "—"}
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">{order.ticker}</div>
                        <div className="text-xs text-muted-foreground">{order.display_name}</div>
                      </TableCell>
                      <TableCell>{order.exchange}</TableCell>
                      <TableCell className="text-right">{formatNumber(order.czk_amount)}</TableCell>
                      <TableCell className="text-right">
                        {order.quantity != null ? order.quantity : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {order.fill_price != null ? formatNumber(order.fill_price) : "—"}
                      </TableCell>
                      <TableCell><StatusBadge status={order.status} /></TableCell>
                    </TableRow>
                  ))
              }
              {!ordersLoading && filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    No orders match the current filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
