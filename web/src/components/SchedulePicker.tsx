import { useState, useEffect } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";

type Frequency = "daily" | "weekly" | "monthly";

const FREQ_LABELS: Record<Frequency, string> = {
  daily: "Day",
  weekly: "Week",
  monthly: "Month",
};

interface ScheduleState {
  frequency: Frequency;
  dow: number;
  dom: number;
}

interface SchedulePickerProps {
  value: string;
  onChange: (cron: string) => void;
}

function cronToSchedule(cron: string): ScheduleState {
  const daily = cron.match(/^\* \* \* \* \*$/);
  if (daily) return { frequency: "daily", dow: 1, dom: 1 };

  const weekly = cron.match(/^\* \* \* \* ([0-7])$/);
  if (weekly) return { frequency: "weekly", dow: Number(weekly[1]), dom: 1 };

  const monthly = cron.match(/^\* \* (\d+) \* \*$/);
  if (monthly) return { frequency: "monthly", dow: 1, dom: Number(monthly[1]) };

  return { frequency: "monthly", dow: 1, dom: 1 };
}

function scheduleToCron({ frequency, dow, dom }: ScheduleState): string {
  if (frequency === "daily") return `* * * * *`;
  if (frequency === "weekly") return `* * * * ${dow}`;
  return `* * ${dom} * *`;
}

const DOW_OPTIONS = [
  { value: 1, label: "Monday" },
  { value: 2, label: "Tuesday" },
  { value: 3, label: "Wednesday" },
  { value: 4, label: "Thursday" },
  { value: 5, label: "Friday" },
  { value: 6, label: "Saturday" },
  { value: 0, label: "Sunday" },
];

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] ?? s[v] ?? s[0]);
}

const DOM_OPTIONS = Array.from({ length: 28 }, (_, i) => ({
  value: i + 1,
  label: ordinal(i + 1),
}));

export function SchedulePicker({ value, onChange }: SchedulePickerProps) {
  const [schedule, setSchedule] = useState<ScheduleState>(() => cronToSchedule(value));

  useEffect(() => {
    setSchedule(cronToSchedule(value));
  }, [value]);

  function update(patch: Partial<ScheduleState>) {
    const next = { ...schedule, ...patch };
    setSchedule(next);
    onChange(scheduleToCron(next));
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-muted-foreground">Every</span>

      <Select value={schedule.frequency} onValueChange={(v) => update({ frequency: v as Frequency })}>
        <SelectTrigger className="w-32">
          <span className="flex flex-1 text-left text-sm">{FREQ_LABELS[schedule.frequency]}</span>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="daily">Day</SelectItem>
          <SelectItem value="weekly">Week</SelectItem>
          <SelectItem value="monthly">Month</SelectItem>
        </SelectContent>
      </Select>

      {(schedule.frequency === "weekly" || schedule.frequency === "monthly") && (
        <span className="text-sm text-muted-foreground">on</span>
      )}

      {schedule.frequency === "weekly" && (
        <Select value={String(schedule.dow)} onValueChange={(v) => update({ dow: Number(v) })}>
          <SelectTrigger className="w-36">
            <span className="flex flex-1 text-left text-sm">
              {DOW_OPTIONS.find((o) => o.value === schedule.dow)?.label}
            </span>
          </SelectTrigger>
          <SelectContent>
            {DOW_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={String(o.value)}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {schedule.frequency === "monthly" && (
        <Select value={String(schedule.dom)} onValueChange={(v) => update({ dom: Number(v) })}>
          <SelectTrigger className="w-24">
            <span className="flex flex-1 text-left text-sm">{ordinal(schedule.dom)}</span>
          </SelectTrigger>
          <SelectContent>
            {DOM_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={String(o.value)}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
