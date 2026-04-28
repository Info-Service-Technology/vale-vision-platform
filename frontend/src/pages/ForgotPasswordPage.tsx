import { useState } from "react";
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
import { Link as RouterLink } from "react-router-dom";
import logo from "../assets/Logo_Sensx.png";
import { api } from "../services/api";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSuccess("");

    try {
      await api.post("/auth/forgot-password", { email });
      setSuccess("Se o e-mail existir, enviaremos instruções para recuperação.");
    } catch {
      setError("Não foi possível solicitar recuperação de senha.");
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
                <Typography variant="h5">Recuperar senha</Typography>
                <Typography color="text.secondary">
                  Informe seu e-mail para receber as instruções.
                </Typography>
              </Stack>

              {error && <Alert severity="error" sx={{ width: "100%" }}>{error}</Alert>}
              {success && <Alert severity="success" sx={{ width: "100%" }}>{success}</Alert>}

              <Box component="form" onSubmit={handleSubmit} sx={{ width: "100%" }}>
                <Stack spacing={2}>
                  <TextField
                    label="E-mail"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    fullWidth
                    required
                  />

                  <Button type="submit" variant="contained" size="large">
                    Enviar instruções
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