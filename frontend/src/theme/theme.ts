import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1976d2' },
    secondary: { main: '#9c27b0' },
    background: {
      default: '#0f172a',
      paper: '#111827'
    }
  },
  shape: { borderRadius: 12 }
})
