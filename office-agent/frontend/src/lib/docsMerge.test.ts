import { describe, expect, it } from "vitest";
import type { Block } from "./docsEditor";
import { mergeBlocks } from "./docsMerge";

const para = (id: string | undefined, text: string): Block => ({ id, kind: "paragraph", runs: [{ t: text }] });
const texts = (blocks: Block[] | null) => blocks?.map((b) => ("runs" in b ? b.runs.map((r) => r.t).join("") : b.kind));
const BASE = [para("b0", "one"), para("b1", "two"), para("b2", "three"), para("b3", "four")];

describe("mergeBlocks", () => {
  it("keeps the person's edit and the file's change when they touch different blocks", () => {
    const mine = [BASE[0], para("b1", "two, edited"), BASE[2], BASE[3]];
    const theirs = [BASE[0], BASE[1], BASE[2], para("b3", "four, by coscribe")];
    const merged = mergeBlocks(BASE, mine, theirs);
    expect(texts(merged)).toEqual(["one", "two, edited", "three", "four, by coscribe"]);
    expect(merged?.map((b) => b.id)).toEqual(["b0", "b1", "b2", "b3"]);
  });

  it("takes the ids of the file when it added a block before the person's edit", () => {
    const theirs = [para("b0", "intro"), para("b1", "one"), para("b2", "two"), para("b3", "three"), para("b4", "four")];
    const mine = [BASE[0], para("b1", "two, edited"), BASE[2], BASE[3]];
    const merged = mergeBlocks(BASE, mine, theirs);
    expect(texts(merged)).toEqual(["intro", "one", "two, edited", "three", "four"]);
    expect(merged?.map((b) => b.id)).toEqual(["b0", "b1", "b2", "b3", "b4"]);
  });

  it("brings in a block the person added without an id, and their delete", () => {
    const mine = [BASE[0], para(undefined, "new line"), BASE[1], BASE[3]];
    const theirs = [BASE[0], BASE[1], BASE[2], para("b3", "four, by coscribe")];
    const merged = mergeBlocks(BASE, mine, theirs);
    expect(texts(merged)).toEqual(["one", "new line", "two", "four, by coscribe"]);
    expect(merged?.[1].id).toBeUndefined();
  });

  it("gives up where both changed the same block, and where both added at the same place", () => {
    const edited = (text: string) => BASE.map((b, i) => (i === 1 ? para("b1", text) : b));
    expect(mergeBlocks(BASE, edited("mine"), edited("theirs"))).toBeNull();
    const added = (text: string) => [BASE[0], para(undefined, text), ...BASE.slice(1)];
    expect(mergeBlocks(BASE, added("mine"), added("theirs"))).toBeNull();
  });

  it("is the person's text when the file did not change, and the file's when they did not", () => {
    const mine = [...BASE.slice(0, 3), para("b3", "four, edited")];
    expect(texts(mergeBlocks(BASE, mine, BASE))).toEqual(texts(mine));
    expect(texts(mergeBlocks(BASE, BASE, mine))).toEqual(texts(mine));
  });
});
