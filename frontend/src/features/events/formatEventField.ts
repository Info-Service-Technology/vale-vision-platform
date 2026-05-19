export function formatEventText(value: unknown): string {
  if (value == null) {
    return "-";
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "-";
  }

  const text = String(value).trim();
  if (!text) {
    return "-";
  }

  if (
    (text.startsWith("[") && text.endsWith("]")) ||
    (text.startsWith("{") && text.endsWith("}"))
  ) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) {
        return parsed.length ? parsed.join(", ") : "-";
      }
      if (typeof parsed === "string") {
        return parsed || "-";
      }
    } catch {
      return text;
    }
  }

  return text;
}
