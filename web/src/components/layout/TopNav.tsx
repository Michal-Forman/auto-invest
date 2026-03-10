import { Link, NavLink } from "react-router-dom";
import { UserCircle } from "lucide-react";
import logo from "@/assets/logo_white.png";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { to: "/", label: "Overview" },
  { to: "/runs", label: "Run History" },
  { to: "/orders", label: "Orders" },
  { to: "/instruments", label: "Instruments" },
  { to: "/preview", label: "Next Run Preview" },
  { to: "/analytics", label: "Analytics" },
];

export function TopNav() {
  const { session } = useAuth();
  const avatarUrl = session?.user.user_metadata?.avatar_url as string | undefined;
  const displayName =
    (session?.user.user_metadata?.full_name as string | undefined) ??
    session?.user.email ??
    "";

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
      <Link
        to="/profile"
        className="ml-auto flex items-center gap-2 text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt={displayName} className="h-7 w-7 rounded-full object-cover" />
        ) : (
          <UserCircle className="h-7 w-7" />
        )}
        <span className="text-sm whitespace-nowrap">{displayName}</span>
      </Link>
    </header>
  );
}
