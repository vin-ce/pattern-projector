import { expect, test } from "@jest/globals";
import { escapeHtml } from "./escape-html";

test("treats executable-looking PDF text as literal text in hover labels", () => {
  expect(escapeHtml('<img src=x onerror="alert(1)">')).toBe(
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
  expect(escapeHtml("grainline & ⅜″ 'fold'")).toBe(
    "grainline &amp; ⅜″ &#39;fold&#39;",
  );
});
