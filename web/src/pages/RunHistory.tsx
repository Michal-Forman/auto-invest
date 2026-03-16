import { useNavigate } from "react-router-dom";
import { usePageTitle } from "@/hooks/use-page-title";
import { useRuns } from "@/hooks/use-runs";
import { formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function RunHistory() {
  usePageTitle("Runs");
  const navigate = useNavigate();
  const { data: runs, loading, error } = useRuns();

  if (error) return <p className="text-red-600 p-6">Failed to load data.</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Run History</h1>
      <Card>
        <CardContent className="p-0 -mt-4">
          <Table>
            <TableHeader>
              <TableRow className="bg-primary/5 hover:bg-primary/5">
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total CZK</TableHead>
                <TableHead className="text-right">Orders</TableHead>
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
                : (runs ?? []).map((run) => (
                    <TableRow
                      key={run.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/runs/${run.id}`)}
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
