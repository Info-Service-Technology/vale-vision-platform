import { Grid } from "@mui/material";
import { MetricCard } from "./MetricCard";

export function MetricsGrid({ metrics, t }: any) {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={3}>
        <MetricCard title={t("totalEvents")} value={metrics?.total_events ?? 0} />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard title={t("okEvents")} value={metrics?.ok_events ?? 0} severity="success" />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard title={t("activeContaminations")} value={metrics?.active_contaminations ?? 0} severity="error" />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard
          title={t("avgFill")}
          value={`${(metrics?.avg_fill_percent ?? 0).toFixed(1)}%`}
          subtitle={`${t("over75")}: ${metrics?.over_threshold ?? 0}`}
          severity={(metrics?.over_threshold ?? 0) > 0 ? "warning" : "default"}
        />
      </Grid>
    </Grid>
  );
}