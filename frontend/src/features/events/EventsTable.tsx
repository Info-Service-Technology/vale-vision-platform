import { Table, TableBody, TableCell, TableHead, TableRow, Button, Chip } from "@mui/material";
import ImageIcon from "@mui/icons-material/Image";

export function EventsTable({ rows, onOpenImage, t }: any) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>{t("local")}</TableCell>
          <TableCell>{t("status")}</TableCell>
          <TableCell>{t("volume")}</TableCell>
          <TableCell>{t("frame")}</TableCell>
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
              <Button startIcon={<ImageIcon />} onClick={() => onOpenImage(event)}>
                {t("viewImage")}
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}