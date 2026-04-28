import { Dialog, DialogContent, DialogTitle, IconButton, Stack, Typography, CircularProgress } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useLocale } from "../context/LocaleContext";
interface Props { open: boolean; title?: string; imageUrl?: string | null; loading?: boolean; onClose: () => void; }
export function ImageModal({ open, title, imageUrl, loading, onClose }: Props) {
  const { t } = useLocale();
  return <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth><DialogTitle><Stack direction="row" alignItems="center" justifyContent="space-between"><Typography variant="h6">{title || t("frame")}</Typography><IconButton onClick={onClose}><CloseIcon /></IconButton></Stack></DialogTitle><DialogContent dividers sx={{ minHeight: 420, display: "flex", alignItems: "center", justifyContent: "center" }}>{loading && <CircularProgress />}{!loading && imageUrl && <img src={imageUrl} alt={title || "frame"} style={{ width: "100%", maxHeight: "75vh", objectFit: "contain", borderRadius: 12 }} />}{!loading && !imageUrl && <Typography color="text.secondary">{t("noData")}</Typography>}</DialogContent></Dialog>;
}
