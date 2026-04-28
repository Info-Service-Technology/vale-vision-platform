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
import { useLocale } from "../context/LocaleContext";
import { Lang } from "../i18n/translations";
import { fetchCurrentTenant, login } from "../services/api";
import { Link as RouterLink } from "react-router-dom";

type LoginProfile = "mineradora" | "sensx";

export function LoginPage() {
  const navigate = useNavigate();
  const { t, lang, setLang } = useLocale();

  const [tenant, setTenant] = useState<{
    id: number;
    name: string;
    slug: string;
  } | null>(null);

  const [loginProfile, setLoginProfile] = useState<LoginProfile>("mineradora");
  const [email, setEmail] = useState("admin@valevision.com");
  const [password, setPassword] = useState("123456");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCurrentTenant()
      .then(setTenant)
      .catch(() => setError("Não foi possível carregar o tenant da plataforma."));
  }, []);

  function handleProfileChange(
    _event: React.MouseEvent<HTMLElement>,
    value: LoginProfile | null
  ) {
    if (!value) return;

    setLoginProfile(value);

    if (value === "mineradora") {
      setEmail("admin@valevision.com");
    }

    if (value === "sensx") {
      setEmail("admin@sensx.com.br");
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    try {
      const res = await login(email, password);

      localStorage.setItem("vale_token", res.access_token);

      if (res.user) {
        localStorage.setItem(
          "vale_user",
          JSON.stringify({
            ...res.user,
            loginProfile,
          })
        );
      }

      navigate("/dashboard");
    } catch {
      setError("Falha no login. Verifique usuário e senha.");
    }
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        background: "linear-gradient(135deg,#F7FAFC 0%,#EAF3F2 100%)",
      }}
    >
      <Container maxWidth="sm">
        <Card sx={{ p: 2 }}>
          <CardContent>
            <Stack spacing={2.5} alignItems="center">
              <Box
                sx={{
                  width: "100%",
                  maxWidth: 300,
                  height: 90,
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
                    maxWidth: 280,
                    width: "100%",
                    height: "auto",
                    objectFit: "contain",
                  }}
                />
              </Box>

              <Stack spacing={0.5} textAlign="center">
                <Typography variant="h5">
                  {tenant?.name || "..."} {t("appTitle")}
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
                  Usuário Mineradora
                </ToggleButton>

                <ToggleButton value="sensx">
                  Usuário SensX
                </ToggleButton>
              </ToggleButtonGroup>

              <FormControl
                size="small"
                sx={{
                  alignSelf: "flex-end",
                  width: 150,
                }}
              >
                <InputLabel>Idioma</InputLabel>

                <Select
                  label="Idioma"
                  value={lang}
                  onChange={(event) => setLang(event.target.value as Lang)}
                >
                  <MenuItem value="pt-BR">pt-BR</MenuItem>
                  <MenuItem value="en">en</MenuItem>
                  <MenuItem value="es">es</MenuItem>
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
                <Stack spacing={2}>
                  <TextField
                    label={t("email")}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    fullWidth
                  />

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
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                  >
                    <Link
                      component={RouterLink}
                      to="/register"
                      underline="none"
                    >
                      Registrar novo usuário
                    </Link>

                    <Link
                      component={RouterLink}
                      to="/forgot-password"
                      underline="none"
                    >
                      Recuperar senha
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