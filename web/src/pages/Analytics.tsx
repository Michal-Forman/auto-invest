import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { usePageTitle } from "@/hooks/use-page-title";
import { mockRunHistory, mockAllocationHistory, mockDropHistory, mockStatusBreakdown, mockPortfolioGrowth } from "@/data/mock";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = ["#1e3a8a", "#1e40af", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#f59e0b", "#10b981"];
const STATUS_COLORS: Record<string, string> = {
  FILLED: "#10b981",
  FINISHED: "#1e3a8a",
  FAILED: "#ef4444",
  CREATED: "#9ca3af",
};

const INSTRUMENTS = ["VWCE", "IWDA", "CSPX", "EIMI", "IUSN", "IQQH", "2B7K", "BTC"];
const DROP_INSTRUMENTS = ["VWCE", "IWDA", "CSPX", "EIMI", "IQQH", "BTC"];

export function Analytics() {
  usePageTitle("Analytics");
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-primary">Analytics</h1>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">CZK Invested per Run</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={mockRunHistory} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="czk" fill="#1e3a8a" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
            <CardTitle className="text-base text-primary">Run Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={mockStatusBreakdown.filter((d) => d.count > 0)}
                  dataKey="count"
                  nameKey="status"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ status, count }) => `${status} (${count})`}
                  labelLine
                >
                  {mockStatusBreakdown.filter((d) => d.count > 0).map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? "#9ca3af"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Allocation % per Instrument over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={mockAllocationHistory} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {INSTRUMENTS.map((key, i) => (
                <Bar key={key} dataKey={key} stackId="a" fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Portfolio Value Over Time (CZK)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={mockPortfolioGrowth} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => [`${v.toLocaleString()} CZK`, "Total Invested"]} />
              <Line type="monotone" dataKey="total" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="-mt-4 border-b bg-primary/5 pt-4">
          <CardTitle className="text-base text-primary">Drop-from-ATH % per Instrument</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={mockDropHistory} margin={{ top: 4, right: 8, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {DROP_INSTRUMENTS.map((key, i) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[i % COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
