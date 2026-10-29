import { expect, test } from "@jest/globals";
import { parseInches, formatInches } from "./measurements";

test("accepts decimal, fraction, and mixed inch allowances in physical millimetres", () => {
  expect(parseInches("3/8")).toBeCloseTo(9.525);
  expect(parseInches("1")).toBeCloseTo(25.4);
  expect(parseInches("1 5/8")).toBeCloseTo(41.275);
  expect(parseInches("0.375")).toBeCloseTo(9.525);
  expect(formatInches(9.525)).toBe("3/8");
  expect(formatInches(41.275)).toBe("1 5/8");
});

test.each(["", "3/0", "-1", "abc", "1.2.3"])(
  "rejects invalid physical measurements: %s",
  (value) => {
    expect(parseInches(value)).toBeNull();
  },
);
