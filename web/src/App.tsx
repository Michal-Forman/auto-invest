import { BrowserRouter, Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/lib/auth-context";
import { Layout } from "@/components/layout/Layout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Overview } from "@/pages/Overview";
import { RunHistory } from "@/pages/RunHistory";
import { RunDetail } from "@/pages/RunDetail";
import { Orders } from "@/pages/Orders";
import { Instruments } from "@/pages/Instruments";
import { Preview } from "@/pages/Preview";
import { Analytics } from "@/pages/Analytics";
import { Profile } from "@/pages/Profile";
import { Login } from "@/pages/Login";
import { Signup } from "@/pages/Signup";
import { ResetPassword } from "@/pages/ResetPassword";

export default function App() {
  return (
    <TooltipProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route index element={<Overview />} />
                <Route path="runs" element={<RunHistory />} />
                <Route path="runs/:id" element={<RunDetail />} />
                <Route path="orders" element={<Orders />} />
                <Route path="instruments" element={<Instruments />} />
                <Route path="preview" element={<Preview />} />
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
