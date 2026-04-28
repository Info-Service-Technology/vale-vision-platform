import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./app/App";
import { theme } from "./theme/theme";
import { LocaleProvider } from "./context/LocaleContext";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <LocaleProvider>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <BrowserRouter><App /></BrowserRouter>
        </ThemeProvider>
      </LocaleProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
