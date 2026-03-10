import { NavLink } from "react-router-dom";
import logo from "@/assets/logo_white.png";

const navItems = [
  { to: "/", label: "Overview" },
  { to: "/runs", label: "Run History" },
  { to: "/orders", label: "Orders" },
  { to: "/instruments", label: "Instruments" },
  { to: "/preview", label: "Next Run Preview" },
  { to: "/analytics", label: "Analytics" },
  { to: "/config", label: "Configuration" },
];

export function TopNav() {
  return (
    <header className="hidden lg:flex h-14 items-center border-b bg-sidebar px-6 gap-8 shrink-0">
      <div className="flex items-center gap-2.5 shrink-0">
        <img src={logo} alt="auto-invest logo" className="h-7 w-7 shrink-0" />
        <span className="font-semibold text-sm text-sidebar-foreground">auto-invest</span>
      </div>
      <nav className="flex items-center gap-1">
        {navItems.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              [
                "px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50",
              ].join(" ")
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}
