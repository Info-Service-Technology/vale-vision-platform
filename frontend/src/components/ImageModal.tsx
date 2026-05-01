import { Alert, Box, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton, Stack, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useLocale } from "../hooks/useLocale";
import { VisionEvent } from "../types/events";

interface Props {
  open: boolean;
  event?: VisionEvent | null;
  imageUrl?: string | null;
  loading?: boolean;
  onClose: () => void;
}

export function ImageModal({
  open,
  event,
  imageUrl,
  loading = false,
  onClose,
}: Props) {
  const { t } = useLocale();
  const title = event?.id ? `${t("frame")} #${event.id}` : t("frame");

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">{title}</Typography>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Stack>
      </DialogTitle>

      <DialogContent
        sx={{
          overflow: "visible",
        }}
      >
        {event && (
          <Stack spacing={2}>
            <Typography fontWeight={800}>
              {event.file_path || event.s3_key_raw || title}
            </Typography>

            {loading ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress />
              </Box>
            ) : imageUrl ? (
              <Box
                component="img"
                src={imageUrl}
                alt={title}
                sx={{
                  width: "100%",
                  maxHeight: 300,
                  objectFit: "contain",
                  borderRadius: 2,
                  border: "1px solid rgba(15,23,42,0.12)",
                }}
              />
            ) : (
              <Alert severity="warning">Imagem não disponível.</Alert>
            )}

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                gap: 1,
              }}
            >
              <Typography>
                <strong>Caçamba:</strong> {event.cacamba_esperada || "-"}
              </Typography>
              <Typography>
                <strong>Material esperado:</strong> {event.material_esperado || "-"}
              </Typography>
              <Typography>
                <strong>Material detectado:</strong> {event.materiais_detectados || "-"}
              </Typography>
              <Typography>
                <strong>Contaminante:</strong> {event.contaminantes_detectados || "-"}
              </Typography>
              <Typography>
                <strong>Ocupação:</strong> {(event.fill_percent ?? 0).toFixed(1)}%
              </Typography>
            </Box>
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
}
