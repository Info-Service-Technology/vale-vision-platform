import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
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
import AddIcon from "@mui/icons-material/Add";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { BillingStatusBanner } from "../components/BillingStatusBanner";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import {
  approveAdminUser,
  createAdminUser,
  deleteAdminUser,
  fetchAdminUsers,
  fetchMetrics,
  fetchPendingAdminUsers,
  fetchTenants,
  rejectAdminUser,
  updateAdminUser,
} from "../services/api";

type UserFormState = {
  id?: number;
  name: string;
  email: string;
  password: string;
  role: string;
  tenant_id: string;
};

const emptyForm: UserFormState = {
  name: "",
  email: "",
  password: "",
  role: "viewer",
  tenant_id: "",
};

export function AdminUsersPage() {
  const queryClient = useQueryClient();
  const { t, lang, setLang } = useLocale();
  const { user, tenant, isSuperAdmin, logout, canWriteTenantData } = useAuth();

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<UserFormState>(emptyForm);
  const [error, setError] = useState("");

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetchMetrics(),
    retry: false,
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users", search, roleFilter],
    queryFn: () =>
      fetchAdminUsers({
        search: search || undefined,
        role: roleFilter || undefined,
      }),
    retry: false,
  });

  const pendingUsersQuery = useQuery({
    queryKey: ["admin-users-pending"],
    queryFn: fetchPendingAdminUsers,
    retry: false,
  });

  const tenantsQuery = useQuery({
    queryKey: ["tenants"],
    queryFn: fetchTenants,
    enabled: isSuperAdmin,
    retry: false,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const tenantId = form.tenant_id ? Number(form.tenant_id) : undefined;

      if (form.id) {
        return updateAdminUser(form.id, {
          name: form.name,
          role: form.role,
          tenant_id: tenantId,
          password: form.password || undefined,
        });
      }

      return createAdminUser({
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
        tenant_id: tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-users-pending"] });
      setDialogOpen(false);
      setForm(emptyForm);
      setError("");
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || t("user_create_error"));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: number) => deleteAdminUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-users-pending"] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (userId: number) => approveAdminUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-users-pending"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (userId: number) => rejectAdminUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-users-pending"] });
    },
  });

  const tenantOptions = useMemo(() => tenantsQuery.data || [], [tenantsQuery.data]);
  const rows = usersQuery.data?.items || [];
  const pendingRows = pendingUsersQuery.data?.items || [];

  function openCreateDialog() {
    setForm({
      ...emptyForm,
      tenant_id: isSuperAdmin ? "" : String(tenant?.id || ""),
      role: isSuperAdmin ? "admin-tenant" : "viewer",
    });
    setError("");
    setDialogOpen(true);
  }

  function openEditDialog(selected: (typeof rows)[number]) {
    setForm({
      id: selected.id,
      name: selected.name,
      email: selected.email,
      password: "",
      role: selected.role,
      tenant_id: selected.tenant_id ? String(selected.tenant_id) : "",
    });
    setError("");
    setDialogOpen(true);
  }

  const roleOptions = isSuperAdmin
    ? ["super-admin", "admin-tenant", "operator", "viewer"]
    : ["admin-tenant", "operator", "viewer"];

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
            <BillingStatusBanner />

            <Box>
              <Typography variant="h5" fontWeight={800}>
                {t("users")}
              </Typography>
              <Typography color="text.secondary">
                {t("admin_user_management")}
              </Typography>
            </Box>

            <Paper sx={{ p: 2 }}>
              <Stack spacing={2} sx={{ mb: 3 }}>
                <Box>
                  <Typography variant="h6" fontWeight={700}>
                    {t("pending_users")}
                  </Typography>
                  <Typography color="text.secondary">
                    {t("pending_users_subtitle")}
                  </Typography>
                </Box>

                {pendingUsersQuery.isError && (
                  <Alert severity="error">{t("pending_users_load_error")}</Alert>
                )}

                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("first_name")}</TableCell>
                      <TableCell>{t("email")}</TableCell>
                      <TableCell>{t("role")}</TableCell>
                      <TableCell>{t("tenant")}</TableCell>
                      <TableCell>{t("created_at")}</TableCell>
                      <TableCell align="right">{t("actions")}</TableCell>
                    </TableRow>
                  </TableHead>

                  <TableBody>
                    {pendingRows.map((row) => (
                      <TableRow key={row.id} hover>
                        <TableCell>{row.name}</TableCell>
                        <TableCell>{row.email}</TableCell>
                        <TableCell>{row.role}</TableCell>
                        <TableCell>{row.tenant_name || "-"}</TableCell>
                        <TableCell>
                          {row.created_at ? new Date(row.created_at).toLocaleString(lang) : "-"}
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            size="small"
                            color="success"
                            startIcon={<CheckIcon />}
                            onClick={() => approveMutation.mutate(row.id)}
                            disabled={approveMutation.isPending || (!isSuperAdmin && !canWriteTenantData)}
                          >
                            {t("approve")}
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            startIcon={<CloseIcon />}
                            onClick={() => rejectMutation.mutate(row.id)}
                            disabled={rejectMutation.isPending || (!isSuperAdmin && !canWriteTenantData)}
                          >
                            {t("reject")}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}

                    {pendingRows.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <Typography color="text.secondary" textAlign="center" sx={{ py: 3 }}>
                            {t("no_pending_users")}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </Stack>

              <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
                <TextField
                  label={t("search_users")}
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  size="small"
                  sx={{ minWidth: 280 }}
                />

                <TextField
                  select
                  label={t("role")}
                  value={roleFilter}
                  onChange={(event) => setRoleFilter(event.target.value)}
                  size="small"
                  sx={{ minWidth: 220 }}
                >
                  <MenuItem value="">{t("all_roles")}</MenuItem>
                  {roleOptions.map((role) => (
                    <MenuItem key={role} value={role}>
                      {role}
                    </MenuItem>
                  ))}
                </TextField>

                <Box sx={{ flexGrow: 1 }} />

                <Button
                  startIcon={<AddIcon />}
                  variant="contained"
                  onClick={openCreateDialog}
                  disabled={!isSuperAdmin && !canWriteTenantData}
                >
                  {t("add_new_user")}
                </Button>
              </Stack>

              {usersQuery.isError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {t("users_fetch_error")}
                </Alert>
              )}

              <Table size="small">
                <TableHead>
                  <TableRow>
                  <TableCell>{t("first_name")}</TableCell>
                  <TableCell>{t("email")}</TableCell>
                  <TableCell>{t("role")}</TableCell>
                  <TableCell>{t("status")}</TableCell>
                  <TableCell>{t("tenant")}</TableCell>
                  <TableCell>{t("created_at")}</TableCell>
                  <TableCell align="right">{t("actions")}</TableCell>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.id} hover>
                      <TableCell>{row.name}</TableCell>
                      <TableCell>{row.email}</TableCell>
                      <TableCell>{row.role}</TableCell>
                      <TableCell>{row.approval_status || "approved"}</TableCell>
                      <TableCell>{row.tenant_name || "-"}</TableCell>
                      <TableCell>
                        {row.created_at ? new Date(row.created_at).toLocaleString(lang) : "-"}
                      </TableCell>
                      <TableCell align="right">
                        <IconButton onClick={() => openEditDialog(row)} disabled={!isSuperAdmin && !canWriteTenantData}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          color="error"
                          onClick={() => deleteMutation.mutate(row.id)}
                          disabled={deleteMutation.isPending || (!isSuperAdmin && !canWriteTenantData)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}

                  {rows.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <Typography color="text.secondary" textAlign="center" sx={{ py: 3 }}>
                          {t("no_users_found")}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Paper>
          </Stack>
        </Container>
      </Box>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{form.id ? t("edit_user") : t("add_new_user")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {error && <Alert severity="error">{error}</Alert>}

            <TextField
              label={t("first_name")}
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
              fullWidth
            />

            <TextField
              label={t("email")}
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              fullWidth
              disabled={Boolean(form.id)}
            />

            <TextField
              label={form.id ? t("new_password") : t("password")}
              type="password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              fullWidth
              helperText={form.id ? t("password_placeholder") : undefined}
            />

            <TextField
              select
              label={t("role")}
              value={form.role}
              onChange={(event) => setForm((prev) => ({ ...prev, role: event.target.value }))}
              fullWidth
            >
              {roleOptions.map((role) => (
                <MenuItem key={role} value={role}>
                  {role}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label={t("tenant")}
              value={form.tenant_id}
              onChange={(event) => setForm((prev) => ({ ...prev, tenant_id: event.target.value }))}
              fullWidth
              disabled={!isSuperAdmin}
            >
              {isSuperAdmin ? (
                tenantOptions.map((tenantOption) => (
                  <MenuItem key={tenantOption.id} value={String(tenantOption.id)}>
                    {tenantOption.name}
                  </MenuItem>
                ))
              ) : (
                <MenuItem value={String(tenant?.id || "")}>{tenant?.name || "-"}</MenuItem>
              )}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("cancel")}</Button>
          <Button
            variant="contained"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || (!isSuperAdmin && !canWriteTenantData)}
          >
            {t("save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
