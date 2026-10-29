export function parseInches(value: string): number | null {
  const normalized = value.trim();
  const match = /^(?:(\d+)\s+)?(\d+)\/(\d+)$/.exec(normalized);
  const inches = match
    ? Number(match[1] || 0) + Number(match[2]) / Number(match[3])
    : /^\d+(?:\.\d+)?$/.test(normalized)
      ? Number(normalized)
      : NaN;
  return Number.isFinite(inches) ? inches * 25.4 : null;
}

export function formatInches(mm: number): string {
  const eighths = Math.round((mm / 25.4) * 8);
  if (Math.abs(eighths / 8 - mm / 25.4) > 0.0001)
    return (mm / 25.4).toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  const whole = Math.floor(eighths / 8),
    remainder = eighths % 8;
  if (!remainder) return String(whole);
  const divisor = remainder % 4 === 0 ? 4 : remainder % 2 === 0 ? 2 : 1;
  return `${whole ? whole + " " : ""}${remainder / divisor}/${8 / divisor}`;
}
