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

import { useLocation, useNavigate } from "react-router-dom";
import logo from "../assets/Logo_Sensx.png";

interface Props {
  role: string;
  onLogout: () => void;
}

export function Sidebar({ role, onLogout }: Props) {
  const navigate = useNavigate();
  const location = useLocation();

  const isSuperAdmin = role === "super-admin";

  const tenantMenu = [
    { label: "Painel", icon: <DashboardIcon />, path: "/dashboard" },
    { label: "Caçambas", icon: <DeleteIcon />, path: "/cacambas" },
    { label: "Perfil", icon: <PersonIcon />, path: "/perfil" },
    { label: "Sistema", icon: <SettingsIcon />, path: "/sistema" },
    { label: "Ajuda", icon: <HelpOutlineIcon />, path: "/ajuda" },
  ];

  const adminMenu = [
    { label: "Administração de usuários", icon: <AdminPanelSettingsIcon />, path: "/admin/users" },
    { label: "Billing", icon: <ReceiptIcon />, path: "/billing" },
    { label: "Auditoria", icon: <HistoryIcon />, path: "/audit" },
  ];

  function renderItem(item: { label: string; icon: React.ReactNode; path: string }) {
    const selected = location.pathname === item.path;

    return (
      <ListItemButton
        key={item.label}
        selected={selected}
        onClick={() => navigate(item.path)}
        sx={{
          mx: 1,
          mb: 0.5,
          borderRadius: 2,
          "&.Mui-selected": {
            backgroundColor: "primary.main",
            color: "primary.contrastText",
            "& .MuiListItemIcon-root": {
              color: "primary.contrastText",
            },
          },
        }}
      >
        <ListItemIcon>{item.icon}</ListItemIcon>
        <ListItemText primary={item.label} />
      </ListItemButton>
    );
  }

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
          height: 96,
          px: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
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
          }}
        />
      </Box>

      <Divider />

      <List sx={{ py: 2 }}>
        {tenantMenu.map(renderItem)}
      </List>

      {isSuperAdmin && (
        <>
          <Divider />
          <List sx={{ py: 2 }}>
            {adminMenu.map(renderItem)}
          </List>
        </>
      )}

      <Box sx={{ flexGrow: 1 }} />

      <Divider />

      <List sx={{ py: 1 }}>
        <ListItemButton onClick={onLogout} sx={{ mx: 1, borderRadius: 2 }}>
          <ListItemIcon>
            <LogoutIcon />
          </ListItemIcon>
          <ListItemText primary="Sair" />
        </ListItemButton>
      </List>
    </Drawer>
  );
}