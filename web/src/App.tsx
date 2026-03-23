import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth-context";
import { Layout } from "@/components/layout/Layout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Overview } from "@/pages/Overview";
import { History } from "@/pages/History";
import { RunDetail } from "@/pages/RunDetail";
import { Instruments } from "@/pages/Instruments";
import { Invest } from "@/pages/Invest";
import { Analytics } from "@/pages/Analytics";
import { Profile } from "@/pages/Profile";
import { Login } from "@/pages/Login";
import { Signup } from "@/pages/Signup";
import { ResetPassword } from "@/pages/ResetPassword";
import { Landing } from "@/pages/Landing";

export default function App() {
  return (
    <TooltipProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/app" element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route index element={<Overview />} />
                <Route path="history" element={<History />} />
                <Route path="runs" element={<Navigate to="/app/history" replace />} />
                <Route path="runs/:id" element={<RunDetail />} />
                <Route path="orders" element={<Navigate to="/app/history" replace />} />
                <Route path="instruments" element={<Instruments />} />
                <Route path="invest" element={<Invest />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="profile" element={<Profile />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  );
}
