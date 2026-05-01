import { Lang } from "../i18n/translations";

export const PROFILE_STORAGE_KEY = "vale_profile_settings";
export const SYSTEM_STORAGE_KEY = "vale_system_settings";
export const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;

export type ProfileSettings = {
  display_name?: string;
  avatar_url?: string;
  phone?: string;
  about?: string;
  language?: Lang;
};

export type SystemSettings = {
  app_name: string;
  default_language: Lang;
  timezone: string;
  monitoring_label: string;
  enable_notifications: boolean;
  enable_audit_log: boolean;
  company_logo_url?: string;
};

export const defaultSystemSettings: SystemSettings = {
  app_name: "SensX Vision Platform",
  default_language: "pt-BR",
  timezone: "America/Sao_Paulo",
  monitoring_label: "monitoramento",
  enable_notifications: true,
  enable_audit_log: true,
  company_logo_url: "",
};

export function readProfileSettings(): ProfileSettings {
  const raw = localStorage.getItem(PROFILE_STORAGE_KEY);
  if (!raw) return {};

  try {
    return JSON.parse(raw) as ProfileSettings;
  } catch {
    return {};
  }
}

export function saveProfileSettings(settings: ProfileSettings) {
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(settings));
}

export function readSystemSettings(): SystemSettings {
  const raw = localStorage.getItem(SYSTEM_STORAGE_KEY);
  if (!raw) return defaultSystemSettings;

  try {
    return {
      ...defaultSystemSettings,
      ...(JSON.parse(raw) as Partial<SystemSettings>),
    };
  } catch {
    return defaultSystemSettings;
  }
}

export function saveSystemSettings(settings: SystemSettings) {
  localStorage.setItem(SYSTEM_STORAGE_KEY, JSON.stringify(settings));
}

export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("file_read_failed"));
    reader.readAsDataURL(file);
  });
}

export function validateImageFile(file: File) {
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    throw new Error("image_too_large");
  }
}
