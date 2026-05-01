import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchMe, login as loginRequest } from "../services/api";
import { canTenantWrite, isBillingRestrictedStatus, normalizeBillingStatus } from "../utils/billing";

type AuthUser = {
  id: number;
  name?: string;
  email: string;
  role: string;
  approval_status?: string | null;
  is_active?: boolean | null;
  avatar_url?: string | null;
  phone?: string | null;
  about?: string | null;
  tenant_id?: number | null;
  tenant_slug?: string | null;
  tenant_name?: string | null;
};

type AuthTenant = {
  id: number;
  name: string;
  slug: string;
  scope_type?: string;
  scope_value?: string;
  company_logo_url?: string | null;
  billing_status?: string | null;
  billing_due_date?: string | null;
  billing_grace_until?: string | null;
  billing_suspended_at?: string | null;
  billing_contact_email?: string | null;
  billing_notes?: string | null;
  payment_method?: string | null;
  contract_type?: string | null;
  billing_amount?: number | null;
  billing_currency?: string | null;
  billing_cycle?: string | null;
  plan_slug?: string | null;
  platform_title?: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  tenant: AuthTenant | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
  billingStatus: string;
  isBillingRestricted: boolean;
  canWriteTenantData: boolean;
  login: (email: string, password: string, tenantSlug?: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("vale_token"));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem("vale_user");
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  });
  const [tenant, setTenant] = useState<AuthTenant | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshMe() {
    const data = await fetchMe();

    setUser(data.user ?? null);
    setTenant(data.tenant ?? null);

    if (data.user) {
      localStorage.setItem("vale_user", JSON.stringify(data.user));
    } else {
      localStorage.removeItem("vale_user");
    }

    if (data.tenant) {
      localStorage.setItem("vale_tenant", JSON.stringify(data.tenant));
    } else {
      localStorage.removeItem("vale_tenant");
    }
  }

  function logout() {
    setToken(null);
    setUser(null);
    setTenant(null);
    localStorage.removeItem("vale_token");
    localStorage.removeItem("vale_user");
    localStorage.removeItem("vale_tenant");
    localStorage.removeItem("vale_tenant_slug");
  }

  async function login(email: string, password: string, tenantSlug?: string) {
    const response = await loginRequest(email, password, tenantSlug);

    setToken(response.access_token);
    localStorage.setItem("vale_token", response.access_token);

    if (tenantSlug) {
      localStorage.setItem("vale_tenant_slug", tenantSlug);
    }

    await refreshMe();
  }

  useEffect(() => {
    let alive = true;

    async function loadSession() {
      if (!token) {
        if (alive) {
          setLoading(false);
          setUser(null);
          setTenant(null);
        }
        return;
      }

      try {
        await refreshMe();
      } catch {
        if (alive) logout();
      } finally {
        if (alive) setLoading(false);
      }
    }

    loadSession();

    return () => {
      alive = false;
    };
  }, [token]);

  const value = useMemo(
    () => {
      const billingStatus = normalizeBillingStatus(tenant?.billing_status);
      const isSuperAdmin = user?.role === "super-admin";

      return {
        user,
        tenant,
        token,
        loading,
        isAuthenticated: !!token,
        isAdmin: user?.role === "admin-tenant" || isSuperAdmin,
        isSuperAdmin,
        billingStatus,
        isBillingRestricted: !isSuperAdmin && isBillingRestrictedStatus(billingStatus),
        canWriteTenantData: isSuperAdmin || canTenantWrite(billingStatus),
        login,
        logout,
        refreshMe,
      };
    },
    [user, tenant, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return ctx;
}
