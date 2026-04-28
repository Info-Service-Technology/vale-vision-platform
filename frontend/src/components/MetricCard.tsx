import { Card, CardContent, Stack, Typography, Box } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  severity?: "default" | "success" | "warning" | "error";
}

function SeverityIcon({ severity }: { severity: Props["severity"] }) {
  if (severity === "success") {
    return <CheckCircleIcon color="success" fontSize="small" />;
  }

  if (severity === "warning") {
    return <WarningAmberIcon color="warning" fontSize="small" />;
  }

  if (severity === "error") {
    return <ErrorIcon color="error" fontSize="small" />;
  }

  return null;
}

export function MetricCard({
  title,
  value,
  subtitle,
  severity = "default",
}: Props) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="body1" color="text.secondary" fontWeight={700}>
              {title}
            </Typography>

            <Box sx={{ height: 24 }}>
              <SeverityIcon severity={severity} />
            </Box>
          </Stack>

          <Typography variant="h4">{value}</Typography>

          {subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}