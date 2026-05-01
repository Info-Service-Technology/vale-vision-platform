export type BillingStatus =
  | "active"
  | "past_due"
  | "grace_period"
  | "suspended_read_only"
  | "suspended_full"
  | "terminated";

export function normalizeBillingStatus(value?: string | null): BillingStatus {
  const normalized = String(value || "active").trim().toLowerCase();

  if (
    normalized === "past_due" ||
    normalized === "grace_period" ||
    normalized === "suspended_read_only" ||
    normalized === "suspended_full" ||
    normalized === "terminated"
  ) {
    return normalized;
  }

  return "active";
}

export function isBillingWarningStatus(status: BillingStatus) {
  return status === "past_due" || status === "grace_period";
}

export function isBillingRestrictedStatus(status: BillingStatus) {
  return (
    status === "suspended_read_only" ||
    status === "suspended_full" ||
    status === "terminated"
  );
}

export function canTenantWrite(status: BillingStatus) {
  return !isBillingRestrictedStatus(status);
}
