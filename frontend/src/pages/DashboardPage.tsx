import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Paper,
  Stack,
  Tab,
  Tabs,
  TablePagination,
  TextField,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import { MetricsGrid } from "../components/MetricsGrid";
import { EventsTable } from "../features/events/EventsTable";
import { ImageModal } from "../components/ImageModal";
import { ResolveDialog } from "../components/ResolveDialog";
import { useLocale } from "../context/LocaleContext";
import {
  fetchEvents,
  fetchImageUrl,
  fetchMetrics,
  resolveEvent,
} from "../services/api";
import { VisionEvent } from "../types/events";

const containers = [
  {
    key: "all",
    labelKey: "all",
    filter: undefined,
  },
  {
    key: "plastico",
    labelKey: "plastic",
    filter: "plastico",
  },
  {
    key: "madeira",
    labelKey: "wood",
    filter: "madeira",
  },
  {
    key: "sucata",
    labelKey: "scrap",
    filter: "sucata",
  },
];

function getUserName() {
  try {
    const user = JSON.parse(localStorage.getItem("vale_user") || "{}");
    return user.name || user.email || "usuário";
  } catch {
    return "usuário";
  }
}

export function DashboardPage() {
  const { t, lang, setLang } = useLocale();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [tab, setTab] = useState("all");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");

  const [imageModal, setImageModal] = useState<{
    open: boolean;
    event?: VisionEvent | null;
    url?: string | null;
    loading?: boolean;
  }>({
    open: false,
  });

  const [resolveDialog, setResolveDialog] = useState<{
    open: boolean;
    event?: VisionEvent | null;
  }>({
    open: false,
  });

  const containerFilter = useMemo(() => {
    return containers.find((container) => container.key === tab)?.filter;
  }, [tab]);

  const metricsQuery = useQuery({
    queryKey: ["metrics", containerFilter],
    queryFn: () => fetchMetrics(containerFilter),
    retry: false,
  });

  const eventsQuery = useQuery({
    queryKey: ["events", page, pageSize, containerFilter, search],
    queryFn: () =>
      fetchEvents({
        page: page + 1,
        page_size: pageSize,
        container: containerFilter,
        search,
        activeOnly: true,
      }),
    retry: false,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      resolveEvent(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
    },
  });

  function logout() {
    localStorage.removeItem("vale_token");
    localStorage.removeItem("vale_user");
    navigate("/login");
  }

  async function openImage(event: VisionEvent) {
    setImageModal({
      open: true,
      event,
      loading: true,
    });

    try {
      const url = await fetchImageUrl(event.id);

      setImageModal({
        open: true,
        event,
        url,
        loading: false,
      });
    } catch {
      setImageModal({
        open: true,
        event,
        url: null,
        loading: false,
      });
    }
  }

  const metrics = metricsQuery.data;
  const rows = eventsQuery.data?.items || [];
  const total = eventsQuery.data?.total || 0;
  const systemOnline = metrics?.system_online ?? true;

  return (
  <Box sx={{ display: "flex" }}>
    
    {/* SIDEBAR */}
    <Sidebar
      role={JSON.parse(localStorage.getItem("vale_user") || "{}")?.role}
      onLogout={logout}
    />

    {/* CONTEÚDO PRINCIPAL */}
    <Box
      sx={{
        flexGrow: 1,
        minHeight: "100vh",
        backgroundColor: "background.default",
        pt: "72px",
      }}
    >
      
      <Header
        userName={getUserName()}
        systemOnline={systemOnline}
        lang={lang}
        setLang={setLang}
        onLogout={logout}
        t={t}
      />

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Stack spacing={3}>
          <MetricsGrid metrics={metrics} t={t} />

          {(metrics?.over_threshold ?? 0) > 0 && (
            <Alert severity="warning" icon={<WarningAmberIcon />}>
              <strong>{t("fillAlarm")}:</strong> {t("fillAlarmDesc")}
            </Alert>
          )}

          <Card>
            <CardContent>
              <Stack
                direction={{ xs: "column", md: "row" }}
                spacing={2}
                alignItems={{ xs: "stretch", md: "center" }}
              >
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="h5">{t("dashboard")}</Typography>
                  <Typography color="text.secondary">
                    {t("lastFrame")}: {metrics?.last_frame_at || "-"}
                  </Typography>
                </Box>

                <Button variant="outlined" color="warning">
                  {t("resetCount")}
                </Button>

                <Button
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircleIcon />}
                >
                  {t("releaseContaminant")}
                </Button>
              </Stack>
            </CardContent>
          </Card>

          <Paper sx={{ p: 2 }}>
            <Tabs
              value={tab}
              onChange={(_, value) => {
                setTab(value);
                setPage(0);
              }}
              variant="fullWidth"
              sx={{ mb: 2 }}
            >
              {containers.map((container) => (
                <Tab
                  key={container.key}
                  value={container.key}
                  label={t(container.labelKey)}
                />
              ))}
            </Tabs>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ mb: 2 }}
            >
              <TextField
                label={t("search")}
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(0);
                }}
                size="small"
                sx={{ minWidth: 280 }}
              />

              <Box sx={{ flexGrow: 1 }} />

              <Button variant="outlined">{t("export")}</Button>
            </Stack>

            <EventsTable rows={rows} onOpenImage={openImage} t={t} />

            <TablePagination
              component="div"
              count={total}
              page={page}
              onPageChange={(_, next) => setPage(next)}
              rowsPerPage={pageSize}
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
  </Box>
);
}