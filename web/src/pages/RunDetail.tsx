import { useParams, useNavigate } from "react-router-dom";
import { usePageTitle } from "@/hooks/use-page-title";
import { useRunDetail } from "@/hooks/use-run-detail";
import { formatNumber } from "@/lib/utils";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ChevronLeft } from "lucide-react";

const STATUS_STEPS = ["CREATED", "FINISHED", "FILLED"] as const;

export function RunDetail() {
  usePageTitle("Run Detail");
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: run, loading, error } = useRunDetail(id);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ChevronLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <Skeleton className="h-8 w-32" />
        </div>
        <Card>
          <CardHeader><CardTitle className="text-base">Run Summary</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">State Timeline</CardTitle></CardHeader>
          <CardContent><Skeleton className="h-10 w-full" /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Orders</CardTitle></CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  {Array.from({ length: 6 }).map((__, j) => (
                    <TableHead key={j}><Skeleton className="h-4 w-full" /></TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((__, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    );
  }
  if (error || !run) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ChevronLeft className="h-4 w-4 mr-1" /> Back
        </Button>
        <p className="text-muted-foreground">{error ? "Failed to load data." : "Run not found."}</p>
      </div>
    );
  }

  const currentStep = STATUS_STEPS.indexOf(run.status as (typeof STATUS_STEPS)[number]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ChevronLeft className="h-4 w-4 mr-1" /> Back
        </Button>
        <h1 className="text-2xl font-semibold">Run Detail</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Run Summary</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-muted-foreground">Date</div>
            <div className="font-medium">
              {new Date(run.created_at).toLocaleDateString("en-GB", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Status</div>
            <div className="mt-1"><StatusBadge status={run.status} /></div>
          </div>
          <div>
            <div className="text-sm text-muted-foreground">Total CZK</div>
            <div className="font-medium">
              {run.total_czk > 0 ? `${formatNumber(run.total_czk)} CZK` : "—"}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">State Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            {STATUS_STEPS.map((step, i) => {
              const done = run.status === "FAILED" ? false : i <= currentStep;
              const active = i === currentStep;
              return (
                <div key={step} className="flex items-center gap-2">
                  <div className="flex flex-col items-center gap-1">
                    <div
                      className={`h-3 w-3 rounded-full border-2 ${
                        done
                          ? active
                            ? "border-primary bg-primary"
                            : "border-green-500 bg-green-500"
                          : "border-muted-foreground bg-background"
                      }`}
                    />
                    <span className="text-xs text-muted-foreground">{step}</span>
                  </div>
                  {i < STATUS_STEPS.length - 1 && (
                    <div className={`mb-4 h-px w-16 ${done && i < currentStep ? "bg-green-500" : "bg-border"}`} />
                  )}
                </div>
              );
            })}
            {run.status === "FAILED" && (
              <div className="flex flex-col items-center gap-1 ml-4">
                <div className="h-3 w-3 rounded-full border-2 border-red-500 bg-red-500" />
                <span className="text-xs text-red-600">FAILED</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {run.orders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Orders</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Exchange</TableHead>
                  <TableHead className="text-right">CZK</TableHead>
                  <TableHead className="text-right">Qty</TableHead>
                  <TableHead className="text-right">Fill Price</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.orders.map((order) => (
                  <TableRow key={order.id}>
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
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
