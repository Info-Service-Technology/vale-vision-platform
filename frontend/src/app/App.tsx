import { Navigate, Route, Routes } from "react-router-dom";
import { CircularProgress, Stack } from "@mui/material";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { AuditPage } from "../pages/AuditPage";
import { AdminUsersPage } from "../pages/AdminUsersPage";
import { AdminAuditPage } from "../pages/AdminAuditPage";
import { HelpPage } from "../pages/HelpPage";
import { BillingPage } from "../pages/BillingPage";
import { AdminTenantsPage } from "../pages/AdminTenantsPage";
// NOVAS PÁGINAS (vamos criar depois)
import { RegisterPage } from "../pages/RegisterPage";
import { ForgotPasswordPage } from "../pages/ForgotPasswordPage";
import { ResetPasswordPage } from "../pages/ResetPasswordPage";
import { CacambasPage } from "../pages/CacambasPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SystemPage } from "../pages/SystemPage";
import { useAuth } from "../context/AuthContext";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <Stack minHeight="100vh" alignItems="center" justifyContent="center">
        <CircularProgress />
      </Stack>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) {
    return (
      <Stack minHeight="100vh" alignItems="center" justifyContent="center">
        <CircularProgress />
      </Stack>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

function RequireSuperAdmin({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isSuperAdmin, loading } = useAuth();

  if (loading) {
    return (
      <Stack minHeight="100vh" alignItems="center" justifyContent="center">
        <CircularProgress />
      </Stack>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isSuperAdmin) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>

      {/* públicas */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {/* protegidas */}
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        }
      />
      <Route
        path="/audit"
        element={
          <RequireAuth>
            <AuditPage />
          </RequireAuth>
        }
      />
      <Route
        path="/cacambas"
        element={
          <RequireAuth>
            <CacambasPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin/users"
        element={
          <RequireAdmin>
            <AdminUsersPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/audit"
        element={
          <RequireSuperAdmin>
            <AdminAuditPage />
          </RequireSuperAdmin>
        }
      />
      <Route
        path="/admin/tenants"
        element={
          <RequireSuperAdmin>
            <AdminTenantsPage />
          </RequireSuperAdmin>
        }
      />
      <Route
        path="/ajuda"
        element={
          <RequireAuth>
            <HelpPage />
          </RequireAuth>
        }
      />
      <Route
        path="/sistema"
        element={
          <RequireAuth>
            <SystemPage />
          </RequireAuth>
        }
      />
      <Route
        path="/perfil"
        element={
          <RequireAuth>
            <ProfilePage />
          </RequireAuth>
        }
      />
      <Route
        path="/billing"
        element={
          <RequireAuth>
            <BillingPage />
          </RequireAuth>
        }
      />

      {/* fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
