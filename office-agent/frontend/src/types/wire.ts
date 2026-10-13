/**
 * The chat WebSocket's wire types. They are generated from
 * src/coscribe/conversation/wire.py into wire.gen.ts, so a change to an event
 * starts in Python (`python scripts/gen_wire_ts.py` regenerates the file) and
 * shows up here as a type error wherever the frontend disagrees.
 */
import type { ClientMessage, ServerEvent } from "./wire.gen";

export type * from "./wire.gen";

export type WsServerEvent = ServerEvent;
export type WsClientMessage = ClientMessage;
