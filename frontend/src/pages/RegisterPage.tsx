import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Stack,
  TextField,
  Typography,
  Link,
} from "@mui/material";
import { useNavigate, Link as RouterLink } from "react-router-dom";
import logo from "../assets/Logo_Sensx.png";
import { api } from "../services/api";

export function RegisterPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (password !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    try {
      await api.post("/auth/register", {
        name,
        email,
        password,
      });

      setSuccess("Usuário criado com sucesso!");

      setTimeout(() => navigate("/login"), 1200);
    } catch (err: any) {
      setError(err?.response?.data?.error || "Erro ao registrar usuário.");
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

              {/* LOGO */}
              <Box
                component="img"
                src={logo}
                alt="SensX"
                sx={{ maxWidth: 260 }}
              />

              <Typography variant="h5">
                Criar nova conta
              </Typography>

              {error && <Alert severity="error">{error}</Alert>}
              {success && <Alert severity="success">{success}</Alert>}

              <Box
                component="form"
                onSubmit={handleSubmit}
                sx={{ width: "100%" }}
              >
                <Stack spacing={2}>
                  <TextField
                    label="Nome"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    fullWidth
                  />

                  <TextField
                    label="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    fullWidth
                  />

                  <TextField
                    label="Senha"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    fullWidth
                  />

                  <TextField
                    label="Confirmar senha"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    fullWidth
                  />

                  <Button type="submit" variant="contained" size="large">
                    Registrar
                  </Button>
                </Stack>
              </Box>

              <Link component={RouterLink} to="/login" underline="none">
                Já tem conta? Fazer login
              </Link>

            </Stack>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}