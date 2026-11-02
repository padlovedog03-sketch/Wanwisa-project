/**
 * Validates that a string is a well-formed HTTP/HTTPS URL.
 * Rejects javascript:, data:, file:, and other unsafe protocols to prevent XSS.
 */
export function isValidHttpUrl(candidate: string): boolean {
  if (!candidate || typeof candidate !== 'string') return false;
  const trimmed = candidate.trim();
  if (!trimmed) return false;
  try {
    const parsed = new URL(trimmed);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Calculates completion percentage across an object of string or number fields.
 */
export function calculateFieldsProgress(fields: Record<string, string | number | undefined | null>): number {
  const entries = Object.values(fields);
  if (entries.length === 0) return 0;
  const filled = entries.filter((val) => {
    if (val === null || val === undefined) return false;
    if (typeof val === 'number') return val > 0;
    return val.toString().trim().length > 0;
  }).length;
  return Math.round((filled / entries.length) * 100);
}

