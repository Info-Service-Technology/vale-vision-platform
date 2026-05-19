import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
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
import { RemoveRedEye } from "@mui/icons-material";
import { useQuery } from "@tanstack/react-query";

import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import { BillingStatusBanner } from "../components/BillingStatusBanner";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../hooks/useLocale";
import { fetchImageUrl, fetchMetrics, fetchResolvedEvents } from "../services/api";
import { VisionEvent } from "../types/events";
import { formatEventText } from "../features/events/formatEventField";

export function ResolvedItemsPage() {
  const { t, lang, setLang } = useLocale();
  const { user, logout } = useAuth();
  const [imageUrlCache, setImageUrlCache] = useState<Record<number, string>>({});
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<VisionEvent | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(false);

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetchMetrics(),
    retry: false,
  });

  const resolvedQuery = useQuery({
    queryKey: ["resolved-events", page, pageSize, search],
    queryFn: () =>
      fetchResolvedEvents({
        page: page + 1,
        page_size: pageSize,
        search,
      }),
    retry: false,
  });

  async function openDetails(event: VisionEvent) {
    setSelectedEvent(event);

    const cachedUrl = imageUrlCache[event.id];
    if (cachedUrl) {
      setImageUrl(cachedUrl);
      return;
    }

    setImageUrl(null);
    setImageLoading(true);

    try {
      const url = await fetchImageUrl(event.id);
      setImageUrl(url);
      setImageUrlCache((prev) => ({ ...prev, [event.id]: url }));
    } catch {
      setImageUrl(null);
    } finally {
      setImageLoading(false);
    }
  }

  const rows = resolvedQuery.data?.items || [];
  const total = resolvedQuery.data?.total || 0;

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
          userName={user?.name || user?.email || "Usuario"}
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
                Itens resolvidos
              </Typography>
              <Typography color="text.secondary">
                Eventos de contaminacao que ja foram tratados pela operacao.
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
                  sx={{ minWidth: 300 }}
                />

                <Box sx={{ flexGrow: 1 }} />

                <Chip
                  label={`${total} itens resolvidos`}
                  color="primary"
                  variant="outlined"
                />
              </Stack>

              {resolvedQuery.isError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  Nao foi possivel carregar os itens resolvidos.
                </Alert>
              )}

              {resolvedQuery.isLoading ? (
                <Stack alignItems="center" sx={{ py: 6 }}>
                  <CircularProgress />
                </Stack>
              ) : (
                <>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Data</TableCell>
                        <TableCell>Hora</TableCell>
                        <TableCell>Cacamba</TableCell>
                        <TableCell>Esperado</TableCell>
                        <TableCell>Detectado</TableCell>
                        <TableCell>Contaminante</TableCell>
                        <TableCell>Ocupacao</TableCell>
                        <TableCell>Resolvido em</TableCell>
                        <TableCell>Motivo</TableCell>
                        <TableCell align="right">Acoes</TableCell>
                      </TableRow>
                    </TableHead>

                    <TableBody>
                      {rows.map((event) => (
                        <TableRow key={event.id} hover>
                          <TableCell>{event.data_ref || "-"}</TableCell>
                          <TableCell>{event.hora_ref || "-"}</TableCell>
                          <TableCell>{event.cacamba_esperada || "-"}</TableCell>
                          <TableCell>{event.material_esperado || "-"}</TableCell>
                          <TableCell>{formatEventText(event.materiais_detectados)}</TableCell>
                          <TableCell>{formatEventText(event.contaminantes_detectados)}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              color={(event.fill_percent ?? 0) >= 75 ? "warning" : "default"}
                              label={`${(event.fill_percent ?? 0).toFixed(1)}%`}
                            />
                          </TableCell>
                          <TableCell>
                            {event.resolved_at
                              ? new Date(event.resolved_at).toLocaleString("pt-BR")
                              : "-"}
                          </TableCell>
                          <TableCell sx={{ maxWidth: 260 }}>
                            <Typography variant="body2" noWrap title={event.resolved_reason || ""}>
                              {event.resolved_reason || "-"}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<ImageIcon />}
                              onClick={() => openDetails(event)}
                            >
                              <RemoveRedEye fontSize="small" color="secondary" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}

                      {rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={10}>
                            <Typography color="text.secondary" textAlign="center" sx={{ py: 3 }}>
                              Nenhum item resolvido encontrado.
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
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
                </>
              )}
            </Paper>
          </Stack>
        </Container>
      </Box>

      <Dialog open={!!selectedEvent} onClose={() => setSelectedEvent(null)} maxWidth="md" fullWidth>
        <DialogTitle>Detalhes do item resolvido</DialogTitle>
        <DialogContent sx={{ overflow: "visible" }}>
          {selectedEvent && (
            <Stack spacing={2}>
              <Typography fontWeight={800}>
                {selectedEvent.file_path || selectedEvent.s3_key_raw}
              </Typography>

              {imageLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress />
                </Box>
              ) : imageUrl ? (
                <Box
                  component="img"
                  src={imageUrl}
                  alt="Imagem do evento"
                  sx={{
                    width: "100%",
                    maxHeight: 300,
                    objectFit: "contain",
                    borderRadius: 2,
                    border: "1px solid rgba(15,23,42,0.12)",
                  }}
                />
              ) : (
                <Alert severity="warning">Imagem nao disponivel.</Alert>
              )}

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                  gap: 1,
                }}
              >
                <Typography>
                  <strong>Cacamba:</strong> {selectedEvent.cacamba_esperada || "-"}
                </Typography>
                <Typography>
                  <strong>Material esperado:</strong> {selectedEvent.material_esperado || "-"}
                </Typography>
                <Typography>
                  <strong>Material detectado:</strong> {formatEventText(selectedEvent.materiais_detectados)}
                </Typography>
                <Typography>
                  <strong>Contaminante:</strong> {formatEventText(selectedEvent.contaminantes_detectados)}
                </Typography>
                <Typography>
                  <strong>Ocupacao:</strong> {(selectedEvent.fill_percent ?? 0).toFixed(1)}%
                </Typography>
                <Typography>
                  <strong>Resolvido em:</strong>{" "}
                  {selectedEvent.resolved_at
                    ? new Date(selectedEvent.resolved_at).toLocaleString("pt-BR")
                    : "-"}
                </Typography>
              </Box>

              <Typography>
                <strong>Motivo:</strong> {selectedEvent.resolved_reason || "-"}
              </Typography>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedEvent(null)}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
