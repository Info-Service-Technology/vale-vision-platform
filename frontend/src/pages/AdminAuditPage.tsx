import { Box, CircularProgress, Container, Paper, Stack, Table, TableBody, TableCell, TableHead, TablePagination, TableRow, Typography } from "@mui/material";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { BillingStatusBanner } from "../components/BillingStatusBanner";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../hooks/useLocale";
import { fetchAdminAuditLogs, fetchMetrics } from "../services/api";

export function AdminAuditPage() {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useLocale();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  const metricsQuery = useQuery({
    queryKey: ["metrics"],
    queryFn: () => fetchMetrics(),
    retry: false,
  });

  const logsQuery = useQuery({
    queryKey: ["admin-audit", page, pageSize],
    queryFn: () => fetchAdminAuditLogs({ page: page + 1, page_size: pageSize }),
    retry: false,
  });

  const rows = logsQuery.data?.items || [];
  const total = logsQuery.data?.pagination.total || 0;

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
                {t("system_audit")}
              </Typography>
              <Typography color="text.secondary">
                {t("audit_log_subtitle")}
              </Typography>
            </Box>

            <Paper sx={{ p: 2 }}>
              {logsQuery.isLoading ? (
                <Stack alignItems="center" sx={{ py: 6 }}>
                  <CircularProgress />
                </Stack>
              ) : (
                <>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t("date")}</TableCell>
                        <TableCell>{t("user")}</TableCell>
                        <TableCell>{t("action")}</TableCell>
                        <TableCell>{t("method")}</TableCell>
                        <TableCell>{t("endpoint")}</TableCell>
                        <TableCell>{t("status")}</TableCell>
                        <TableCell>{t("tenant")}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {rows.map((row) => (
                        <TableRow key={row.id} hover>
                          <TableCell>
                            {row.created_at ? new Date(row.created_at).toLocaleString(lang) : "-"}
                          </TableCell>
                          <TableCell>{row.user_email || `ID ${row.user_id ?? "-"}`}</TableCell>
                          <TableCell>{row.action}</TableCell>
                          <TableCell>{row.method}</TableCell>
                          <TableCell>{row.endpoint}</TableCell>
                          <TableCell>{row.status}</TableCell>
                          <TableCell>{row.tenant || "-"}</TableCell>
                        </TableRow>
                      ))}
                      {rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={7}>
                            <Typography color="text.secondary" textAlign="center" sx={{ py: 3 }}>
                              {t("no_logs_found")}
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
                    onPageChange={(_, next) => setPage(next)}
                    rowsPerPage={pageSize}
                    onRowsPerPageChange={(event) => {
                      setPageSize(Number(event.target.value));
                      setPage(0);
                    }}
                    rowsPerPageOptions={[10, 20, 50, 100]}
                  />
                </>
              )}
            </Paper>
          </Stack>
        </Container>
      </Box>
    </Box>
  );
}
