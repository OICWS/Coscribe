import { describe, expect, it } from "vitest";
import { ruleSentence } from "./folderRules";

describe("ruleSentence", () => {
  it("says a rule in words", () => {
    expect(ruleSentence("write_file(docs/*)")).toBe("Write file in docs/");
    expect(ruleSentence("run_background_command(git status*)")).toBe("Run commands starting “git status”");
    expect(ruleSentence("run_background_command(npm test)")).toBe("Run “npm test”");
    expect(ruleSentence("github_delete_*")).toBe("Any Github delete action");
    expect(ruleSentence("fetch_*")).toBe("Any fetch action");
    expect(ruleSentence("read_file")).toBe("Read file");
  });

  it("leaves what it can't say better as written", () => {
    expect(ruleSentence("weird rule!")).toBeNull();
    expect(ruleSentence("*")).toBeNull();
  });
});
