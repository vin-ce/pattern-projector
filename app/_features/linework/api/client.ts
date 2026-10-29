import type { components } from "./schema";

export type PatternDocument = components["schemas"]["PatternDocument"];
export type PatternAnalysis = components["schemas"]["PatternAnalysis"];
export type AnalysisRequest = components["schemas"]["AnalysisRequest"];
export type AllowanceSettings = components["schemas"]["AllowanceSettings"];
export type ExportRequest = components["schemas"]["ExportRequest"];
export type Piece = components["schemas"]["Piece"];
export type SavedWorkspace = components["schemas"]["SavedWorkspace"];
export type SessionState = components["schemas"]["SessionState"];

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/linework${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : "The request could not be completed. Check the local engine.",
    );
  }
  return response.json() as Promise<T>;
}

export const jsonRequest = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export async function exportPattern(
  id: string,
  request: ExportRequest,
): Promise<Blob> {
  const response = await fetch(
    `/api/linework/documents/${id}/export`,
    jsonRequest(request),
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || "Export failed.");
  }
  return response.blob();
}
