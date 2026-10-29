import { expect, test, beforeEach } from "@jest/globals";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useLinework } from "./use-linework";
import { api, exportPattern } from "../api/client";

jest.mock("../api/client", () => ({
  api: jest.fn(),
  exportPattern: jest.fn(),
  jsonRequest: (body: unknown) => ({
    method: "POST",
    body: JSON.stringify(body),
  }),
}));
const mockApi = api as jest.Mock;
const mockExport = exportPattern as jest.Mock;
const doc = {
  id: "test",
  name: "Pattern.pdf",
  sizes: ["S", "M", "L"],
  pages: [{ number: 1, width_mm: 500, height_mm: 500, rotation: 0 }],
  source_allowance_mm: 9.525,
  source_hem_mm: 50.8,
  layers: [],
  calibration: [],
  notices: [],
  sha256: "x",
};
const analysis = {
  pieces: [],
  generated: [],
  bounds: null,
  notices: [],
  markings: [],
  source_paths: [],
};
beforeEach(() => {
  jest.clearAllMocks();
  mockApi.mockImplementation((path: string) =>
    Promise.resolve(path === "/documents" ? doc : analysis),
  );
  mockExport.mockResolvedValue(
    new Blob(["%PDF-test"], { type: "application/pdf" }),
  );
});

test("uses suggested allowance and keeps the original file immutable while preparing a derived PDF", async () => {
  const source = new File(["%PDF-source"], "Pattern.pdf", {
    type: "application/pdf",
  });
  const { result } = renderHook(() => useLinework(source));
  await waitFor(() => expect(result.current.analysis).toEqual(analysis));
  expect(result.current.settings.seam_mm).toBe(9.525);
  expect(result.current.size).toBe("M");
  await act(async () => {
    await result.current.generate();
  });
  expect(result.current.projectionFile).not.toBe(source);
  expect(result.current.projectionFile?.name).toContain("M linework");
  expect(source.name).toBe("Pattern.pdf");
  expect(mockExport).toHaveBeenCalledWith(
    "test",
    expect.objectContaining({
      size: "M",
      scale: 1,
      generate: true,
      settings: expect.objectContaining({ seam_mm: 9.525, muslin_mm: 25.4 }),
      allow_partial: false,
    }),
  );
  act(() => result.current.restore());
  expect(result.current.projectionFile).toBeNull();
});

test("never shows a prepared PDF from a previously opened source", async () => {
  const first = new File(["%PDF-first"], "first.pdf");
  const second = new File(["%PDF-second"], "second.pdf");
  const { result, rerender } = renderHook(({ file }) => useLinework(file), {
    initialProps: { file: first },
  });
  await waitFor(() => expect(result.current.analysis).toEqual(analysis));
  await act(async () => {
    await result.current.generate();
  });
  expect(result.current.projectionFile).not.toBeNull();
  rerender({ file: second });
  expect(result.current.projectionFile).toBeNull();
  await waitFor(() => expect(result.current.uploading).toBe(false));
});

test("marks changed allowances as pending instead of pretending old generated lines are current", async () => {
  const source = new File(["%PDF-source"], "Pattern.pdf");
  const { result } = renderHook(() => useLinework(source));
  await waitFor(() => expect(result.current.analysis).toEqual(analysis));
  await act(async () => {
    await result.current.generate();
  });
  act(() => result.current.setSettings((old) => ({ ...old, muslin_mm: 38.1 })));
  expect(result.current.pendingChanges).toBe(true);
  expect(result.current.projectionFile).not.toBeNull();
});

test("restoring the original discards a later result from an in-flight generation", async () => {
  let finish!: (blob: Blob) => void;
  mockExport.mockImplementationOnce(
    () =>
      new Promise<Blob>((resolve) => {
        finish = resolve;
      }),
  );
  const source = new File(["%PDF-source"], "Pattern.pdf");
  const { result } = renderHook(() => useLinework(source));
  await waitFor(() => expect(result.current.analysis).toEqual(analysis));
  let pending!: Promise<void>;
  act(() => {
    pending = result.current.generate();
  });
  act(() => result.current.restore());
  await act(async () => {
    finish(new Blob(["%PDF-late"]));
    await pending;
  });
  expect(result.current.projectionFile).toBeNull();
  expect(result.current.generating).toBe(false);
});
