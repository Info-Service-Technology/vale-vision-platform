import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from "@mui/material";
import { useState } from "react";
import { useLocale } from "../context/LocaleContext";

interface Props {
  open: boolean;
  eventId?: number | null;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void> | void;
}

export function ResolveDialog({ open, eventId, onClose, onConfirm }: Props) {
  const { t } = useLocale(); const [reason, setReason] = useState(""); const [loading, setLoading] = useState(false);
  async function handleConfirm() { setLoading(true); try { await onConfirm(reason || "Contaminante removido fisicamente da caçamba"); setReason(""); onClose(); } finally { setLoading(false); } }
  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm"><DialogTitle>{t("confirmRelease")}</DialogTitle><DialogContent><Stack spacing={2} sx={{ mt: 1 }}><Typography color="text.secondary">Evento #{eventId}</Typography><TextField label={t("releaseReason")} value={reason} onChange={(e) => setReason(e.target.value)} multiline minRows={3} fullWidth /></Stack></DialogContent><DialogActions><Button onClick={onClose}>{t("cancel")}</Button><Button variant="contained" color="success" disabled={loading} onClick={handleConfirm}>{t("confirm")}</Button></DialogActions></Dialog>;
}
