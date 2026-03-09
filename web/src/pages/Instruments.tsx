import { useState } from "react";
import { usePageTitle } from "@/hooks/use-page-title";
import { mockInstruments } from "@/data/mock";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { CapType } from "@/types";

type SortKey = keyof (typeof mockInstruments)[0];

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

  function handleSort(key: SortKey) {
    if (key === sortKey) setAsc(!asc);
    else { setSortKey(key); setAsc(true); }
  }

  const sorted = [...mockInstruments].sort((a, b) => {
    const va = a[sortKey];
    const vb = b[sortKey];
    if (typeof va === "number" && typeof vb === "number") return asc ? va - vb : vb - va;
    return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });

  function SortHeader({ label, col }: { label: string; col: SortKey }) {
    return (
      <TableHead
        className="cursor-pointer select-none hover:bg-muted/50"
        onClick={() => handleSort(col)}
      >
        {label} {sortKey === col ? (asc ? "↑" : "↓") : ""}
      </TableHead>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Instruments</h1>
      <Card>
        <CardContent className="p-0 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <SortHeader label="Ticker" col="ticker" />
                <SortHeader label="Exchange" col="exchange" />
                <SortHeader label="Cap" col="cap_type" />
                <SortHeader label="Weight %" col="target_weight" />
                <SortHeader label="ATH" col="ath_price" />
                <SortHeader label="Current" col="current_price" />
                <SortHeader label="Drop %" col="drop_pct" />
                <SortHeader label="Multiplier" col="multiplier" />
                <SortHeader label="Next CZK" col="next_czk" />
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
                  <TableCell>{(inst.target_weight * 100).toFixed(1)}%</TableCell>
                  <TableCell>{inst.ath_price.toLocaleString()}</TableCell>
                  <TableCell>{inst.current_price.toLocaleString()}</TableCell>
                  <TableCell className={`font-medium ${dropColor(inst.drop_pct)}`}>
                    {inst.drop_pct.toFixed(1)}%
                  </TableCell>
                  <TableCell>{inst.multiplier.toFixed(2)}×</TableCell>
                  <TableCell className="font-medium">{inst.next_czk.toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
