import { Badge } from "../ui/badge";
import type { RunStatus, OrderStatus } from "../../types";

type Status = RunStatus | OrderStatus;

const variants: Record<Status, { label: string; className: string }> = {
  FILLED: { label: "Filled", className: "bg-green-100 text-green-800 border-green-200" },
  FINISHED: { label: "Finished", className: "bg-blue-100 text-blue-800 border-blue-200" },
  CREATED: { label: "Created", className: "bg-gray-100 text-gray-700 border-gray-200" },
  FAILED: { label: "Failed", className: "bg-red-100 text-red-800 border-red-200" },
  SUBMITTED: { label: "Submitted", className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  CANCELLED: { label: "Cancelled", className: "bg-orange-100 text-orange-800 border-orange-200" },
};

export function StatusBadge({ status }: { status: Status }) {
  const v = variants[status] ?? { label: status, className: "" };
  return (
    <Badge variant="outline" className={v.className}>
      {v.label}
    </Badge>
  );
}
