"""What a "webhook" task (decision 0040) keeps beside its memory: the key a program sends events
with, whether it waits for a sample and the sample it got, the latest event and the events that
started no run and why. One JSON file per task; the key's value is in the keychain where there is
one, and only its SHA-256 is read to check an event, so checking never touches the keychain."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...runtime import delete_secret, harden_file_permissions, resolve_secret, store_secret
from ...workflow_spec import WorkflowInput
from ._trigger_files import trigger_file
from .connector_items import MAX_ITEM_CHARS, MAX_RUNNING, event_inputs, item_fields, missed_item

if TYPE_CHECKING:
    from .schedule_rule import ScheduleRule
    from .scheduled_run import ScheduledRun

_MAX_MISSED = 20
_KEY_BYTES = 32


@dataclass
class Delivery:
    """What an event came to: `status` is the HTTP status the sender gets, `message` says why in
    the person's words, and `inputs` are the run's when it starts one."""

    status: int
    message: str
    inputs: dict[str, Any] | None = None


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class WebhookEvents:
    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "task_memory"

    def key(self, trigger_id: str) -> str | None:
        """The task's key, or None when it has none or the keychain lost it (a new key helps)."""
        state = self.read(trigger_id)
        if not state.get("key_sha256"):
            return None
        try:
            key = resolve_secret(state.get("key"))
        except RuntimeError:
            return None
        return key if key and hmac.compare_digest(_digest(key), str(state["key_sha256"])) else None

    def ensure_key(self, trigger_id: str) -> None:
        """Gives the task a key when it has none; only the file is read, never the keychain."""
        if not self.read(trigger_id).get("key_sha256"):
            self.new_key(trigger_id)

    def new_key(self, trigger_id: str) -> str:
        """A new key; the old one stops working at once."""
        state = self.read(trigger_id)
        delete_secret(state.get("key"))
        key = secrets.token_urlsafe(_KEY_BYTES)
        state["key"] = store_secret(f"webhook:{trigger_id}", key)
        state["key_sha256"] = _digest(key)
        self._write(trigger_id, state)
        return key

    def accepts(self, trigger_id: str, key: str) -> bool:
        expected = str(self.read(trigger_id).get("key_sha256") or "")
        return bool(expected) and hmac.compare_digest(_digest(key), expected)

    def wait_for_sample(self, trigger_id: str, waiting: bool) -> None:
        state = self.read(trigger_id)
        state["waiting"] = waiting
        self._write(trigger_id, state)

    def take(
        self,
        trigger_id: str,
        rule: ScheduleRule,
        specs: list[WorkflowInput],
        runs: list[ScheduledRun],
        event: Any,
    ) -> Delivery:
        """What an event that came with the task's key comes to, recorded on the task."""
        state = self.read(trigger_id)
        if state.get("waiting"):
            state |= {"waiting": False, "sample": event}
            return self._done(trigger_id, state, Delivery(200, "Kept as the task's sample"))
        now = datetime.now()
        hour_ago = (now - timedelta(hours=1)).isoformat(timespec="seconds")
        # Counted here, not from the runs: the task keeps only its latest runs, and folds some.
        started = [at for at in state.get("started") or [] if str(at) >= hour_ago]
        going = sum(run.source == "webhook" and run.status == "running" for run in runs)
        if len(json.dumps(event, ensure_ascii=False, default=str)) > MAX_ITEM_CHARS:
            delivery = Delivery(400, f"It is over {MAX_ITEM_CHARS // 1000} KB")
        elif len(started) >= rule.per_hour or going >= MAX_RUNNING:
            delivery = Delivery(429, "The task is at its limit of runs; send it again later")
        else:
            try:
                inputs = event_inputs(specs, rule.inputs_from, event, date.today())
            except ValueError as exc:
                delivery = Delivery(400, str(exc))
            else:
                state["started"] = [*started, now.isoformat(timespec="seconds")]
                return self._done(trigger_id, state, Delivery(202, "Started a run", inputs))
        missed = [*(state.get("missed") or []), missed_item(event, delivery.message)]
        state["missed"] = missed[-_MAX_MISSED:]
        return self._done(trigger_id, state, delivery)

    def _done(self, trigger_id: str, state: dict[str, Any], delivery: Delivery) -> Delivery:
        state["last_event"] = {
            "at": datetime.now().isoformat(timespec="seconds"),
            "status": delivery.status,
            "message": delivery.message,
        }
        self._write(trigger_id, state)
        return delivery

    def shown(self, trigger_id: str) -> dict[str, Any]:
        """What the task page shows: never the key, which has a route of its own."""
        state = self.read(trigger_id)
        return {
            "waiting": bool(state.get("waiting")),
            "sample": state.get("sample"),
            # Its fields by dotted path, as the form offers them to inputs.
            "fields": item_fields(state.get("sample")),
            "last_event": state.get("last_event"),
            "missed": state.get("missed") or [],
        }

    def forget(self, trigger_id: str) -> None:
        delete_secret(self.read(trigger_id).get("key"))
        self._path(trigger_id).unlink(missing_ok=True)

    def read(self, trigger_id: str) -> dict[str, Any]:
        try:
            data = json.loads(self._path(trigger_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write(self, trigger_id: str, state: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(trigger_id)
        tmp_path = path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, path)
        # Where there is no keychain the key is in this file.
        harden_file_permissions(path)

    def _path(self, trigger_id: str) -> Path:
        return trigger_file(self.root, trigger_id, ".webhook.json")
