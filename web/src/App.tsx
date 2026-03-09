import { BrowserRouter, Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Layout } from "@/components/layout/Layout";
import { Overview } from "@/pages/Overview";
import { RunHistory } from "@/pages/RunHistory";
import { RunDetail } from "@/pages/RunDetail";
import { Orders } from "@/pages/Orders";
import { Instruments } from "@/pages/Instruments";
import { Preview } from "@/pages/Preview";
import { Analytics } from "@/pages/Analytics";
import { Config } from "@/pages/Config";

export default function App() {
  return (
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="runs" element={<RunHistory />} />
            <Route path="runs/:id" element={<RunDetail />} />
            <Route path="orders" element={<Orders />} />
            <Route path="instruments" element={<Instruments />} />
            <Route path="preview" element={<Preview />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="config" element={<Config />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  );
}
