import { useState } from "react";
import type { LineworkController } from "../hooks/use-linework";
import { formatInches, parseInches } from "../utils/measurements";

export function LineworkPanel({
  controller: c,
  patternScale,
  onClose,
}: {
  controller: LineworkController;
  patternScale: number;
  onClose: () => void;
}) {
  return (
    <aside
      className="linework-panel"
      aria-label="Sewing and muslin linework"
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="linework-heading">
        <h2>SEWING / MUSLIN</h2>
        <button type="button" aria-label="Close linework" onClick={onClose}>
          ×
        </button>
      </div>
      {c.uploading ? (
        <p role="status">Reading PDF layers and measurements…</p>
      ) : c.document ? (
        <LineworkForm key={c.document.id} c={c} patternScale={patternScale} />
      ) : (
        <p>
          Open a PDF with Pattern Projector’s Open File button to begin. SVGs
          still work in the original viewer.
        </p>
      )}
      {c.error && (
        <div className="linework-message" role="alert">
          <p>{c.error}</p>
          {!c.document && (
            <button type="button" onClick={c.retry}>
              Reconnect to local engine
            </button>
          )}
        </div>
      )}
    </aside>
  );
}

function LineworkForm({
  c,
  patternScale,
}: {
  c: LineworkController;
  patternScale: number;
}) {
  const doc = c.document!;
  const [seam, setSeam] = useState(formatInches(c.settings.seam_mm));
  const [muslin, setMuslin] = useState(formatInches(c.settings.muslin_mm));
  const [hem, setHem] = useState(formatInches(c.settings.hem_mm));
  const [pdfScale, setPdfScale] = useState(String(c.scale));
  const seamMm = parseInches(seam),
    muslinMm = parseInches(muslin),
    hemMm = parseInches(hem);
  const valid =
    seamMm !== null &&
    seamMm >= 0 &&
    seamMm <= 100 &&
    muslinMm !== null &&
    muslinMm > 0 &&
    muslinMm <= 150 &&
    hemMm !== null &&
    hemMm >= 0 &&
    hemMm <= 150 &&
    Number(pdfScale) > 0.05 &&
    Number(pdfScale) <= 20;
  const pieces =
    c.analysis?.pieces.filter((p) => p.status !== "excluded") ?? [];
  const incomplete =
    !!c.analysis && c.analysis.generated.length < pieces.length;
  const refs = doc.calibration;
  const generated = c.analysis?.generated.length ?? 0;
  const sameScale = Math.abs(patternScale - 1) < 1e-8;
  const shared = [
    ...new Set(doc.layers.filter((l) => l.kind !== "size").map((l) => l.name)),
  ];
  const update = (field: "seam_mm" | "muslin_mm" | "hem_mm", raw: string) => {
    const value = parseInches(raw);
    if (value !== null) c.setSettings((old) => ({ ...old, [field]: value }));
  };
  function download() {
    if (!c.projectionFile) return;
    const url = URL.createObjectURL(c.projectionFile);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = c.projectionFile.name;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  return (
    <>
      <p className="linework-filename">{doc.name}</p>
      {doc.pages.length > 1 && (
        <nav className="linework-pages" aria-label="Linework page review">
          <button
            aria-label="Previous review page"
            disabled={c.page <= 1}
            onClick={() => c.setPage(c.page - 1)}
          >
            ←
          </button>
          <span>
            {c.page} of {doc.pages.length} pages
          </span>
          <button
            aria-label="Next review page"
            disabled={c.page >= doc.pages.length}
            onClick={() => c.setPage(c.page + 1)}
          >
            →
          </button>
        </nav>
      )}
      <label className="linework-field">
        Size
        <select
          aria-label="Linework size"
          value={c.size ?? ""}
          onChange={(e) => c.setSize(e.target.value || null)}
        >
          {!doc.sizes.length && <option value="">All source content</option>}
          {doc.sizes.map((size) => (
            <option key={size}>{size}</option>
          ))}
        </select>
      </label>
      <p className="linework-help">
        Shared notches, grainlines, text, and control lines are retained.
      </p>
      <fieldset>
        <legend>ALLOWANCES / INCHES</legend>
        <label className="linework-field">
          Original seam
          <input
            aria-label="Original seam allowance in inches"
            value={seam}
            onChange={(e) => {
              setSeam(e.target.value);
              update("seam_mm", e.target.value);
            }}
            aria-invalid={seamMm === null}
          />
        </label>
        <label className="linework-field">
          Muslin from sewing
          <input
            aria-label="Muslin allowance in inches"
            value={muslin}
            onChange={(e) => {
              setMuslin(e.target.value);
              update("muslin_mm", e.target.value);
            }}
            aria-invalid={muslinMm === null}
          />
        </label>
        <label className="linework-check">
          <input
            type="checkbox"
            checked={c.settings.preserve_hem}
            onChange={(e) =>
              c.setSettings((old) => ({
                ...old,
                preserve_hem: e.target.checked,
              }))
            }
          />
          Preserve pattern hems
        </label>
        {c.settings.preserve_hem && (
          <label className="linework-field">
            Pattern hem
            <input
              aria-label="Pattern hem allowance in inches"
              value={hem}
              onChange={(e) => {
                setHem(e.target.value);
                update("hem_mm", e.target.value);
              }}
              aria-invalid={hemMm === null}
            />
          </label>
        )}
        <p className="linework-help">
          Sewing is inward from the original cut. Muslin is outward from sewing.{" "}
          {valid &&
            muslinMm! >= seamMm! &&
            `${formatInches(muslinMm! - seamMm!)}″ extra outside ordinary seams.`}
        </p>
        {doc.source_allowance_mm !== null && (
          <p className="linework-help">
            Pattern suggests {formatInches(doc.source_allowance_mm)}″ seams
            {doc.source_hem_mm !== null
              ? ` and ${formatInches(doc.source_hem_mm)}″ hems`
              : ""}
            .
          </p>
        )}
      </fieldset>
      <fieldset>
        <legend>LINEWORK</legend>
        {(["original", "sewing", "muslin"] as const).map((kind) => (
          <label className="linework-check" key={kind}>
            <input
              type="checkbox"
              checked={c.lines[kind]}
              onChange={(e) =>
                c.setLines((old) => ({ ...old, [kind]: e.target.checked }))
              }
            />
            <span className={`linework-sample ${kind}`} />
            {kind === "original"
              ? "Original cutting line"
              : kind === "sewing"
                ? "Sewing line"
                : "Muslin cutting line"}
          </label>
        ))}
      </fieldset>
      <details>
        <summary>PDF scale + shared markings</summary>
        <p className="linework-help">
          {refs.length
            ? refs.every((r) => r.verified)
              ? "PDF reference squares verified at native scale."
              : "PDF reference measurements need checking."
            : "No reference squares detected. Measure a known length before cutting."}
        </p>
        {refs.slice(0, 2).map((r, i) => (
          <p className="linework-help" key={i}>
            {r.label}: {r.width_mm.toFixed(2)} × {r.height_mm.toFixed(2)} mm
          </p>
        ))}
        <label className="linework-field">
          PDF correction
          <input
            aria-label="PDF scale correction"
            inputMode="decimal"
            value={pdfScale}
            onChange={(e) => {
              setPdfScale(e.target.value);
              const value = Number(e.target.value);
              if (value > 0.05 && value <= 20) c.setScale(value);
            }}
          />
        </label>
        <p className="linework-help">
          Correction = known length ÷ measured PDF length. Allowances remain in
          physical units. Projector calibration is separate.
        </p>
        {shared.map((name) => (
          <label key={name} className="linework-check">
            <input
              type="checkbox"
              checked={!c.hiddenLayers.includes(name)}
              onChange={(e) =>
                c.setHiddenLayers((old) =>
                  e.target.checked
                    ? old.filter((x) => x !== name)
                    : [...old, name],
                )
              }
            />
            {name}
          </label>
        ))}
      </details>
      <details className="linework-review">
        <summary>
          Review boundaries / {generated} of {pieces.length} ready
        </summary>
        <p className="linework-help">
          Review a proposed straight closure or fold against the source before
          confirming. Excluding a piece omits generated lines; its original
          markings remain.
        </p>
        {c.analysis?.pieces.map((piece) => (
          <div className="linework-piece" key={piece.id}>
            <svg
              viewBox={`${piece.bounds[0] - 10} ${piece.bounds[1] - 10} ${piece.bounds[2] - piece.bounds[0] + 20} ${piece.bounds[3] - piece.bounds[1] + 20}`}
              aria-label={`${piece.name} boundary`}
            >
              <path
                d={
                  piece.boundary
                    .map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`)
                    .join(" ") + " Z"
                }
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
                strokeDasharray={piece.status === "ready" ? undefined : "3 2"}
              />
            </svg>
            <strong>{piece.name}</strong>
            <span>{piece.status}</span>
            {piece.notices?.map((n, i) => (
              <p className="linework-help" key={i}>
                {n}
              </p>
            ))}
            {piece.status !== "ready" &&
              piece.status !== "excluded" &&
              piece.can_confirm && (
                <button onClick={() => c.confirm(piece.id)}>
                  Confirm {piece.fold_edge ? "fold edge" : "straight closure"}
                </button>
              )}
            <button onClick={() => c.exclude(piece.id)}>
              {piece.status === "excluded"
                ? "Include piece"
                : "Exclude from new lines"}
            </button>
          </div>
        ))}
        {[...doc.notices, ...(c.analysis?.notices ?? [])].map((n, i) => (
          <p className="linework-help" key={i}>
            {n}
          </p>
        ))}
      </details>
      {incomplete && (c.lines.sewing || c.lines.muslin) && (
        <label className="linework-check linework-message">
          <input
            type="checkbox"
            checked={c.allowPartial}
            onChange={(e) => c.setAllowPartial(e.target.checked)}
          />
          Generate available pieces only ({generated} of {pieces.length} on this
          page); other pages may also need review.
        </label>
      )}
      {!sameScale && (
        <p className="linework-message">
          Set Pattern Scale to 1.00 before generating, and use PDF correction
          above if needed.
        </p>
      )}
      {!valid && (
        <p className="linework-message" role="alert">
          Enter valid decimal or fractional allowances and a valid PDF
          correction.
        </p>
      )}
      <button
        className="linework-primary"
        disabled={
          !valid ||
          !sameScale ||
          !c.analysis ||
          c.analyzing ||
          c.generating ||
          (!c.lines.original && !c.lines.sewing && !c.lines.muslin) ||
          (incomplete && !c.allowPartial && (c.lines.sewing || c.lines.muslin))
        }
        onClick={() => void c.generate()}
      >
        {c.generating
          ? "GENERATING…"
          : c.analyzing
            ? "ANALYZING…"
            : "GENERATE + PROJECT"}
      </button>
      {c.projectionFile && (
        <>
          <p className="linework-help" role="status">
            {c.pendingChanges
              ? "Settings changed. Generate again to update the projected PDF."
              : "Prepared PDF is displayed with Pattern Projector’s calibration and transforms."}
          </p>
          <div className="linework-actions">
            <button onClick={download}>Download PDF</button>
            <button onClick={c.restore}>Restore original</button>
          </div>
        </>
      )}
    </>
  );
}
