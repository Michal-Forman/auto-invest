import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Gauge,
  History,
  ListOrdered,
  PlayCircle,
  Settings,
  TrendingUp,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar";

const navItems = [
  { to: "/", label: "Overview", icon: Gauge },
  { to: "/runs", label: "Run History", icon: History },
  { to: "/orders", label: "Orders", icon: ListOrdered },
  { to: "/instruments", label: "Instruments", icon: TrendingUp },
  { to: "/preview", label: "Next Run Preview", icon: PlayCircle },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/config", label: "Configuration", icon: Settings },
];

export function AppSidebar() {
  return (
    <Sidebar>
      <SidebarHeader className="px-2 py-4 md:hidden">
        <SidebarTrigger />
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map(({ to, label, icon: Icon }) => (
                <SidebarMenuItem key={to}>
                  <NavLink to={to} end={to === "/"}>
                    {({ isActive }) => (
                      <SidebarMenuButton isActive={isActive}>
                        <Icon className="h-4 w-4" />
                        <span>{label}</span>
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
