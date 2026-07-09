import { describe, expect, it } from "vitest";
import { parseManifest } from "./images";

const EMPTY_META = { cities: {}, corridors: {}, societies: {} };

// Same cases run by hand in round 4 (node --experimental-strip-types),
// committed here so the malformed-shape handling can't silently regress.
// Imports the actual shipped parseManifest - not a reimplementation.
// Extended in round 7 when _meta (illustrative-tag disclosure) went from
// "ignored" to "parsed defensively" - same malformed-input discipline
// applies to it as to the image paths themselves.
describe("parseManifest", () => {
  it("passes through a valid nested manifest unchanged", () => {
    const input = {
      cities: { Pune: "/assets/images/pune.jpg" },
      corridors: { "Pune::Hinjewadi": "/assets/images/hinjewadi.jpg" },
      societies: { "Pune::Hinjewadi::Godrej Elements": "/assets/images/godrej-elements.jpg" },
    };
    expect(parseManifest(input)).toEqual({ ...input, meta: EMPTY_META });
  });

  it("fills in missing keys with empty buckets", () => {
    expect(parseManifest({})).toEqual({ cities: {}, corridors: {}, societies: {}, meta: EMPTY_META });
  });

  it("treats null as an empty manifest", () => {
    expect(parseManifest(null)).toEqual({ cities: {}, corridors: {}, societies: {}, meta: EMPTY_META });
  });

  it("treats a top-level array as an empty manifest", () => {
    expect(parseManifest([])).toEqual({ cities: {}, corridors: {}, societies: {}, meta: EMPTY_META });
  });

  it("treats a top-level string as an empty manifest", () => {
    expect(parseManifest("oops")).toEqual({ cities: {}, corridors: {}, societies: {}, meta: EMPTY_META });
  });

  it("drops a bucket whose value is the wrong type", () => {
    const input = { cities: "not an object", corridors: { b: "y" }, societies: null };
    expect(parseManifest(input)).toEqual({ cities: {}, corridors: { b: "y" }, societies: {}, meta: EMPTY_META });
  });

  it("drops individual non-string values within a bucket", () => {
    const input = { cities: { a: 123, b: null, c: "ok" }, corridors: {}, societies: {} };
    expect(parseManifest(input)).toEqual({ cities: { c: "ok" }, corridors: {}, societies: {}, meta: EMPTY_META });
  });

  it("tolerates _comment and parses a well-formed _meta block", () => {
    const input = {
      _comment: "hi",
      cities: {},
      corridors: { "Pune::Hinjewadi": "/x.jpg" },
      societies: {},
      _meta: { corridors: { "Pune::Hinjewadi": { illustrative: true } } },
    };
    expect(parseManifest(input)).toEqual({
      cities: {},
      corridors: { "Pune::Hinjewadi": "/x.jpg" },
      societies: {},
      meta: { cities: {}, corridors: { "Pune::Hinjewadi": { illustrative: true } }, societies: {} },
    });
  });

  it("degrades a malformed _meta to empty meta buckets, never throws", () => {
    const input = { cities: {}, corridors: {}, societies: {}, _meta: "not an object" };
    expect(parseManifest(input)).toEqual({ cities: {}, corridors: {}, societies: {}, meta: EMPTY_META });
  });

  it("drops a _meta entry whose value isn't an object, and a non-boolean illustrative flag", () => {
    const input = {
      cities: {},
      corridors: {},
      societies: {},
      _meta: { cities: { A: "not an object", B: { illustrative: "yes" }, C: { illustrative: true } } },
    };
    expect(parseManifest(input)).toEqual({
      cities: {},
      corridors: {},
      societies: {},
      meta: { cities: { B: { illustrative: undefined }, C: { illustrative: true } }, corridors: {}, societies: {} },
    });
  });
});
