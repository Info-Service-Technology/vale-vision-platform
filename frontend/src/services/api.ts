import axios from "axios";
import { EventsResponse, MetricsResponse } from "../types/events";

export const api = axios.create({ baseURL: "/api", timeout: 30000 });
api.interceptors.request.use((config) => { const token = localStorage.getItem("vale_token"); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });

export async function login(email: string, password: string, tenantSlug?: string) {
  const { data } = await api.post("/auth/login", {
    email,
    password,
    tenant_slug: tenantSlug,
  });
  return data as {
    access_token: string;
    user?: {
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
  };
}
export async function fetchMetrics(container?: string) {
  const { data } = await api.get<MetricsResponse>("/events/metrics", { params: { container } });
  return data;
}
export async function fetchEvents(params: { page: number; page_size: number; container?: string; search?: string; activeOnly?: boolean }) {
  const { data } = await api.get<EventsResponse>("/events", { params: { page: params.page, page_size: params.page_size, container: params.container, search: params.search, active_only: params.activeOnly ?? true } });
  return data;
}
export async function fetchImageUrl(eventId: number) {
  const { data } = await api.get<{ url: string }>(`/events/${eventId}/image-url`);
  return data.url;
}
export async function resolveEvent(eventId: number, reason: string) {
  const { data } = await api.patch(`/events/${eventId}/resolve`, { reason });
  return data;
}

export async function fetchCurrentTenant() {
  const savedTenantSlug = localStorage.getItem("vale_tenant_slug");
  const { data } = await api.get<{
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
  }>("/tenants/current", {
    params: {
      slug: savedTenantSlug || undefined,
    },
  });

  return data;
}

export async function fetchTenantBySlug(slug: string) {
  const { data } = await api.get<{
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
  }>("/tenants/current", {
    params: {
      slug,
    },
  });

  return data;
}

export async function fetchResolvedEvents(params: {
  page: number;
  page_size: number;
  search?: string;
}) {
  const { data } = await api.get<EventsResponse>("/events/resolved", {
    params,
  });

  return data;
}

export async function fetchMe() {
  const { data } = await api.get<{
    user: {
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
    } | null;
    tenant: {
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
    } | null;
  }>("/account/me");

  return data;
}

export async function fetchTenants() {
  const { data } = await api.get<{
    items: Array<{
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
    }>;
  }>("/tenants");

  return data.items;
}

export async function fetchAdminUsers(params?: {
  search?: string;
  role?: string;
  approval_status?: string;
  tenant_id?: number;
}) {
  const { data } = await api.get<{
    items: Array<{
      id: number;
      name: string;
      email: string;
      role: string;
      approval_status?: string | null;
      is_active?: boolean | null;
      tenant_id?: number | null;
      tenant_slug?: string | null;
      tenant_name?: string | null;
      created_at?: string | null;
    }>;
    total: number;
  }>("/admin/users", {
    params,
  });

  return data;
}

export async function createAdminUser(payload: {
  name: string;
  email: string;
  password: string;
  role: string;
  tenant_id?: number;
}) {
  const { data } = await api.post("/admin/users", payload);
  return data;
}

export async function updateAdminUser(
  userId: number,
  payload: {
    name: string;
    role: string;
    tenant_id?: number;
    password?: string;
  }
) {
  const { data } = await api.put(`/admin/users/${userId}`, payload);
  return data;
}

export async function deleteAdminUser(userId: number) {
  const { data } = await api.delete(`/admin/users/${userId}`);
  return data;
}

export async function fetchPendingAdminUsers() {
  const { data } = await api.get<{
    items: Array<{
      id: number;
      name: string;
      email: string;
      role: string;
      approval_status?: string | null;
      is_active?: boolean | null;
      tenant_id?: number | null;
      tenant_slug?: string | null;
      tenant_name?: string | null;
      created_at?: string | null;
    }>;
    total: number;
  }>("/admin/users/pending");

  return data;
}

export async function approveAdminUser(userId: number) {
  const { data } = await api.post(`/admin/users/${userId}/approve`);
  return data;
}

export async function rejectAdminUser(userId: number) {
  const { data } = await api.post(`/admin/users/${userId}/reject`);
  return data;
}

export async function fetchAdminAuditLogs(params: {
  page: number;
  page_size: number;
}) {
  const { data } = await api.get<{
    items: Array<{
      id: number;
      user_id?: number | null;
      user_email?: string | null;
      tenant_id?: number | null;
      tenant?: string | null;
      action: string;
      method: string;
      endpoint: string;
      status: number;
      details?: string | null;
      created_at?: string | null;
    }>;
    pagination: {
      page: number;
      page_size: number;
      total: number;
      pages: number;
      has_prev: boolean;
      has_next: boolean;
    };
  }>("/admin/audit/logs", {
    params,
  });

  return data;
}

export async function updateMyProfile(payload: {
  name?: string;
  phone?: string;
  about?: string;
  avatar_url?: string;
}) {
  const { data } = await api.put("/account/me", payload);
  return data;
}

export async function uploadMyAvatar(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<{ avatar_url: string }>("/account/avatar", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return data;
}

export async function uploadCurrentTenantLogo(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<{ company_logo_url: string }>(
    "/tenants/current/logo",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return data;
}

export async function fetchBillingTenants() {
  const { data } = await api.get<{
    items: Array<{
      id: number;
      name: string;
      slug: string;
      scope_type?: string | null;
      scope_value?: string | null;
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
      platform_title?: string | null;
    }>;
  }>("/billing/tenants");

  return data.items;
}

export async function updateTenantBilling(
  tenantId: number,
  payload: {
    billing_status: string;
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
  }
) {
  const { data } = await api.put(`/admin/billing/tenants/${tenantId}`, payload);
  return data;
}

export async function fetchAdminTenants() {
  const { data } = await api.get<{
    items: Array<{
      id: number;
      name: string;
      slug: string;
      scope_type?: string | null;
      scope_value?: string | null;
      is_active?: boolean | null;
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
      platform_title?: string | null;
    }>;
  }>("/admin/tenants");

  return data.items;
}

export async function createAdminTenant(payload: {
  name: string;
  slug: string;
  scope_type?: string;
  scope_value?: string;
  is_active?: boolean;
  billing_contact_email?: string | null;
  plan_slug?: string | null;
}) {
  const { data } = await api.post("/admin/tenants", payload);
  return data;
}

export async function updateAdminTenant(
  tenantId: number,
  payload: {
    name: string;
    slug: string;
    scope_type?: string;
    scope_value?: string;
    is_active?: boolean;
    billing_contact_email?: string | null;
    plan_slug?: string | null;
  }
) {
  const { data } = await api.put(`/admin/tenants/${tenantId}`, payload);
  return data;
}

export async function fetchTenantDomains(tenantId: number) {
  const { data } = await api.get<{
    tenant: {
      id: number;
      name: string;
      slug: string;
    };
    items: Array<{
      id: number;
      tenant_id: number;
      domain: string;
      is_verified?: boolean | null;
      is_primary?: boolean | null;
      is_active?: boolean | null;
      match_mode?: string | null;
      created_at?: string | null;
    }>;
  }>(`/admin/tenants/${tenantId}/domains`);

  return data;
}

export async function createTenantDomain(
  tenantId: number,
  payload: {
    domain: string;
    is_verified?: boolean;
    is_primary?: boolean;
    is_active?: boolean;
    match_mode?: string;
  }
) {
  const { data } = await api.post(`/admin/tenants/${tenantId}/domains`, payload);
  return data;
}

export async function deleteTenantDomain(domainId: number) {
  const { data } = await api.delete(`/admin/tenants/domains/${domainId}`);
  return data;
}

export async function fetchTenantBillingEvents(tenantId: number) {
  const { data } = await api.get<{
    tenant: {
      id: number;
      name: string;
      slug: string;
    };
    items: Array<{
      id: number;
      tenant_id: number;
      event_type: string;
      previous_status?: string | null;
      next_status?: string | null;
      message?: string | null;
      actor_user_id?: number | null;
      actor_email?: string | null;
      created_at?: string | null;
    }>;
  }>(`/admin/tenants/${tenantId}/billing-events`);

  return data;
}
