import { useEffect, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Container,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import UploadIcon from "@mui/icons-material/Upload";
import { ChangeEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { BillingStatusBanner } from "../components/BillingStatusBanner";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../hooks/useLocale";
import { Lang, supportedLanguages } from "../i18n/translations";
import {
  readSystemSettings,
  saveSystemSettings,
  type SystemSettings,
  validateImageFile,
} from "../utils/branding";
import { uploadCurrentTenantLogo } from "../services/api";

export function SystemPage() {
  const { user, tenant, logout, isSuperAdmin, refreshMe } = useAuth();
  const { t, lang, setLang } = useLocale();
  const [config, setConfig] = useState<SystemSettings>(readSystemSettings());
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setConfig({
      ...readSystemSettings(),
      company_logo_url: tenant?.company_logo_url || readSystemSettings().company_logo_url,
    });
  }, [tenant?.company_logo_url]);

  function handleSave() {
    saveSystemSettings(config);
    setLang(config.default_language);
    setSuccess(t("system_settings_saved_local"));
    setError("");
  }

  const readOnly = !isSuperAdmin;

  const logoMutation = useMutation({
    mutationFn: async (file: File) => uploadCurrentTenantLogo(file),
    onSuccess: async (data) => {
      setConfig((prev) => ({ ...prev, company_logo_url: data.company_logo_url }));
      await refreshMe();
      setSuccess(t("system_logo_saved_backend"));
      setError("");
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || t("image_max_size_error"));
    },
  });

  async function handleLogoChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      validateImageFile(file);
      logoMutation.mutate(file);
    } catch (err: any) {
      setError(err?.response?.data?.detail || t("image_max_size_error"));
    }
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
          systemOnline
          lang={lang}
          setLang={setLang}
          onLogout={logout}
          t={t}
        />

        <Container maxWidth="lg" sx={{ py: 3 }}>
          <Stack spacing={3}>
            <BillingStatusBanner />

            <Box>
              <Typography variant="h5" fontWeight={800}>
                {t("system")}
              </Typography>
              <Typography color="text.secondary">
                {t("monitoring_system_subtitle")}
              </Typography>
            </Box>

            {readOnly && (
              <Alert severity="info">{t("system_settings_super_admin_only")}</Alert>
            )}

            {error && <Alert severity="error">{error}</Alert>}
            {success && <Alert severity="success">{success}</Alert>}

            <Paper sx={{ p: 3 }}>
              <Stack spacing={2}>
                <Stack direction={{ xs: "column", md: "row" }} spacing={3} alignItems={{ xs: "flex-start", md: "center" }}>
                  <Avatar
                    src={config.company_logo_url || undefined}
                    variant="rounded"
                    sx={{ width: 120, height: 120, bgcolor: "background.paper", border: "1px solid rgba(15,23,42,0.12)" }}
                  >
                    {config.app_name.charAt(0).toUpperCase()}
                  </Avatar>

                  <Stack spacing={1}>
                    <Button
                      variant="outlined"
                      component="label"
                      startIcon={<UploadIcon />}
                      disabled={readOnly}
                    >
                      {t("upload_company_logo")}
                      <input hidden type="file" accept="image/*" onChange={handleLogoChange} />
                    </Button>
                    <Typography variant="caption" color="text.secondary">
                      {t("image_max_size_help")}
                    </Typography>
                  </Stack>
                </Stack>

                <TextField
                  label={t("system_name")}
                  value={config.app_name}
                  onChange={(event) =>
                    setConfig((prev) => ({ ...prev, app_name: event.target.value }))
                  }
                  disabled={readOnly}
                  fullWidth
                />

                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField
                    select
                    label={t("default_language")}
                    value={config.default_language}
                    onChange={(event) =>
                      setConfig((prev) => ({
                        ...prev,
                        default_language: event.target.value as Lang,
                      }))
                    }
                    disabled={readOnly}
                    fullWidth
                  >
                    {supportedLanguages.map((language) => (
                      <MenuItem key={language} value={language}>
                        {language}
                      </MenuItem>
                    ))}
                  </TextField>

                  <TextField
                    label={t("timezone")}
                    value={config.timezone}
                    onChange={(event) =>
                      setConfig((prev) => ({ ...prev, timezone: event.target.value }))
                    }
                    disabled={readOnly}
                    fullWidth
                  />
                </Stack>

                <TextField
                  label={t("monitoring_label")}
                  value={config.monitoring_label}
                  onChange={(event) =>
                    setConfig((prev) => ({
                      ...prev,
                      monitoring_label: event.target.value,
                    }))
                  }
                  disabled={readOnly}
                  helperText={t("monitoring_label_help")}
                  fullWidth
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={config.enable_notifications}
                      onChange={(_, checked) =>
                        setConfig((prev) => ({
                          ...prev,
                          enable_notifications: checked,
                        }))
                      }
                      disabled={readOnly}
                    />
                  }
                  label={t("enable_system_notifications")}
                />

                <FormControlLabel
                  control={
                    <Switch
                      checked={config.enable_audit_log}
                      onChange={(_, checked) =>
                        setConfig((prev) => ({
                          ...prev,
                          enable_audit_log: checked,
                        }))
                      }
                      disabled={readOnly}
                    />
                  }
                  label={t("enable_admin_audit_log")}
                />

                <Box>
                  <Button
                    variant="contained"
                    startIcon={<SaveIcon />}
                    onClick={handleSave}
                    disabled={readOnly}
                  >
                    {t("save")}
                  </Button>
                </Box>
              </Stack>
            </Paper>
          </Stack>
        </Container>
      </Box>
    </Box>
  );
}
