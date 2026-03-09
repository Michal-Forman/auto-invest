import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { mockOrders, mockRuns } from "@/data/mock";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Exchange, OrderStatus } from "@/types";

const ALL = "ALL";
const runDateMap = Object.fromEntries(mockRuns.map((r) => [r.id, r.created_at.slice(0, 10)]));

export function Orders() {
  usePageTitle("Orders");
  const [search, setSearch] = useState("");
  const [exchange, setExchange] = useState<Exchange | typeof ALL>(ALL);
  const [status, setStatus] = useState<OrderStatus | typeof ALL>(ALL);

  const filtered = mockOrders.filter((o) => {
    const matchSearch =
      search === "" ||
      o.ticker.toLowerCase().includes(search.toLowerCase()) ||
      o.display_name.toLowerCase().includes(search.toLowerCase());
    const matchExchange = exchange === ALL || o.exchange === exchange;
    const matchStatus = status === ALL || o.status === status;
    return matchSearch && matchExchange && matchStatus;
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Orders</h1>

      <div className="flex flex-wrap gap-3">
        <Input
          placeholder="Search ticker..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
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

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Ticker</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead className="text-right">CZK</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Fill Price</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="text-muted-foreground text-sm">
                    {runDateMap[order.run_id] ?? "—"}
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">{order.ticker}</div>
                    <div className="text-xs text-muted-foreground">{order.display_name}</div>
                  </TableCell>
                  <TableCell>{order.exchange}</TableCell>
                  <TableCell className="text-right">{order.czk_amount.toLocaleString()}</TableCell>
                  <TableCell className="text-right">
                    {order.quantity != null ? order.quantity : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {order.fill_price != null ? order.fill_price.toLocaleString() : "—"}
                  </TableCell>
                  <TableCell><StatusBadge status={order.status} /></TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
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
