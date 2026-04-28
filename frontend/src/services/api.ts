import axios from "axios";
import { EventsResponse, MetricsResponse } from "../types/events";

export const api = axios.create({ baseURL: "/api", timeout: 30000 });
api.interceptors.request.use((config) => { const token = localStorage.getItem("vale_token"); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });

export async function login(email: string, password: string) {
  const { data } = await api.post("/auth/login", { email, password });
  return data as { access_token: string; user?: { id: number; name?: string; email: string; role: string } };
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
  const { data } = await api.get<{
    id: number;
    name: string;
    slug: string;
    scope_type?: string;
    scope_value?: string;
    platform_title?: string;
  }>("/tenants/current");

  return data;
}
