import { Alert, Avatar, Box, Button, Container, Paper, Stack, TextField, Typography } from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import UploadIcon from "@mui/icons-material/Upload";
import { ChangeEvent, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { BillingStatusBanner } from "../components/BillingStatusBanner";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../hooks/useLocale";
import { resolveAssetUrl, validateImageFile } from "../utils/branding";
import { updateMyProfile, uploadMyAvatar } from "../services/api";

type ProfileForm = {
  display_name: string;
  avatar_url: string;
  phone: string;
  about: string;
};

export function ProfilePage() {
  const { user, logout, refreshMe } = useAuth();
  const { t, lang, setLang } = useLocale();
  const [form, setForm] = useState<ProfileForm>({
    display_name: "",
    avatar_url: "",
    phone: "",
    about: "",
  });
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setForm({
      display_name: user?.name || "",
      avatar_url: resolveAssetUrl(user?.avatar_url),
      phone: user?.phone || "",
      about: user?.about || "",
    });
  }, [user?.about, user?.avatar_url, user?.name, user?.phone]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      await updateMyProfile({
        name: form.display_name,
        phone: form.phone,
        about: form.about,
        avatar_url: form.avatar_url,
      });
      await refreshMe();
    },
    onSuccess: () => {
      setSuccess(t("profile_saved_backend"));
      setError("");
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || t("save_failed"));
    },
  });

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      validateImageFile(file);
      const response = await uploadMyAvatar(file);
      setForm((prev) => ({ ...prev, avatar_url: resolveAssetUrl(response.avatar_url) }));
      await refreshMe();
      setSuccess(t("profile_avatar_saved_backend"));
      setError("");
    } catch (err: any) {
      setError(err?.response?.data?.detail || t("image_max_size_error"));
    }
  }

  function handleSave() {
    saveMutation.mutate();
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
          userName={form.display_name || user?.name || user?.email || "Usuário"}
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
                {t("profile")}
              </Typography>
              <Typography color="text.secondary">
                {t("profile_manage_preferences")}
              </Typography>
            </Box>

            {error && <Alert severity="error">{error}</Alert>}
            {success && <Alert severity="success">{success}</Alert>}

            <Paper sx={{ p: 3 }}>
              <Stack spacing={3}>
                <Stack direction={{ xs: "column", md: "row" }} spacing={3} alignItems={{ xs: "flex-start", md: "center" }}>
                  <Avatar
                    src={form.avatar_url || undefined}
                    sx={{ width: 96, height: 96 }}
                  >
                    {(form.display_name || user?.name || "U").charAt(0).toUpperCase()}
                  </Avatar>

                  <Stack spacing={1}>
                    <Button variant="outlined" component="label" startIcon={<UploadIcon />}>
                      {t("upload_avatar")}
                      <input hidden type="file" accept="image/*" onChange={handleAvatarChange} />
                    </Button>
                    <Typography variant="caption" color="text.secondary">
                      {t("image_max_size_help")}
                    </Typography>
                  </Stack>
                </Stack>

                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField
                    label={t("first_name")}
                    value={form.display_name}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, display_name: event.target.value }))
                    }
                    fullWidth
                  />

                  <TextField
                    label={t("email")}
                    value={user?.email || ""}
                    fullWidth
                    disabled
                  />
                </Stack>

                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <TextField
                    label={t("role")}
                    value={user?.role || ""}
                    fullWidth
                    disabled
                  />

                  <TextField
                    label={t("phone")}
                    value={form.phone}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, phone: event.target.value }))
                    }
                    fullWidth
                  />
                </Stack>

                <TextField
                  label={t("about")}
                  value={form.about}
                  onChange={(event) =>
                    setForm((prev) => ({ ...prev, about: event.target.value }))
                  }
                  fullWidth
                  multiline
                  minRows={4}
                />

                <Box>
                  <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSave}>
                    {saveMutation.isPending ? t("loading") : t("save")}
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
