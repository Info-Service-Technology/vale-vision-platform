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
import ApartmentIcon from "@mui/icons-material/Apartment";

import { useLocation, useNavigate } from "react-router-dom";
import logo from "../assets/Logo_Sensx.png";
import { useAuth } from "../context/AuthContext";
import { useLocale } from "../context/LocaleContext";

interface Props {
  role: string;
  onLogout: () => void;
}

export function Sidebar({ role, onLogout }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isSuperAdmin, canWriteTenantData } = useAuth();
  const { t } = useLocale();

  const isTenantAdmin = role === "admin-tenant";

  const tenantMenu = [
    { label: t("dashboard"), icon: <DashboardIcon />, path: "/dashboard" },
    { label: t("bins"), icon: <DeleteIcon />, path: "/cacambas" },
    { label: t("billing"), icon: <ReceiptIcon />, path: "/billing" },
    { label: t("profile"), icon: <PersonIcon />, path: "/perfil" },
    { label: t("system"), icon: <SettingsIcon />, path: "/sistema" },
    { label: t("help"), icon: <HelpOutlineIcon />, path: "/ajuda" },
  ];

  const adminMenu = [
    {
      label: t("users_management"),
      icon: <AdminPanelSettingsIcon />,
      path: "/admin/users",
      disabled: !isSuperAdmin && !canWriteTenantData,
    },
  ];

  const superAdminMenu = [
    { label: t("tenants"), icon: <ApartmentIcon />, path: "/admin/tenants" },
    { label: t("audit"), icon: <HistoryIcon />, path: "/admin/audit" },
  ];

  function renderItem(item: { label: string; icon: React.ReactNode; path: string; disabled?: boolean }) {
    const selected = location.pathname === item.path;

    return (
      <ListItemButton
        key={item.label}
        selected={selected}
        onClick={() => {
          if (!item.disabled) navigate(item.path);
        }}
        disabled={item.disabled}
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
          src={(() => {
            try {
              const tenant = JSON.parse(localStorage.getItem("vale_tenant") || "{}");
              return tenant.company_logo_url || logo;
            } catch {
              return logo;
            }
          })()}
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

      {(isSuperAdmin || isTenantAdmin) && (
        <>
          <Divider />
          <List sx={{ py: 2 }}>
            {adminMenu.map(renderItem)}
            {isSuperAdmin && superAdminMenu.map(renderItem)}
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
          <ListItemText primary={t("logout")} />
        </ListItemButton>
      </List>
    </Drawer>
  );
}
