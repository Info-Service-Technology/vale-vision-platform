import { useState } from "react";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  ListItemIcon,
  Menu,
  MenuItem,
  Select,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";

import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import SettingsIcon from "@mui/icons-material/Settings";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import LogoutIcon from "@mui/icons-material/Logout";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";

import { Lang } from "../i18n/translations";

interface Props {
  userName: string;
  systemOnline: boolean;
  lang: string;
  setLang: (lang: Lang) => void;
  onLogout: () => void;
  t: (key: string) => string;
}

function getUserEmail() {
  try {
    const user = JSON.parse(localStorage.getItem("vale_user") || "{}");
    return user.email || "";
  } catch {
    return "";
  }
}

function getUserRole() {
  try {
    const user = JSON.parse(localStorage.getItem("vale_user") || "{}");
    return user.role || "";
  } catch {
    return "";
  }
}

export function Header({
  userName,
  systemOnline,
  lang,
  setLang,
  onLogout,
  t,
}: Props) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const open = Boolean(anchorEl);
  const userEmail = getUserEmail();
  const userRole = getUserRole();

  return (
    <AppBar
      position="fixed"
      color="inherit"
      elevation={0}
      sx={{
        top: 0,
        left: 240,
        width: "calc(100% - 240px)",
        zIndex: (theme) => theme.zIndex.drawer + 1,
        borderBottom: "1px solid rgba(15,23,42,0.08)",
        backgroundColor: "background.paper",
      }}
    >
      <Toolbar sx={{ gap: 2, minHeight: 72 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" fontWeight={800}>
            {t("appTitle")}
          </Typography>

          <Typography variant="body2" color="text.secondary">
            {t("welcome")}, {userName || "Usuário"}
          </Typography>
        </Box>

        <Chip
          color={systemOnline ? "success" : "error"}
          label={systemOnline ? t("systemOnline") : t("systemOffline")}
          sx={{ fontWeight: 700 }}
        />

        <Button startIcon={<CalendarTodayIcon />} variant="outlined">
          {t("updatedToday")}
        </Button>

        <FormControl size="small" sx={{ minWidth: 118 }}>
          <InputLabel>Idioma</InputLabel>
          <Select
            label="Idioma"
            value={lang}
            onChange={(event) => setLang(event.target.value as Lang)}
          >
            <MenuItem value="pt-BR">pt-BR</MenuItem>
            <MenuItem value="en">en</MenuItem>
            <MenuItem value="es">es</MenuItem>
          </Select>
        </FormControl>

        <Button
          color="inherit"
          onClick={(event) => setAnchorEl(event.currentTarget)}
          endIcon={<KeyboardArrowDownIcon />}
          sx={{
            textTransform: "none",
            minWidth: 0,
          }}
        >
          <Stack direction="row" spacing={1.2} alignItems="center">
            <Avatar sx={{ width: 34, height: 34 }}>
              {userName?.charAt(0)?.toUpperCase() || "U"}
            </Avatar>

            <Box sx={{ textAlign: "left", display: { xs: "none", md: "block" } }}>
              <Typography variant="body2" fontWeight={800} lineHeight={1.1}>
                {userName}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {userRole || "Usuário"}
              </Typography>
            </Box>
          </Stack>
        </Button>

        <Menu
          anchorEl={anchorEl}
          open={open}
          onClose={() => setAnchorEl(null)}
          anchorOrigin={{
            vertical: "bottom",
            horizontal: "right",
          }}
          transformOrigin={{
            vertical: "top",
            horizontal: "right",
          }}
          PaperProps={{
            sx: {
              width: 260,
              mt: 1,
            },
          }}
        >
          <Box sx={{ px: 2, py: 1.5 }}>
            <Typography variant="body2" fontWeight={800}>
              {userName}
            </Typography>

            <Typography variant="caption" color="text.secondary">
              {userEmail}
            </Typography>

            <Box sx={{ mt: 1 }}>
              <Chip size="small" label={userRole || "Usuário"} />
            </Box>
          </Box>

          <Divider />

          <MenuItem>
            <ListItemIcon>
              <AccountCircleIcon fontSize="small" />
            </ListItemIcon>
            Perfil
          </MenuItem>

          <MenuItem>
            <ListItemIcon>
              <ReceiptLongIcon fontSize="small" />
            </ListItemIcon>
            Billing
          </MenuItem>

          <MenuItem>
            <ListItemIcon>
              <SettingsIcon fontSize="small" />
            </ListItemIcon>
            Sistema
          </MenuItem>

          <Divider />

          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              onLogout();
            }}
            sx={{ color: "error.main" }}
          >
            <ListItemIcon>
              <LogoutIcon fontSize="small" color="error" />
            </ListItemIcon>
            Sair
          </MenuItem>
        </Menu>

        <IconButton onClick={onLogout} sx={{ display: { xs: "inline-flex", md: "none" } }}>
          <LogoutIcon />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
}