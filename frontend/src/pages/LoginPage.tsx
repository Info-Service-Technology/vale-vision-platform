import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  FormControl,
  InputLabel,
  Link,
  MenuItem,
  Select,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import logo from "../assets/Logo_Sensx.png";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../hooks/useLocale";
import { Lang, supportedLanguages } from "../i18n/translations";
import { fetchTenantBySlug } from "../services/api";
import { Link as RouterLink } from "react-router-dom";

type LoginProfile = "mineradora" | "sensx";

export function LoginPage() {
  const navigate = useNavigate();
  const { t, lang, setLang } = useLocale();
  const { login } = useAuth();

  const [tenant, setTenant] = useState<{
    id: number;
    name: string;
    slug: string;
  } | null>(null);

  const [tenantSlug, setTenantSlug] = useState(
    () => localStorage.getItem("vale_tenant_slug") || ""
  );
  const [loginProfile, setLoginProfile] = useState<LoginProfile>("mineradora");
  const [email, setEmail] = useState("admin@valevision.com");
  const [password, setPassword] = useState("123456");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadTenant() {
      if (loginProfile !== "mineradora") {
        setTenant(null);
        setError("");
        return;
      }

      if (!tenantSlug.trim()) {
        setTenant(null);
        return;
      }

      try {
        const data = await fetchTenantBySlug(tenantSlug.trim());
        if (active) {
          setTenant(data);
          setError("");
        }
      } catch {
        if (active) {
          setTenant(null);
          setError("Mineradora não encontrada.");
        }
      }
    }

    loadTenant();

    return () => {
      active = false;
    };
  }, [tenantSlug, loginProfile]);

  function handleProfileChange(
    _event: React.MouseEvent<HTMLElement>,
    value: LoginProfile | null
  ) {
    if (!value) return;

    setLoginProfile(value);
    setError("");

    if (value === "mineradora") {
      setEmail("admin@valevision.com");
      return;
    }

    setTenant(null);
    setEmail("admin@sensx.com");
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    if (loginProfile === "mineradora" && !tenantSlug.trim()) {
      setError("Informe a mineradora para continuar.");
      return;
    }

    try {
      await login(
        email,
        password,
        loginProfile === "mineradora" ? tenantSlug.trim() : undefined
      );
      navigate("/dashboard");
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          "Falha no login. Verifique usuário, senha e perfil de acesso."
      );
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        py: 2,
        background: "linear-gradient(135deg,#F7FAFC 0%,#EAF3F2 100%)",
      }}
    >
      <Container maxWidth="sm">
        <Card sx={{ p: 1.5 }}>
          <CardContent sx={{ "&:last-child": { pb: 2 } }}>
            <Stack spacing={1.75} alignItems="center">
              <Box
                sx={{
                  width: "100%",
                  maxWidth: 260,
                  height: 72,
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  overflow: "visible",
                }}
              >
                <Box
                  component="img"
                  src={logo}
                  alt="SensX"
                  sx={{
                    maxWidth: 240,
                    width: "100%",
                    height: "auto",
                    objectFit: "contain",
                  }}
                />
              </Box>

              <Stack spacing={0.5} textAlign="center">
                <Typography variant="h5">
                  {tenant?.name || t("organization")} {t("appTitle")}
                </Typography>

                <Typography color="text.secondary">
                  {t("loginSubtitle")}
                </Typography>
              </Stack>

              <ToggleButtonGroup
                exclusive
                fullWidth
                value={loginProfile}
                onChange={handleProfileChange}
                size="small"
              >
                <ToggleButton value="mineradora">
                  {t("miningUser")}
                </ToggleButton>
                <ToggleButton value="sensx">
                  {t("sensxUser")}
                </ToggleButton>
              </ToggleButtonGroup>

              <FormControl
                size="small"
                sx={{
                  alignSelf: "flex-end",
                  width: 140,
                }}
              >
                <InputLabel>Idioma</InputLabel>

                <Select
                  label="Idioma"
                  value={lang}
                  onChange={(event) => setLang(event.target.value as Lang)}
                >
                  {supportedLanguages.map((language) => (
                    <MenuItem key={language} value={language}>
                      {language}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {error && (
                <Alert severity="error" sx={{ width: "100%" }}>
                  {error}
                </Alert>
              )}

              <Box
                component="form"
                onSubmit={handleSubmit}
                sx={{ width: "100%" }}
              >
                <Stack spacing={1.5}>
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                    <TextField
                      label={t("organizationSlug")}
                      value={tenantSlug}
                      onChange={(event) => setTenantSlug(event.target.value)}
                      fullWidth
                      required={loginProfile === "mineradora"}
                      disabled={loginProfile !== "mineradora"}
                      helperText={
                        loginProfile === "mineradora"
                          ? tenant?.slug
                            ? `${t("organization")}: ${tenant.name}`
                            : t("organizationSlugHelp")
                          : t("sensxLoginHelp")
                      }
                    />

                    <TextField
                      label={t("email")}
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      fullWidth
                    />
                  </Stack>

                  <TextField
                    label={t("password")}
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    fullWidth
                  />

                  <Button type="submit" variant="contained" size="large">
                    {t("login")}
                  </Button>

                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                    alignItems={{ xs: "flex-start", sm: "center" }}
                    spacing={1}
                  >
                    <Link
                      component={RouterLink}
                      to="/register"
                      underline="none"
                    >
                      {t("registerNewUser")}
                    </Link>

                    <Link
                      component={RouterLink}
                      to="/forgot-password"
                      underline="none"
                    >
                      {t("recoverPassword")}
                    </Link>
                  </Stack>
                </Stack>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
