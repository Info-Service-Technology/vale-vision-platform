import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import HubIcon from "@mui/icons-material/Hub";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";
import {
  createAdminTenant,
  createTenantDomain,
  deleteTenantDomain,
  fetchAdminTenants,
  fetchMetrics,
  fetchTenantBillingEvents,
  fetchTenantDomains,
  updateAdminTenant,
} from "../services/api";

type TenantFormState = {
  id?: number;
  name: string;
  slug: string;
  scope_type: string;
  scope_value: string;
  is_active: boolean;
  billing_contact_email: string;
  plan_slug: string;
};

const emptyTenantForm: TenantFormState = {
  name: "",
  slug: "",
  scope_type: "ORG",
  scope_value: "global",
  is_active: true,
  billing_contact_email: "",
  plan_slug: "free",
};

export function AdminTenantsPage() {
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useLocale();
  const [selectedTenantId, setSelectedTenantId] = useState<number | null>(null);
  const [tenantDialogOpen, setTenantDialogOpen] = useState(false);
  const [domainDialogOpen, setDomainDialogOpen] = useState(false);
  const [tenantForm, setTenantForm] = useState<TenantFormState>(emptyTenantForm);
  const [domainForm, setDomainForm] = useState({
    domain: "",
    match_mode: "exact",
    is_primary: false,
    is_verified: true,
    is_active: true,
  });
  const [feedback, setFeedback] = useState({ error: "", success: "" });

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetchMetrics(),
    retry: false,
  });

  const tenantsQuery = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: fetchAdminTenants,
    retry: false,
  });

  const tenants = tenantsQuery.data || [];

  useEffect(() => {
    if (!tenants.length) return;
    if (!selectedTenantId || !tenants.some((tenant) => tenant.id === selectedTenantId)) {
      setSelectedTenantId(tenants[0].id);
    }
  }, [tenants, selectedTenantId]);

  const currentTenant = useMemo(
    () => tenants.find((tenant) => tenant.id === selectedTenantId) || null,
    [tenants, selectedTenantId]
  );

  const domainsQuery = useQuery({
    queryKey: ["tenant-domains", selectedTenantId],
    queryFn: () => fetchTenantDomains(selectedTenantId as number),
    enabled: Boolean(selectedTenantId),
    retry: false,
  });

  const billingEventsQuery = useQuery({
    queryKey: ["tenant-billing-events", selectedTenantId],
    queryFn: () => fetchTenantBillingEvents(selectedTenantId as number),
    enabled: Boolean(selectedTenantId),
    retry: false,
  });

  const saveTenantMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name: tenantForm.name,
        slug: tenantForm.slug,
        scope_type: tenantForm.scope_type,
        scope_value: tenantForm.scope_value,
        is_active: tenantForm.is_active,
        billing_contact_email: tenantForm.billing_contact_email || null,
        plan_slug: tenantForm.plan_slug || "free",
      };

      if (tenantForm.id) {
        return updateAdminTenant(tenantForm.id, payload);
      }

      return createAdminTenant(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-tenants"] });
      setTenantDialogOpen(false);
      setTenantForm(emptyTenantForm);
      setFeedback({ error: "", success: "Tenant salvo com sucesso." });
    },
    onError: (err: any) => {
      setFeedback({
        error: err?.response?.data?.detail || "Não foi possível salvar o tenant.",
        success: "",
      });
    },
  });

  const createDomainMutation = useMutation({
    mutationFn: async () => {
      if (!selectedTenantId) throw new Error("Tenant não selecionado");
      return createTenantDomain(selectedTenantId, domainForm);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tenant-domains", selectedTenantId] });
      setDomainDialogOpen(false);
      setDomainForm({
        domain: "",
        match_mode: "exact",
        is_primary: false,
        is_verified: true,
        is_active: true,
      });
      setFeedback({ error: "", success: "Domínio cadastrado com sucesso." });
    },
    onError: (err: any) => {
      setFeedback({
        error: err?.response?.data?.detail || "Não foi possível cadastrar o domínio.",
        success: "",
      });
    },
  });

  const deleteDomainMutation = useMutation({
    mutationFn: (domainId: number) => deleteTenantDomain(domainId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tenant-domains", selectedTenantId] });
      setFeedback({ error: "", success: "Domínio removido com sucesso." });
    },
    onError: (err: any) => {
      setFeedback({
        error: err?.response?.data?.detail || "Não foi possível remover o domínio.",
        success: "",
      });
    },
  });

  function openCreateTenant() {
    setTenantForm(emptyTenantForm);
    setTenantDialogOpen(true);
  }

  function openEditTenant() {
    if (!currentTenant) return;
    setTenantForm({
      id: currentTenant.id,
      name: currentTenant.name,
      slug: currentTenant.slug,
      scope_type: currentTenant.scope_type || "ORG",
      scope_value: currentTenant.scope_value || "global",
      is_active: currentTenant.is_active ?? true,
      billing_contact_email: currentTenant.billing_contact_email || "",
      plan_slug: currentTenant.plan_slug || "free",
    });
    setTenantDialogOpen(true);
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
                Governança de Tenants
              </Typography>
              <Typography color="text.secondary">
                Gestão global de organizações monitoradas, domínios autorizados e trilha de billing.
              </Typography>
            </Box>

            {feedback.error && <Alert severity="error">{feedback.error}</Alert>}
            {feedback.success && <Alert severity="success">{feedback.success}</Alert>}

            <Paper sx={{ p: 2 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ xs: "stretch", md: "center" }}>
                <TextField
                  select
                  label="Tenant"
                  value={selectedTenantId ? String(selectedTenantId) : ""}
                  onChange={(event) => setSelectedTenantId(Number(event.target.value))}
                  sx={{ minWidth: 320 }}
                >
                  {tenants.map((tenant) => (
                    <MenuItem key={tenant.id} value={tenant.id}>
                      {tenant.name} ({tenant.slug})
                    </MenuItem>
                  ))}
                </TextField>

                <Button startIcon={<AddIcon />} variant="contained" onClick={openCreateTenant}>
                  Novo tenant
                </Button>

                <Button
                  startIcon={<EditIcon />}
                  variant="outlined"
                  onClick={openEditTenant}
                  disabled={!currentTenant}
                >
                  Editar tenant
                </Button>
              </Stack>
            </Paper>

            {currentTenant && (
              <Stack spacing={3}>
                <Paper sx={{ p: 3 }}>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between">
                    <Box>
                      <Typography variant="h6" fontWeight={800}>
                        {currentTenant.name}
                      </Typography>
                      <Typography color="text.secondary">
                        Slug: {currentTenant.slug} | Escopo: {currentTenant.scope_type || "ORG"} / {currentTenant.scope_value || "global"}
                      </Typography>
                    </Box>

                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        color={currentTenant.is_active === false ? "default" : "success"}
                        label={currentTenant.is_active === false ? "Inativo" : "Ativo"}
                      />
                      <Chip
                        color={currentTenant.billing_status === "active" ? "success" : "warning"}
                        label={currentTenant.billing_status || "active"}
                      />
                      <Chip label={`Plano ${currentTenant.plan_slug || "free"}`} />
                    </Stack>
                  </Stack>
                </Paper>

                <Stack direction={{ xs: "column", lg: "row" }} spacing={3} alignItems="stretch">
                  <Paper sx={{ p: 3, flex: 1 }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                      <Box>
                        <Typography variant="h6" fontWeight={800}>
                          Domínios do tenant
                        </Typography>
                        <Typography color="text.secondary">
                          Descoberta explícita de tenant no estilo HDI, sem fallback inseguro.
                        </Typography>
                      </Box>
                      <Button startIcon={<HubIcon />} variant="outlined" onClick={() => setDomainDialogOpen(true)}>
                        Novo domínio
                      </Button>
                    </Stack>

                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Domínio</TableCell>
                          <TableCell>Match</TableCell>
                          <TableCell>Primário</TableCell>
                          <TableCell>Verificado</TableCell>
                          <TableCell>Ativo</TableCell>
                          <TableCell align="right">Ações</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(domainsQuery.data?.items || []).map((row) => (
                          <TableRow key={row.id} hover>
                            <TableCell>{row.domain}</TableCell>
                            <TableCell>{row.match_mode || "exact"}</TableCell>
                            <TableCell>{row.is_primary ? "Sim" : "Não"}</TableCell>
                            <TableCell>{row.is_verified ? "Sim" : "Não"}</TableCell>
                            <TableCell>{row.is_active === false ? "Não" : "Sim"}</TableCell>
                            <TableCell align="right">
                              <Button
                                color="error"
                                startIcon={<DeleteIcon />}
                                onClick={() => deleteDomainMutation.mutate(row.id)}
                                disabled={deleteDomainMutation.isPending}
                              >
                                Remover
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        {(domainsQuery.data?.items || []).length === 0 && (
                          <TableRow>
                            <TableCell colSpan={6}>
                              <Typography color="text.secondary" textAlign="center" sx={{ py: 3 }}>
                                Nenhum domínio cadastrado para este tenant.
                              </Typography>
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </Paper>

                  <Paper sx={{ p: 3, flex: 1 }}>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>
                      Histórico de billing
                    </Typography>
                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                      Mudanças financeiras e de status operacional aplicadas ao tenant.
                    </Typography>

                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Data</TableCell>
                          <TableCell>Evento</TableCell>
                          <TableCell>Transição</TableCell>
                          <TableCell>Responsável</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(billingEventsQuery.data?.items || []).map((row) => (
                          <TableRow key={row.id} hover>
                            <TableCell>
                              {row.created_at ? new Date(row.created_at).toLocaleString(lang) : "-"}
                            </TableCell>
                            <TableCell>{row.message || row.event_type}</TableCell>
                            <TableCell>
                              {(row.previous_status || "-")} {"->"} {(row.next_status || "-")}
                            </TableCell>
                            <TableCell>{row.actor_email || "-"}</TableCell>
                          </TableRow>
                        ))}
                        {(billingEventsQuery.data?.items || []).length === 0 && (
                          <TableRow>
                            <TableCell colSpan={4}>
                              <Typography color="text.secondary" textAlign="center" sx={{ py: 3 }}>
                                Ainda não há eventos de billing para este tenant.
                              </Typography>
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </Paper>
                </Stack>
              </Stack>
            )}
          </Stack>
        </Container>
      </Box>

      <Dialog open={tenantDialogOpen} onClose={() => setTenantDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{tenantForm.id ? "Editar tenant" : "Novo tenant"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Nome"
              value={tenantForm.name}
              onChange={(event) => setTenantForm((prev) => ({ ...prev, name: event.target.value }))}
              fullWidth
            />
            <TextField
              label="Slug"
              value={tenantForm.slug}
              onChange={(event) => setTenantForm((prev) => ({ ...prev, slug: event.target.value }))}
              fullWidth
            />
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                label="Tipo de escopo"
                value={tenantForm.scope_type}
                onChange={(event) => setTenantForm((prev) => ({ ...prev, scope_type: event.target.value }))}
                fullWidth
              />
              <TextField
                label="Valor do escopo"
                value={tenantForm.scope_value}
                onChange={(event) => setTenantForm((prev) => ({ ...prev, scope_value: event.target.value }))}
                fullWidth
              />
            </Stack>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                label="Contato financeiro"
                value={tenantForm.billing_contact_email}
                onChange={(event) => setTenantForm((prev) => ({ ...prev, billing_contact_email: event.target.value }))}
                fullWidth
              />
              <TextField
                select
                label="Plano"
                value={tenantForm.plan_slug}
                onChange={(event) => setTenantForm((prev) => ({ ...prev, plan_slug: event.target.value }))}
                fullWidth
              >
                <MenuItem value="free">Free</MenuItem>
                <MenuItem value="pro">Pro</MenuItem>
                <MenuItem value="enterprise">Enterprise</MenuItem>
              </TextField>
            </Stack>
            <FormControlLabel
              control={
                <Switch
                  checked={tenantForm.is_active}
                  onChange={(_, checked) => setTenantForm((prev) => ({ ...prev, is_active: checked }))}
                />
              }
              label="Tenant ativo"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTenantDialogOpen(false)}>{t("cancel")}</Button>
          <Button variant="contained" onClick={() => saveTenantMutation.mutate()} disabled={saveTenantMutation.isPending}>
            {t("save")}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={domainDialogOpen} onClose={() => setDomainDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Novo domínio do tenant</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Domínio"
              value={domainForm.domain}
              onChange={(event) => setDomainForm((prev) => ({ ...prev, domain: event.target.value }))}
              fullWidth
              helperText="Ex.: mineradora.com.br ou operacao.mineradora.com.br"
            />
            <TextField
              select
              label="Modo de correspondência"
              value={domainForm.match_mode}
              onChange={(event) => setDomainForm((prev) => ({ ...prev, match_mode: event.target.value }))}
              fullWidth
            >
              <MenuItem value="exact">exact</MenuItem>
              <MenuItem value="suffix">suffix</MenuItem>
            </TextField>
            <FormControlLabel
              control={
                <Switch
                  checked={domainForm.is_primary}
                  onChange={(_, checked) => setDomainForm((prev) => ({ ...prev, is_primary: checked }))}
                />
              }
              label="Domínio primário"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={domainForm.is_verified}
                  onChange={(_, checked) => setDomainForm((prev) => ({ ...prev, is_verified: checked }))}
                />
              }
              label="Domínio verificado"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDomainDialogOpen(false)}>{t("cancel")}</Button>
          <Button variant="contained" onClick={() => createDomainMutation.mutate()} disabled={createDomainMutation.isPending}>
            {t("save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
