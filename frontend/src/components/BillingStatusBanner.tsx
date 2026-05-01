import { Alert } from "@mui/material";
import { useAuth } from "../context/AuthContext";

export function BillingStatusBanner() {
  const { isSuperAdmin, billingStatus, tenant } = useAuth();

  if (isSuperAdmin || !tenant) {
    return null;
  }

  const messageByStatus: Record<string, { severity: "info" | "warning" | "error"; text: string }> = {
    past_due: {
      severity: "warning",
      text: "Existe débito em aberto para este tenant. O acesso segue normal, mas a regularização financeira já deve ser tratada.",
    },
    grace_period: {
      severity: "warning",
      text: "Este tenant está em período de tolerância. A regularização deve acontecer antes de uma suspensão operacional.",
    },
    suspended_read_only: {
      severity: "error",
      text: "Este tenant está em modo leitura por billing. Acompanhamento continua disponível, mas ações de escrita e resolução manual estão bloqueadas.",
    },
    suspended_full: {
      severity: "error",
      text: "Este tenant está suspenso por billing. Recursos operacionais sensíveis estão bloqueados até a regularização financeira.",
    },
    terminated: {
      severity: "error",
      text: "Este tenant está encerrado. Qualquer retomada depende de validação contratual e financeira pela operação SensX.",
    },
  };

  const config = messageByStatus[billingStatus];
  if (!config) {
    return null;
  }

  return <Alert severity={config.severity}>{config.text}</Alert>;
}
