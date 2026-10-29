// @vitest-environment jsdom
import { getSchema } from "@tiptap/core";
import { Node as PMNode } from "@tiptap/pm/model";
import type { Decoration } from "@tiptap/pm/view";
import { describe, expect, it } from "vitest";
import { docContent, docExtensions } from "./docModel";
import { tableLook } from "./docTableLook";

const schema = getSchema(docExtensions);
const classes = (decorations: Decoration[]) => decorations.map((d) => (d as unknown as { type: { attrs: { class: string } } }).type.attrs.class);

describe("tableLook", () => {
  it("right-aligns number columns and bolds a last total row, as the Word file does", () => {
    const text = "| 渠道 | 订单 |\n| --- | --- |\n| 自然搜索 | 1,240 |\n| 信息流 | 860 |\n| 合计 | 2,100 |";
    const doc = PMNode.fromJSON(schema, docContent([{ index: 0, kind: "table", text }]));
    const found = classes(tableLook(doc.child(0), 0));
    expect(found.filter((c) => c.includes("doc-num"))).toHaveLength(4);
    expect(found.filter((c) => c.includes("doc-total"))).toHaveLength(2);
  });

  it("leaves a table of words alone", () => {
    const text = "| 环节 | 负责人 |\n| --- | --- |\n| 预算核对 | 张明 |";
    const doc = PMNode.fromJSON(schema, docContent([{ index: 0, kind: "table", text }]));
    expect(tableLook(doc.child(0), 0)).toEqual([]);
  });
});
