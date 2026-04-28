import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Link,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Link as RouterLink, useNavigate, useSearchParams } from "react-router-dom";
import logo from "../assets/Logo_Sensx.png";
import { api } from "../services/api";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const token = useMemo(() => searchParams.get("token") || "", [searchParams]);

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!token) {
      setError("Token de recuperação não informado.");
      return;
    }

    if (password !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    if (password.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    try {
      await api.post("/auth/reset-password", {
        token,
        password,
      });

      setSuccess("Senha alterada com sucesso.");

      setTimeout(() => navigate("/login"), 1200);
    } catch {
      setError("Não foi possível alterar a senha.");
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
        <Card>
          <CardContent>
            <Stack spacing={3} alignItems="center">
              <Box component="img" src={logo} alt="SensX" sx={{ maxWidth: 260 }} />

              <Stack spacing={0.5} textAlign="center">
                <Typography variant="h5">Redefinir senha</Typography>
                <Typography color="text.secondary">
                  Informe sua nova senha.
                </Typography>
              </Stack>

              {error && <Alert severity="error" sx={{ width: "100%" }}>{error}</Alert>}
              {success && <Alert severity="success" sx={{ width: "100%" }}>{success}</Alert>}

              <Box component="form" onSubmit={handleSubmit} sx={{ width: "100%" }}>
                <Stack spacing={2}>
                  <TextField
                    label="Nova senha"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    fullWidth
                    required
                  />

                  <TextField
                    label="Confirmar nova senha"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    fullWidth
                    required
                  />

                  <Button type="submit" variant="contained" size="large">
                    Alterar senha
                  </Button>
                </Stack>
              </Box>

              <Link component={RouterLink} to="/login" underline="none">
                Voltar para login
              </Link>
            </Stack>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}