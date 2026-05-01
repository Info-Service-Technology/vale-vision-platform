import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import BlockIcon from "@mui/icons-material/Block";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import { fetchBillingTenants, fetchMetrics, updateTenantBilling } from "../services/api";

type BillingTenant = {
  id: number;
  name: string;
  slug: string;
  scope_type?: string | null;
  scope_value?: string | null;
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
};

type BillingFormState = {
  billing_status: string;
  billing_due_date: string;
  billing_grace_until: string;
  billing_suspended_at: string;
  billing_contact_email: string;
  billing_notes: string;
  payment_method: string;
  contract_type: string;
  billing_amount: string;
  billing_currency: string;
  billing_cycle: string;
  plan_slug: string;
};

const billingStatuses = [
  "active",
  "past_due",
  "grace_period",
  "suspended_read_only",
  "suspended_full",
  "terminated",
];

function formatMessage(template: string, values: Record<string, string | number>) {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => String(values[key] ?? ""));
}

function toDateTimeLocal(value?: string | null) {
  if (!value) return "";
  return value.replace("Z", "").slice(0, 16);
}

function toApiDateTime(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function formatDate(value?: string | null, locale?: string) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleString(locale);
}

function getDaysUntil(value?: string | null) {
  if (!value) return null;
  const target = new Date(value);
  if (Number.isNaN(target.getTime())) return null;
  const now = new Date();
  const startNow = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startTarget = new Date(target.getFullYear(), target.getMonth(), target.getDate());
  return Math.ceil((startTarget.getTime() - startNow.getTime()) / 86400000);
}

function getStatusColor(status: string) {
  switch (status) {
    case "active":
      return "success";
    case "grace_period":
      return "warning";
    case "past_due":
      return "warning";
    case "suspended_read_only":
    case "suspended_full":
    case "terminated":
      return "error";
    default:
      return "default";
  }
}

function emptyForm(tenant?: BillingTenant | null): BillingFormState {
  return {
    billing_status: tenant?.billing_status || "active",
    billing_due_date: toDateTimeLocal(tenant?.billing_due_date),
    billing_grace_until: toDateTimeLocal(tenant?.billing_grace_until),
    billing_suspended_at: toDateTimeLocal(tenant?.billing_suspended_at),
    billing_contact_email: tenant?.billing_contact_email || "",
    billing_notes: tenant?.billing_notes || "",
    payment_method: tenant?.payment_method || "invoice",
    contract_type: tenant?.contract_type || "monthly_contract",
    billing_amount:
      tenant?.billing_amount !== null && tenant?.billing_amount !== undefined
        ? String(tenant.billing_amount)
        : "",
    billing_currency: tenant?.billing_currency || "BRL",
    billing_cycle: tenant?.billing_cycle || "monthly",
    plan_slug: tenant?.plan_slug || "free",
  };
}

export function BillingPage() {
  const queryClient = useQueryClient();
  const { user, tenant, logout, isSuperAdmin } = useAuth();
  const { t, lang, setLang } = useLocale();
  const [selectedTenantId, setSelectedTenantId] = useState<number | null>(tenant?.id || null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<BillingFormState>(emptyForm());
  const [feedback, setFeedback] = useState<{ error: string; success: string }>({
    error: "",
    success: "",
  });

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetchMetrics(),
    retry: false,
  });

  const billingQuery = useQuery({
    queryKey: ["billing-tenants"],
    queryFn: fetchBillingTenants,
    retry: false,
  });

  const rows = billingQuery.data || [];

  useEffect(() => {
    if (!rows.length) return;
    if (!selectedTenantId) {
      setSelectedTenantId(tenant?.id || rows[0].id);
      return;
    }
    if (!rows.some((row) => row.id === selectedTenantId)) {
      setSelectedTenantId(rows[0].id);
    }
  }, [rows, selectedTenantId, tenant?.id]);

  const currentTenant = useMemo(() => {
    if (!rows.length) return null;
    return rows.find((row) => row.id === selectedTenantId) || rows[0];
  }, [rows, selectedTenantId]);

  const dueSoonDays = getDaysUntil(currentTenant?.billing_due_date);
  const status = currentTenant?.billing_status || "active";

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!currentTenant) throw new Error("Tenant não encontrado");
      return updateTenantBilling(currentTenant.id, {
        billing_status: form.billing_status,
        billing_due_date: toApiDateTime(form.billing_due_date),
        billing_grace_until: toApiDateTime(form.billing_grace_until),
        billing_suspended_at: toApiDateTime(form.billing_suspended_at),
        billing_contact_email: form.billing_contact_email || null,
        billing_notes: form.billing_notes || null,
        payment_method: form.payment_method || null,
        contract_type: form.contract_type || null,
        billing_amount: form.billing_amount ? Number(form.billing_amount) : null,
        billing_currency: form.billing_currency || null,
        billing_cycle: form.billing_cycle || null,
        plan_slug: form.plan_slug || null,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["billing-tenants"] });
      setFeedback({ error: "", success: t("billing_save_success") });
      setDialogOpen(false);
    },
    onError: (err: any) => {
      setFeedback({
        error: err?.response?.data?.detail || t("billing_save_error"),
        success: "",
      });
    },
  });

  function openEditDialog() {
    setForm(emptyForm(currentTenant));
    setDialogOpen(true);
    setFeedback((prev) => ({ ...prev, error: "" }));
  }

  function getStatusLabel(value: string) {
    return t(`billing_status_${value}`);
  }

  function getBannerMessage(value: string) {
    const map: Record<string, string> = {
      active: "",
      past_due: t("billing_banner_past_due"),
      grace_period: t("billing_banner_grace_period"),
      suspended_read_only: t("billing_banner_suspended_read_only"),
      suspended_full: t("billing_banner_suspended_full"),
      terminated: t("billing_terminated_cta"),
    };

    return map[value] || "";
  }

  function getStatusCallout(value: string) {
    const map: Record<string, string> = {
      active: t("billing_active_details_description"),
      past_due: t("billing_past_due_cta"),
      grace_period: t("billing_grace_period_cta"),
      suspended_read_only: t("billing_suspended_read_only_cta"),
      suspended_full: t("billing_suspended_full_cta"),
      terminated: t("billing_terminated_cta"),
    };

    return map[value] || "";
  }

  function formatAmount(row?: BillingTenant | null) {
    if (!row || row.billing_amount === null || row.billing_amount === undefined) {
      return t("billing_not_available_yet");
    }

    return new Intl.NumberFormat(lang, {
      style: "currency",
      currency: row.billing_currency || "BRL",
    }).format(Number(row.billing_amount));
  }

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar role={user?.role || ""} onLogout={logout} />

      <Box
        sx={{
          flexGrow: 1,
          minHeight: "100vh",
          backgroundColor: "background.default",
          pt: "72px",
        }}
      >
        <Header
          userName={user?.name || user?.email || "Usuário"}
          systemOnline={metricsQuery.data?.system_online ?? true}
          lang={lang}
          setLang={setLang}
          onLogout={logout}
          t={t}
        />

        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h5" fontWeight={800}>
                {t("billing")}
              </Typography>
              <Typography color="text.secondary">
                {t("billing_page_subtitle")}
              </Typography>
            </Box>

            {feedback.error && <Alert severity="error">{feedback.error}</Alert>}
            {feedback.success && <Alert severity="success">{feedback.success}</Alert>}
            {billingQuery.isError && <Alert severity="error">{t("billing_load_error")}</Alert>}

            {currentTenant && getBannerMessage(status) && (
              <Alert severity={status === "active" ? "success" : "warning"}>
                {getBannerMessage(status)}
              </Alert>
            )}

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, lg: 8 }}>
                <Stack spacing={3}>
                  <Paper sx={{ p: 3 }}>
                    <Stack
                      direction={{ xs: "column", md: "row" }}
                      spacing={2}
                      justifyContent="space-between"
                      alignItems={{ xs: "flex-start", md: "center" }}
                    >
                      <Box>
                        <Typography variant="h6" fontWeight={800}>
                          {t("billing_current_scope")}
                        </Typography>
                        <Typography color="text.secondary">
                          {t("billing_current_scope_description")}
                        </Typography>
                      </Box>

                      {isSuperAdmin && rows.length > 0 && (
                        <TextField
                          select
                          size="small"
                          label={t("billing_select_tenant")}
                          value={String(selectedTenantId || rows[0].id)}
                          onChange={(event) => setSelectedTenantId(Number(event.target.value))}
                          sx={{ minWidth: 280 }}
                        >
                          {rows.map((row) => (
                            <MenuItem key={row.id} value={row.id}>
                              {row.name} ({row.slug})
                            </MenuItem>
                          ))}
                        </TextField>
                      )}
                    </Stack>

                    {currentTenant && (
                      <Stack spacing={2} sx={{ mt: 3 }}>
                        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ xs: "flex-start", md: "center" }}>
                          <Typography variant="h6" fontWeight={700}>
                            {currentTenant.name}
                          </Typography>
                          <Chip
                            color={getStatusColor(status) as any}
                            label={getStatusLabel(status)}
                          />
                          {typeof dueSoonDays === "number" && dueSoonDays >= 0 && dueSoonDays <= 10 && (
                            <Chip
                              icon={<WarningAmberIcon />}
                              color="warning"
                              label={formatMessage(t("billing_due_soon_short"), { days: dueSoonDays })}
                            />
                          )}
                        </Stack>

                        <Typography color="text.secondary">
                          {formatMessage(t("billing_states_description_dynamic"), {
                            tenant: currentTenant.name,
                            status: getStatusLabel(status),
                          })}
                        </Typography>

                        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                          <Card variant="outlined" sx={{ flex: 1 }}>
                            <CardContent>
                              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                                <ReceiptLongIcon color="primary" />
                                <Typography fontWeight={700}>{t("billing_payment_overview")}</Typography>
                              </Stack>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_payment_method")}: {currentTenant.payment_method ? t(`billing_payment_method_${currentTenant.payment_method}`) : t("billing_not_available_yet")}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_contract_type")}: {currentTenant.contract_type ? t(`billing_contract_type_${currentTenant.contract_type}`) : t("billing_not_available_yet")}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_cycle")}: {currentTenant.billing_cycle ? t(`billing_cycle_${currentTenant.billing_cycle}`) : t("billing_not_available_yet")}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_amount")}: {formatAmount(currentTenant)}
                              </Typography>
                            </CardContent>
                          </Card>

                          <Card variant="outlined" sx={{ flex: 1 }}>
                            <CardContent>
                              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                                {status === "active" ? <CheckCircleIcon color="success" /> : <BlockIcon color="warning" />}
                                <Typography fontWeight={700}>{t("billing_status_panel_title")}</Typography>
                              </Stack>
                              <Typography variant="body2" color="text.secondary">
                                {getStatusCallout(status)}
                              </Typography>
                            </CardContent>
                          </Card>
                        </Stack>

                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, md: 6 }}>
                            <Paper variant="outlined" sx={{ p: 2 }}>
                              <Typography fontWeight={700} sx={{ mb: 1 }}>
                                {t("billing_financial_status")}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_due_date")}: {formatDate(currentTenant.billing_due_date, lang)}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_grace_until")}: {formatDate(currentTenant.billing_grace_until, lang)}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_suspended_at")}: {formatDate(currentTenant.billing_suspended_at, lang)}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {t("billing_contact")}: {currentTenant.billing_contact_email || "-"}
                              </Typography>
                            </Paper>
                          </Grid>

                          <Grid size={{ xs: 12, md: 6 }}>
                            <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                              <Typography fontWeight={700} sx={{ mb: 1 }}>
                                {t("billing_debt_summary")}
                              </Typography>
                              <Typography variant="body2" color="text.secondary">
                                {currentTenant.billing_notes || t("billing_no_notes")}
                              </Typography>
                            </Paper>
                          </Grid>
                        </Grid>

                        {isSuperAdmin && (
                          <Box>
                            <Button variant="contained" startIcon={<EditIcon />} onClick={openEditDialog}>
                              {t("billing_edit_tenant_title")}
                            </Button>
                          </Box>
                        )}
                      </Stack>
                    )}
                  </Paper>

                  {isSuperAdmin && (
                    <Paper sx={{ p: 3 }}>
                      <Typography variant="h6" fontWeight={800} sx={{ mb: 2 }}>
                        {t("billing_tenants_title")}
                      </Typography>
                      <Typography color="text.secondary" sx={{ mb: 2 }}>
                        {t("billing_tenants_super_admin_hint")}
                      </Typography>

                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>{t("tenant")}</TableCell>
                            <TableCell>{t("billing_financial_status")}</TableCell>
                            <TableCell>{t("billing_due_date")}</TableCell>
                            <TableCell>{t("billing_contact")}</TableCell>
                            <TableCell>{t("billing_amount")}</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {rows.map((row) => (
                            <TableRow
                              key={row.id}
                              hover
                              selected={row.id === currentTenant?.id}
                              onClick={() => setSelectedTenantId(row.id)}
                              sx={{ cursor: "pointer" }}
                            >
                              <TableCell>{row.name}</TableCell>
                              <TableCell>
                                <Chip
                                  size="small"
                                  color={getStatusColor(row.billing_status || "active") as any}
                                  label={getStatusLabel(row.billing_status || "active")}
                                />
                              </TableCell>
                              <TableCell>{formatDate(row.billing_due_date, lang)}</TableCell>
                              <TableCell>{row.billing_contact_email || "-"}</TableCell>
                              <TableCell>{formatAmount(row)}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Paper>
                  )}
                </Stack>
              </Grid>

              <Grid size={{ xs: 12, lg: 4 }}>
                <Stack spacing={3}>
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>
                      {t("billing_visible_scope")}
                    </Typography>
                    <Typography color="text.secondary">
                      {isSuperAdmin ? t("billing_scope_super_admin") : t("billing_scope_tenant_admin")}
                    </Typography>
                  </Paper>

                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>
                      {t("billing_best_practices")}
                    </Typography>
                    <Stack spacing={1}>
                      <Typography variant="body2" color="text.secondary">
                        {t("billing_best_practice_tenant_level")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("billing_best_practice_progressive")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("billing_best_practice_read_only")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("billing_best_practice_audit")}
                      </Typography>
                    </Stack>
                  </Paper>
                </Stack>
              </Grid>
            </Grid>
          </Stack>
        </Container>
      </Box>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t("billing_edit_tenant_title")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              select
              label={t("billing_financial_status")}
              value={form.billing_status}
              onChange={(event) => setForm((prev) => ({ ...prev, billing_status: event.target.value }))}
              fullWidth
            >
              {billingStatuses.map((value) => (
                <MenuItem key={value} value={value}>
                  {getStatusLabel(value)}
                </MenuItem>
              ))}
            </TextField>

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                type="datetime-local"
                label={t("billing_due_date")}
                value={form.billing_due_date}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_due_date: event.target.value }))}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                type="datetime-local"
                label={t("billing_grace_until")}
                value={form.billing_grace_until}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_grace_until: event.target.value }))}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Stack>

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                type="datetime-local"
                label={t("billing_suspended_at")}
                value={form.billing_suspended_at}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_suspended_at: event.target.value }))}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
              <TextField
                label={t("billing_contact")}
                value={form.billing_contact_email}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_contact_email: event.target.value }))}
                fullWidth
              />
            </Stack>

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                select
                label={t("billing_payment_method")}
                value={form.payment_method}
                onChange={(event) => setForm((prev) => ({ ...prev, payment_method: event.target.value }))}
                fullWidth
              >
                {["invoice", "pix", "boleto", "card"].map((value) => (
                  <MenuItem key={value} value={value}>
                    {t(`billing_payment_method_${value}`)}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label={t("billing_contract_type")}
                value={form.contract_type}
                onChange={(event) => setForm((prev) => ({ ...prev, contract_type: event.target.value }))}
                fullWidth
              >
                {["annual_contract", "monthly_contract", "trial"].map((value) => (
                  <MenuItem key={value} value={value}>
                    {t(`billing_contract_type_${value}`)}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                label={t("billing_amount")}
                type="number"
                value={form.billing_amount}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_amount: event.target.value }))}
                fullWidth
              />
              <TextField
                label="Currency"
                value={form.billing_currency}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_currency: event.target.value }))}
                fullWidth
              />
              <TextField
                select
                label={t("billing_cycle")}
                value={form.billing_cycle}
                onChange={(event) => setForm((prev) => ({ ...prev, billing_cycle: event.target.value }))}
                fullWidth
              >
                {["annual", "monthly"].map((value) => (
                  <MenuItem key={value} value={value}>
                    {t(`billing_cycle_${value}`)}
                  </MenuItem>
                ))}
              </TextField>
            </Stack>

            <TextField
              select
              label="Plano"
              value={form.plan_slug}
              onChange={(event) => setForm((prev) => ({ ...prev, plan_slug: event.target.value }))}
              fullWidth
            >
              {["free", "pro", "enterprise"].map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`billing_plan_${value}`)}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label={t("billing_debt_summary")}
              value={form.billing_notes}
              onChange={(event) => setForm((prev) => ({ ...prev, billing_notes: event.target.value }))}
              multiline
              minRows={4}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("close")}</Button>
          <Button variant="contained" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {t("save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
