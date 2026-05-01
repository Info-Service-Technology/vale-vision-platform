import { Box, Container, Paper, Stack, Typography } from "@mui/material";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../hooks/useLocale";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>
        {title}
      </Typography>
      <Stack spacing={1.25}>{children}</Stack>
    </Paper>
  );
}

export function HelpPage() {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useLocale();

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
          systemOnline
          lang={lang}
          setLang={setLang}
          onLogout={logout}
          t={t}
        />

        <Container maxWidth="lg" sx={{ py: 3 }}>
          <Stack spacing={3}>
            <Box>
              <Typography variant="h5" fontWeight={800}>
                {t("help_center")}
              </Typography>
              <Typography color="text.secondary">
                {t("monitoring_help_subtitle")}
              </Typography>
            </Box>

            <Section title={t("monitoring_help_what_is_title")}>
              <Typography>{t("monitoring_help_what_is_p1")}</Typography>
              <Typography>{t("monitoring_help_what_is_p2")}</Typography>
            </Section>

            <Section title={t("monitoring_help_navigation_title")}>
              <Typography>{t("monitoring_help_navigation_p1")}</Typography>
              <Typography>{t("monitoring_help_navigation_item_dashboard")}</Typography>
              <Typography>{t("monitoring_help_navigation_item_monitoring")}</Typography>
              <Typography>{t("monitoring_help_navigation_item_audit")}</Typography>
              <Typography>{t("monitoring_help_navigation_item_admin")}</Typography>
            </Section>

            <Section title={t("monitoring_help_operational_title")}>
              <Typography>{t("monitoring_help_operational_p1")}</Typography>
              <Typography>{t("monitoring_help_operational_p2")}</Typography>
              <Typography>{t("monitoring_help_operational_p3")}</Typography>
            </Section>

            <Section title={t("monitoring_help_permissions_title")}>
              <Typography>{t("monitoring_help_permissions_p1")}</Typography>
              <Typography>{t("monitoring_help_permissions_p2")}</Typography>
              <Typography>{t("monitoring_help_permissions_p3")}</Typography>
            </Section>

            <Section title={t("monitoring_help_best_practices_title")}>
              <Typography>{t("monitoring_help_best_practices_1")}</Typography>
              <Typography>{t("monitoring_help_best_practices_2")}</Typography>
              <Typography>{t("monitoring_help_best_practices_3")}</Typography>
              <Typography>{t("monitoring_help_best_practices_4")}</Typography>
            </Section>
          </Stack>
        </Container>
      </Box>
    </Box>
  );
}
