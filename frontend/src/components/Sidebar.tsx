import {
  Box,
  Divider,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from "@mui/material";

import DashboardIcon from "@mui/icons-material/Dashboard";
import DeleteIcon from "@mui/icons-material/Delete";
import PersonIcon from "@mui/icons-material/Person";
import SettingsIcon from "@mui/icons-material/Settings";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import LogoutIcon from "@mui/icons-material/Logout";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import ReceiptIcon from "@mui/icons-material/Receipt";
import HistoryIcon from "@mui/icons-material/History";

import logo from "../assets/Logo_Sensx.png";

interface Props {
  role: string;
  onLogout: () => void;
}

export function Sidebar({ role, onLogout }: Props) {
  const isSuperAdmin = role === "super-admin";

  const tenantMenu = [
    { label: "Painel", icon: <DashboardIcon /> },
    { label: "Caçambas", icon: <DeleteIcon /> },
    { label: "Perfil", icon: <PersonIcon /> },
    { label: "Sistema", icon: <SettingsIcon /> },
    { label: "Ajuda", icon: <HelpOutlineIcon /> },
  ];

  const sensxAdminMenu = [
    { label: "Administração de usuários", icon: <AdminPanelSettingsIcon /> },
    { label: "Billing", icon: <ReceiptIcon /> },
    { label: "Auditoria", icon: <HistoryIcon /> },
  ];

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: 240,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: 240,
          boxSizing: "border-box",
          borderRight: "1px solid rgba(15,23,42,0.08)",
        },
      }}
    >
      <Box
        sx={{
          width: "100%",
          height: 96,
          px: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "visible",
          flexShrink: 0,
        }}
      >
        <Box
          component="img"
          src={logo}
          alt="SensX"
          sx={{
            width: "100%",
            height: "auto",
            objectFit: "contain",
            display: "block",
          }}
        />
      </Box>

      <Divider />

      <List>
        {tenantMenu.map((item) => (
          <ListItemButton key={item.label}>
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>

      {isSuperAdmin && (
        <>
          <Divider />

          <List>
            {sensxAdminMenu.map((item) => (
              <ListItemButton key={item.label}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>
        </>
      )}

      <Box sx={{ flexGrow: 1 }} />

      <Divider />

      <List>
        <ListItemButton onClick={onLogout}>
          <ListItemIcon>
            <LogoutIcon />
          </ListItemIcon>
          <ListItemText primary="Sair" />
        </ListItemButton>
      </List>
    </Drawer>
  );
}