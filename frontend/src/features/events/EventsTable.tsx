import { Table, TableBody, TableCell, TableHead, TableRow, Button, Chip, Stack } from "@mui/material";
import ImageIcon from "@mui/icons-material/Image";
import { RemoveRedEye } from "@mui/icons-material";

export function EventsTable({ rows, onOpenImage, onResolve, t }: any) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>{t("local")}</TableCell>
          <TableCell>{t("status")}</TableCell>
          <TableCell>{t("volume")}</TableCell>
          <TableCell>{t("frame")}</TableCell>
          <TableCell align="right">{t("actions")}</TableCell>
        </TableRow>
      </TableHead>

      <TableBody>
        {rows.map((event: any) => (
          <TableRow key={event.id}>
            <TableCell>{event.cacamba_esperada}</TableCell>

            <TableCell>
              <Chip label={event.status} />
            </TableCell>

            <TableCell>
              {event.fill_percent?.toFixed(1)}%
            </TableCell>

            <TableCell>
              <Stack direction="row" spacing={1} justifyContent="flex-end">
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<ImageIcon />}
                  onClick={() => onOpenImage(event)}
                >
                  <RemoveRedEye fontSize="small" color="secondary" />
                </Button>
                {onResolve && Boolean(event.alerta_contaminacao) && (
                  <Button
                    size="small"
                    variant="contained"
                    color="success"
                    onClick={() => onResolve(event)}
                  >
                    {t("resolve")}
                  </Button>
                )}
              </Stack>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
