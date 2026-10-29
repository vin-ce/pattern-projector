import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  exportPattern,
  jsonRequest,
  type PatternDocument,
  type PatternAnalysis,
  type AllowanceSettings,
  type AnalysisRequest,
} from "../api/client";

const defaults: AllowanceSettings = {
  seam_mm: 9.525,
  muslin_mm: 25.4,
  hem_mm: 50.8,
  preserve_hem: true,
};

export function useLinework(source: File | null) {
  const generation = useRef(0);
  const [document, setDocument] = useState<PatternDocument | null>(null);
  const [analysis, setAnalysis] = useState<PatternAnalysis | null>(null);
  const [settings, setSettings] = useState(defaults);
  const [size, setSize] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [scale, setScale] = useState(1);
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [hiddenLayers, setHiddenLayers] = useState<string[]>([]);
  const [lines, setLines] = useState({
    original: true,
    sewing: true,
    muslin: true,
  });
  const [allowPartial, setAllowPartial] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [prepared, setPrepared] = useState<{
    source: File;
    file: File;
    key: string;
  } | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    generation.current++;
    setGenerating(false);
    setDocument(null);
    setAnalysis(null);
    setPrepared(null);
    setError("");
    setPage(1);
    setScale(1);
    setConfirmed([]);
    setExcluded([]);
    setAllowPartial(false);
    if (!source || !source.name.toLowerCase().endsWith(".pdf")) {
      setUploading(false);
      return;
    }
    const controller = new AbortController();
    setUploading(true);
    const form = new FormData();
    form.append("file", source);
    api<PatternDocument>("/documents", {
      method: "POST",
      body: form,
      signal: controller.signal,
    })
      .then((doc) => {
        if (controller.signal.aborted) return;
        setSettings({
          ...defaults,
          seam_mm: doc.source_allowance_mm ?? defaults.seam_mm,
          hem_mm: doc.source_hem_mm ?? defaults.hem_mm,
        });
        setSize(doc.sizes.includes("M") ? "M" : doc.sizes[0] ?? null);
        setHiddenLayers([
          ...new Set(
            doc.layers
              .filter(
                (l) =>
                  ["grid", "background"].includes(l.kind) ||
                  l.name.toLowerCase().includes("sizing chart"),
              )
              .map((l) => l.name),
          ),
        ]);
        setDocument(doc);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setUploading(false);
      });
    return () => controller.abort();
  }, [source, retry]);

  const request = useMemo<AnalysisRequest>(
    () => ({
      size,
      page,
      scale,
      settings,
      generate: true,
      confirmed_piece_ids: confirmed,
      excluded_piece_ids: excluded,
    }),
    [size, page, scale, settings, confirmed, excluded],
  );
  const key = JSON.stringify({
    id: document?.id,
    request,
    lines,
    hiddenLayers,
    allowPartial,
  });

  useEffect(() => {
    setAnalysis(null);
    if (!document) {
      setAnalyzing(false);
      return;
    }
    const controller = new AbortController();
    setAnalyzing(true);
    setError("");
    const timer = setTimeout(() => {
      api<PatternAnalysis>(`/documents/${document.id}/analysis`, {
        ...jsonRequest(request),
        signal: controller.signal,
      })
        .then((value) => {
          if (!controller.signal.aborted) setAnalysis(value);
        })
        .catch((error) => {
          if (!controller.signal.aborted) setError(error.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setAnalyzing(false);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [document, request]);

  async function generate() {
    if (!document || !source || generating) return;
    const attempt = ++generation.current;
    setGenerating(true);
    setError("");
    try {
      const blob = await exportPattern(document.id, {
        ...request,
        include_original: lines.original,
        include_sewing: lines.sewing,
        include_muslin: lines.muslin,
        monochrome: true,
        allow_partial: allowPartial,
        hidden_layer_names: hiddenLayers,
      });
      if (attempt !== generation.current) return;
      const file = new File(
        [blob],
        `${source.name.replace(/\.pdf$/i, "")} — ${size || "pattern"} linework.pdf`,
        { type: "application/pdf" },
      );
      setPrepared({ source, file, key });
    } catch (error) {
      if (attempt === generation.current)
        setError(
          error instanceof Error
            ? error.message
            : "Linework generation failed.",
        );
    } finally {
      if (attempt === generation.current) setGenerating(false);
    }
  }

  const restore = useCallback(() => {
    generation.current++;
    setGenerating(false);
    setPrepared(null);
  }, []);

  return {
    document,
    analysis,
    size,
    setSize,
    page,
    setPage,
    scale,
    setScale,
    settings,
    setSettings,
    confirmed,
    excluded,
    hiddenLayers,
    setHiddenLayers,
    lines,
    setLines,
    allowPartial,
    setAllowPartial,
    confirm: (id: string) =>
      setConfirmed((old) => (old.includes(id) ? old : [...old, id])),
    exclude: (id: string) =>
      setExcluded((old) =>
        old.includes(id) ? old.filter((x) => x !== id) : [...old, id],
      ),
    uploading,
    analyzing,
    generating,
    error,
    generate,
    retry: () => setRetry((old) => old + 1),
    projectionFile: prepared?.source === source ? prepared.file : null,
    pendingChanges: prepared?.source === source && prepared.key !== key,
    restore,
  };
}

export type LineworkController = ReturnType<typeof useLinework>;
