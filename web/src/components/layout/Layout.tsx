import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Outlet } from "react-router-dom";
import { api } from "@/lib/api";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { TopNav } from "./TopNav";

const MIN = 60 * 1000;

export function Layout() {
  const queryClient = useQueryClient();

  useEffect(() => {
    queryClient.prefetchQuery({ queryKey: ["profile"], queryFn: api.getProfile, staleTime: 5 * MIN });
    queryClient.prefetchQuery({ queryKey: ["health"], queryFn: api.getHealth, staleTime: 5 * MIN });
    queryClient.prefetchQuery({ queryKey: ["runs", undefined, undefined], queryFn: () => api.getRuns(), staleTime: 5 * MIN });
    queryClient.prefetchQuery({ queryKey: ["orders"], queryFn: () => api.getOrders(), staleTime: 5 * MIN });
    queryClient.prefetchQuery({ queryKey: ["instruments"], queryFn: api.getInstruments, staleTime: 15 * MIN });
    queryClient.prefetchQuery({ queryKey: ["config"], queryFn: api.getConfig, staleTime: 60 * MIN });
    queryClient.prefetchQuery({ queryKey: ["analytics", "runs"], queryFn: () => api.getAnalyticsRuns(), staleTime: 15 * MIN });
    queryClient.prefetchQuery({ queryKey: ["analytics", "allocation"], queryFn: () => api.getAnalyticsAllocation(), staleTime: 15 * MIN });
    queryClient.prefetchQuery({ queryKey: ["analytics", "status"], queryFn: () => api.getAnalyticsStatus(), staleTime: 15 * MIN });
    queryClient.prefetchQuery({ queryKey: ["analytics", "portfolioValue"], queryFn: () => api.getPortfolioValue(), staleTime: 15 * MIN });
  }, [queryClient]);

  return (
    <SidebarProvider defaultOpen={false}>
      <AppSidebar />
      <SidebarInset>
        {/* Mobile/tablet header with hamburger trigger */}
        <header className="flex lg:hidden h-12 items-center gap-2 border-b px-4 shrink-0">
          <SidebarTrigger />
        </header>
        {/* Desktop top navigation */}
        <TopNav />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
