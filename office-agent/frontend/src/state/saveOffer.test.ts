import { describe, expect, it } from "vitest";
import { chatReducer, initialChatState, type ChatAction, type ChatState } from "./reducer";

const stateWith = (patch: Partial<ChatState> = {}): ChatState => ({ ...initialChatState, ...patch });
const run = (state: ChatState, ...actions: ChatAction[]): ChatState => actions.reduce(chatReducer, state);

describe("save offer", () => {
  it("is kept until the person sends something or answers it", () => {
    const offered = run(stateWith({}), { type: "save_offer", steps: 6, name: "Weekly report" });
    expect(offered.saveOffer).toEqual({ steps: 6, name: "Weekly report" });
    expect(run(offered, { type: "turn_started", text: "x" }).saveOffer).toBeNull();
    expect(run(offered, { type: "local_user_message", text: "x", instant: false }).saveOffer).toBeNull();
    expect(run(offered, { type: "local_save_offer_dismissed" }).saveOffer).toBeNull();
  });

  it("is not shown while a turn is running", () => {
    const running = stateWith({ turnInFlight: true });
    expect(run(running, { type: "save_offer", steps: 4, name: "Late" })).toBe(running);
  });
});
