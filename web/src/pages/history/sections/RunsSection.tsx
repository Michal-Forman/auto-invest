import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRuns } from "@/hooks/use-runs";
import { formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Run, RunStatus } from "@/types";

const ALL = "ALL";

type RunColKey = "date" | "status" | "total_czk" | "order_count";

const SORT_OPTIONS = [
  { value: "date|desc",      label: "Date: Newest first", col: "date"        as RunColKey, asc: false },
  { value: "date|asc",       label: "Date: Oldest first", col: "date"        as RunColKey, asc: true  },
  { value: "total_czk|desc", label: "CZK: High → Low",   col: "total_czk"   as RunColKey, asc: false },
  { value: "total_czk|asc",  label: "CZK: Low → High",   col: "total_czk"   as RunColKey, asc: true  },
];

function compareRuns(a: Run, b: Run, col: RunColKey): number {
  switch (col) {
    case "date":        return a.created_at.localeCompare(b.created_at);
    case "status":      return a.status.localeCompare(b.status);
    case "total_czk":   return a.total_czk - b.total_czk;
    case "order_count": return (a.order_count ?? 0) - (b.order_count ?? 0);
  }
}

export function RunsSection() {
  const navigate = useNavigate();
  const { data: runs, loading, error } = useRuns();
  const [status, setStatus] = useState<RunStatus | typeof ALL>(ALL);
  const [sortCol, setSortCol] = useState<RunColKey>("date");
  const [sortAsc, setSortAsc] = useState(false);

  if (error) return <p className="text-red-600 p-6">Failed to load data.</p>;

  const filtered = (runs ?? [])
    .filter((r) => status === ALL || r.status === status)
    .sort((a, b) => {
      const diff = compareRuns(a, b, sortCol);
      return sortAsc ? diff : -diff;
    });

  function handleColSort(col: RunColKey) {
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

  function SortHeader({ label, col, className }: { label: string; col: RunColKey; className?: string }) {
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
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground font-medium">Status</label>
            <Select value={status} onValueChange={(v) => setStatus(v as RunStatus | typeof ALL)}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All Statuses</SelectItem>
                <SelectItem value="CREATED">Created</SelectItem>
                <SelectItem value="FINISHED">Finished</SelectItem>
                <SelectItem value="FILLED">Filled</SelectItem>
                <SelectItem value="FAILED">Failed</SelectItem>
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
                <SortHeader label="Status"     col="status" />
                <SortHeader label="Total CZK"  col="total_czk"   className="text-right" />
                <SortHeader label="Orders"     col="order_count" className="text-right" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <TableRow key={i}>
                      {Array.from({ length: 4 }).map((__, j) => (
                        <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                : filtered.map((run) => (
                    <TableRow
                      key={run.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/app/runs/${run.id}`)}
                    >
                      <TableCell>
                        {new Date(run.created_at).toLocaleDateString("en-GB", {
                          weekday: "short",
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={run.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        {run.total_czk > 0 ? formatNumber(run.total_czk) : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        {run.order_count || "—"}
                      </TableCell>
                    </TableRow>
                  ))
              }
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
