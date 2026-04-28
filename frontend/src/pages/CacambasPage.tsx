import { useState } from "react";
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
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ImageIcon from "@mui/icons-material/Image";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import { useLocale } from "../context/LocaleContext";
import { fetchEvents, fetchImageUrl, fetchMetrics, resolveEvent } from "../services/api";
import { VisionEvent } from "../types/events";

function getUser() {
  try {
    return JSON.parse(localStorage.getItem("vale_user") || "{}");
  } catch {
    return {};
  }
}

export function CacambasPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t, lang, setLang } = useLocale();

  const user = getUser();

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [container, setContainer] = useState("all");
  const [search, setSearch] = useState("");

  const [selectedEvent, setSelectedEvent] = useState<VisionEvent | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetchMetrics(),
    retry: false,
  });

  const eventsQuery = useQuery({
    queryKey: ["cacambas", page, pageSize, container, search],
    queryFn: () =>
      fetchEvents({
        page: page + 1,
        page_size: pageSize,
        container: container === "all" ? undefined : container,
        search,
        activeOnly: true,
      }),
    retry: false,
  });

  function logout() {
    localStorage.removeItem("vale_token");
    localStorage.removeItem("vale_user");
    navigate("/login");
  }

  async function openDetails(event: VisionEvent) {
    setSelectedEvent(event);
    setImageUrl(null);
    setImageLoading(true);

    try {
      const url = await fetchImageUrl(event.id);
      setImageUrl(url);
    } finally {
      setImageLoading(false);
    }
  }

  async function handleResolve() {
    if (!selectedEvent) return;

    await resolveEvent(selectedEvent.id, "Resolvido manualmente pela operação");

    setSelectedEvent(null);
    setImageUrl(null);

    queryClient.invalidateQueries({ queryKey: ["cacambas"] });
    queryClient.invalidateQueries({ queryKey: ["metrics"] });
  }

  const rows = eventsQuery.data?.items || [];
  const total = eventsQuery.data?.total || 0;

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar role={user.role} onLogout={logout} />

      <Box
        sx={{
          flexGrow: 1,
          minHeight: "100vh",
          backgroundColor: "background.default",
          pt: "72px",
        }}
      >
        <Header
          userName={user.name || user.email || "Usuário"}
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
                Caçambas
              </Typography>
              <Typography color="text.secondary">
                Eventos ativos de contaminação, ocupação e imagens associadas.
              </Typography>
            </Box>

            <Paper sx={{ p: 2 }}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
                <TextField
                  label="Buscar"
                  size="small"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(0);
                  }}
                  sx={{ minWidth: 280 }}
                />

                <Select
                  size="small"
                  value={container}
                  onChange={(event) => {
                    setContainer(event.target.value);
                    setPage(0);
                  }}
                  sx={{ minWidth: 180 }}
                >
                  <MenuItem value="all">Todas</MenuItem>
                  <MenuItem value="plastico">Plástico</MenuItem>
                  <MenuItem value="madeira">Madeira</MenuItem>
                  <MenuItem value="sucata">Sucata</MenuItem>
                </Select>
              </Stack>

              {eventsQuery.isError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  Não foi possível carregar os eventos.
                </Alert>
              )}

              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Data</TableCell>
                    <TableCell>Hora</TableCell>
                    <TableCell>Caçamba</TableCell>
                    <TableCell>Material esperado</TableCell>
                    <TableCell>Detectado</TableCell>
                    <TableCell>Contaminante</TableCell>
                    <TableCell>Ocupação</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Ações</TableCell>
                  </TableRow>
                </TableHead>

                <TableBody>
                  {rows.map((event) => {
                    const contaminated = Boolean(event.alerta_contaminacao);
                    const fill = event.fill_percent ?? 0;

                    return (
                      <TableRow key={event.id} hover>
                        <TableCell>{event.data_ref || "-"}</TableCell>
                        <TableCell>{event.hora_ref || "-"}</TableCell>
                        <TableCell>{event.cacamba_esperada || "-"}</TableCell>
                        <TableCell>{event.material_esperado || "-"}</TableCell>
                        <TableCell>{event.materiais_detectados || "-"}</TableCell>
                        <TableCell>{event.contaminantes_detectados || "-"}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            color={fill >= 75 ? "warning" : "default"}
                            label={`${fill.toFixed(1)}%`}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            color={contaminated ? "error" : "success"}
                            label={contaminated ? "Contaminada" : "OK"}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<ImageIcon />}
                            onClick={() => openDetails(event)}
                          >
                            Ver imagem
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>

              <TablePagination
                component="div"
                count={total}
                page={page}
                rowsPerPage={pageSize}
                onPageChange={(_, next) => setPage(next)}
                onRowsPerPageChange={(event) => {
                  setPageSize(Number(event.target.value));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 25, 50, 100]}
              />
            </Paper>
          </Stack>
        </Container>
      </Box>

      <Dialog
        open={Boolean(selectedEvent)}
        onClose={() => setSelectedEvent(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Detalhes do evento</DialogTitle>

        <DialogContent>
          {selectedEvent && (
            <Stack spacing={2}>
              <Typography fontWeight={800}>
                {selectedEvent.file_path || selectedEvent.s3_key_raw}
              </Typography>

              {imageLoading ? (
                <Typography>Carregando imagem...</Typography>
              ) : imageUrl ? (
                <Box
                  component="img"
                  src={imageUrl}
                  alt="Imagem do evento"
                  sx={{
                    width: "100%",
                    maxHeight: 420,
                    objectFit: "contain",
                    borderRadius: 2,
                    border: "1px solid rgba(15,23,42,0.12)",
                  }}
                />
              ) : (
                <Alert severity="warning">Imagem não disponível.</Alert>
              )}

              <Stack spacing={0.5}>
                <Typography>
                  <strong>Caçamba:</strong> {selectedEvent.cacamba_esperada || "-"}
                </Typography>
                <Typography>
                  <strong>Material esperado:</strong> {selectedEvent.material_esperado || "-"}
                </Typography>
                <Typography>
                  <strong>Material detectado:</strong> {selectedEvent.materiais_detectados || "-"}
                </Typography>
                <Typography>
                  <strong>Contaminante:</strong> {selectedEvent.contaminantes_detectados || "-"}
                </Typography>
                <Typography>
                  <strong>Ocupação:</strong> {(selectedEvent.fill_percent ?? 0).toFixed(1)}%
                </Typography>
              </Stack>
            </Stack>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setSelectedEvent(null)}>Fechar</Button>

          {selectedEvent?.alerta_contaminacao && (
            <Button
              variant="contained"
              color="success"
              startIcon={<CheckCircleIcon />}
              onClick={handleResolve}
            >
              Resolver
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}