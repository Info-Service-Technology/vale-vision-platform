import { createTheme } from "@mui/material/styles";
export const theme = createTheme({
  palette: { mode: "light", primary: { main: "#063B7A" }, secondary: { main: "#0B8F87" }, background: { default: "#F5F7FB", paper: "#FFFFFF" } },
  shape: { borderRadius: 14 },
  typography: { fontFamily: ["Inter", "Roboto", "Arial", "sans-serif"].join(","), h4: { fontWeight: 800 }, h5: { fontWeight: 800 }, h6: { fontWeight: 700 } },
  components: { MuiCard: { styleOverrides: { root: { boxShadow: "0 2px 10px rgba(15,23,42,0.08)", border: "1px solid rgba(15,23,42,0.08)" } } }, MuiButton: { styleOverrides: { root: { textTransform: "none", fontWeight: 700 } } } }
});
