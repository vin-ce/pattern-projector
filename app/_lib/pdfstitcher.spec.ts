/** @jest-environment node */
import { expect, test } from "@jest/globals";
import { PDFDocument, PDFDict, PDFName } from "@cantoo/pdf-lib";
import { savePDF } from "./pdfstitcher";
import { LineDirection } from "./interfaces/stitch-settings";

const settings = {
  key: "test",
  lineCount: 1,
  edgeInsets: { horizontal: 0, vertical: 0 },
  pageRange: "1-2",
  lineDirection: LineDirection.Row,
};
const fileFrom = (bytes: Uint8Array) =>
  ({
    name: "prepared.pdf",
    arrayBuffer: async () => Uint8Array.from(bytes).buffer,
  }) as File;

test("saving a prepared one-page PDF retains its physical page dimensions and source bytes", async () => {
  const doc = await PDFDocument.create();
  doc.addPage([144, 288]).drawLine({
    start: { x: 10, y: 10 },
    end: { x: 100, y: 100 },
    thickness: 0.7,
  });
  const bytes = await doc.save();
  const original = Array.from(bytes);
  const output = await PDFDocument.load(
    await savePDF(fileFrom(bytes), settings, {}),
  );
  expect(output.getPages()[0].getSize()).toEqual({ width: 144, height: 288 });
  expect(Array.from(bytes)).toEqual(original);
});

test("native stitching keeps both pages as vector form objects with the expected physical extent", async () => {
  const doc = await PDFDocument.create();
  for (let i = 0; i < 2; i++)
    doc.addPage([72, 144]).drawLine({
      start: { x: 10, y: 10 },
      end: { x: 60, y: 100 },
      thickness: 0.7,
    });
  const output = await PDFDocument.load(
    await savePDF(fileFrom(await doc.save()), settings, {}),
  );
  expect(output.getPageCount()).toBe(1);
  expect(output.getPages()[0].getSize()).toEqual({ width: 288, height: 288 });
  const resources = output.getPages()[0].node.Resources()!;
  const forms = resources.lookup(PDFName.of("XObject"), PDFDict);
  expect(forms.keys()).toHaveLength(2);
});

test("an empty source page keeps its grid space without breaking vector stitching", async () => {
  const doc = await PDFDocument.create();
  doc.addPage([72, 144]);
  doc
    .addPage([72, 144])
    .drawLine({
      start: { x: 10, y: 10 },
      end: { x: 60, y: 100 },
      thickness: 0.7,
    });
  const output = await PDFDocument.load(
    await savePDF(fileFrom(await doc.save()), settings, {}),
  );
  expect(output.getPageCount()).toBe(1);
  const forms = output
    .getPages()[0]
    .node.Resources()!
    .lookup(PDFName.of("XObject"), PDFDict);
  expect(forms.keys()).toHaveLength(1);
});
