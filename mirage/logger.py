import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class HoneypotLogger:
    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "mirage.log"
        self.events_file = self.log_dir / "events.jsonl"

    def _append_line(self, path: Path, message: str) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    def record_event(self, event_type: str, **details: Any) -> None:
        payload = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event_type, **details}
        self._append_line(self.log_file, f"{event_type} {json.dumps(details, default=str)}")
        self._append_line(self.events_file, json.dumps(payload))
