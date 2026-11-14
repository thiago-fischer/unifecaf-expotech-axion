from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

CAPTURE_PATH = "/network/capture/events"
HEARTBEAT_PATH = "/network/capture/heartbeat"
FIELDS = (
    "frame.number",
    "frame.time_epoch",
    "tcp.srcport",
    "tcp.dstport",
    "tcp.stream",
    "frame.len",
    "http.request.method",
    "http.request.uri",
    "http.response.code",
    "http.request_in",
    "tcp.analysis.retransmission",
    "tcp.flags.reset",
)
NUMERIC_ROUTE = re.compile(r"(?<=/)\d+(?=/|$)")
UUID_ROUTE = re.compile(r"(?<=/)[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=/|$)")


def normalize_path(uri: str) -> str:
    path = urlsplit(uri).path or "/"
    path = UUID_ROUTE.sub("{id}", path)
    return NUMERIC_ROUTE.sub("{id}", path)[:256]


def services(source_port: int, destination_port: int) -> tuple[str, str, str]:
    if destination_port == 8000:
        return "frontend", "backend", "HTTP"
    if source_port == 8000:
        return "backend", "frontend", "HTTP"
    if destination_port == 8001:
        return "backend", "controller", "HTTP"
    if source_port == 8001:
        return "controller", "backend", "HTTP"
    if destination_port == 5432:
        return "backend", "database", "PostgreSQL"
    if source_port == 5432:
        return "database", "backend", "PostgreSQL"
    return "backend", "backend", "TCP"


@dataclass
class PendingRequest:
    observed_at: datetime
    source_service: str
    destination_service: str
    source_port: int
    destination_port: int
    tcp_stream: int
    frame_length: int
    method: str
    path: str


class Sanitizer:
    def __init__(self) -> None:
        self.requests: dict[str, PendingRequest] = {}
        self.ignored_streams: set[int] = set()
        self.suppressed: list[tuple[float, float]] = []

    def suppress(self, started_at: float, finished_at: float) -> None:
        self.suppressed.append((started_at, finished_at + 0.25))
        self.suppressed = self.suppressed[-20:]

    def parse(self, line: str) -> dict[str, object] | None:
        values = next(iter(__import__("csv").reader([line], delimiter=",", quotechar='"')))
        values += [""] * (len(FIELDS) - len(values))
        row = dict(zip(FIELDS, values, strict=True))
        try:
            frame = row["frame.number"]
            observed = datetime.fromtimestamp(float(row["frame.time_epoch"]), UTC)
            source_port = int(row["tcp.srcport"])
            destination_port = int(row["tcp.dstport"])
            stream = int(row["tcp.stream"])
            length = int(row["frame.len"])
        except (TypeError, ValueError):
            return None
        observed_epoch = observed.timestamp()
        if any(start <= observed_epoch <= finish for start, finish in self.suppressed):
            return None

        method = row["http.request.method"]
        uri = row["http.request.uri"]
        if method and uri:
            path = normalize_path(uri)
            if path in {CAPTURE_PATH, HEARTBEAT_PATH}:
                self.ignored_streams.add(stream)
                return None
            source, destination, _ = services(source_port, destination_port)
            self.requests[frame] = PendingRequest(
                observed,
                source,
                destination,
                source_port,
                destination_port,
                stream,
                length,
                method[:16],
                path,
            )
            while len(self.requests) > 2000:
                del self.requests[next(iter(self.requests))]
            return None

        if stream in self.ignored_streams:
            return None
        request_frame = row["http.request_in"]
        if row["http.response.code"] and request_frame in self.requests:
            request = self.requests.pop(request_frame)
            latency = max(0.0, (observed - request.observed_at).total_seconds() * 1000)
            return {
                "observed_at": request.observed_at.isoformat(),
                "source_service": request.source_service,
                "destination_service": request.destination_service,
                "source_port": request.source_port,
                "destination_port": request.destination_port,
                "protocol": "HTTP",
                "tcp_stream": request.tcp_stream,
                "frame_length": request.frame_length + length,
                "http_method": request.method,
                "http_path": request.path,
                "status_code": int(row["http.response.code"]),
                "latency_ms": round(latency, 3),
                "retransmission": False,
                "reset": False,
            }
        retransmission = bool(row["tcp.analysis.retransmission"])
        reset = row["tcp.flags.reset"] in {"1", "True", "true"}
        source, destination, protocol = services(source_port, destination_port)
        if protocol == "PostgreSQL" or retransmission or reset:
            return {
                "observed_at": observed.isoformat(),
                "source_service": source,
                "destination_service": destination,
                "source_port": source_port,
                "destination_port": destination_port,
                "protocol": protocol if protocol == "PostgreSQL" else "TCP",
                "tcp_stream": stream,
                "frame_length": length,
                "retransmission": retransmission,
                "reset": reset,
            }
        return None


class Delivery:
    def __init__(self, token: str, endpoint: str) -> None:
        self.token = token
        self.endpoint = endpoint.rstrip("/")
        self.session_id = str(uuid4())
        self.sequence = 0

    def send(self, events: list[dict[str, object]]) -> None:
        first = self.sequence + 1
        for event in events:
            self.sequence += 1
            event["sequence"] = self.sequence
        body = {
            "batch_id": str(uuid4()),
            "capture_session_id": self.session_id,
            "first_sequence": first,
            "last_sequence": self.sequence,
            "captured_at": datetime.now(UTC).isoformat(),
            "events": events,
        }
        self._post(CAPTURE_PATH, body, retry=True)

    def heartbeat(self) -> None:
        self._post(HEARTBEAT_PATH, {"capture_session_id": self.session_id}, retry=False)

    def _post(self, path: str, body: dict[str, object], retry: bool) -> None:
        payload = json.dumps(body, separators=(",", ":")).encode()
        delay = 0.5
        while True:
            request = Request(
                self.endpoint + path,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Axion-Capture-Token": self.token,
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=3) as response:
                    if response.status == 204:
                        return
            except HTTPError as exc:
                exc.close()
                if exc.code in {403, 422} or not retry:
                    raise RuntimeError(
                        f"Backend recusou metadados de captura (HTTP {exc.code})."
                    ) from exc
            except (URLError, OSError):
                if not retry:
                    return
            time.sleep(delay)
            delay = min(delay * 2, 5)


def tshark_command() -> list[str]:
    command = [
        "tshark",
        "-l",
        "-n",
        "-r",
        "-",
        "-d",
        "tcp.port==8000,http",
        "-d",
        "tcp.port==8001,http",
        "-T",
        "fields",
        "-E",
        "separator=,",
        "-E",
        "quote=d",
        "-E",
        "occurrence=f",
    ]
    for field in FIELDS:
        command.extend(("-e", field))
    return command


def dumpcap_command() -> list[str]:
    return [
        "dumpcap",
        "-q",
        "-i",
        "any",
        "-f",
        "tcp and (port 8000 or port 8001 or port 5432)",
        "-w",
        "-",
    ]


def main() -> None:
    token = os.environ.get("AXION_CAPTURE_TOKEN", "")
    if not token:
        raise SystemExit("Defina AXION_CAPTURE_TOKEN para iniciar a captura.")
    endpoint = os.environ.get("AXION_CAPTURE_ENDPOINT", "http://127.0.0.1:8000")
    delivery = Delivery(token, endpoint)
    sanitizer = Sanitizer()
    lines: queue.Queue[str | None] = queue.Queue(maxsize=1000)
    capture = subprocess.Popen(dumpcap_command(), stdout=subprocess.PIPE, stderr=None)
    assert capture.stdout is not None
    process = subprocess.Popen(
        tshark_command(),
        stdin=capture.stdout,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1,
    )
    capture.stdout.close()
    assert process.stdout is not None

    def read_output() -> None:
        for line in process.stdout:
            lines.put(line.rstrip("\n"))
        lines.put(None)

    threading.Thread(target=read_output, daemon=True).start()
    pending: list[dict[str, object]] = []
    last_delivery = last_heartbeat = time.monotonic()
    while True:
        try:
            line = lines.get(timeout=0.5)
        except queue.Empty:
            line = ""
        if line is None:
            process_code = process.wait()
            capture.terminate()
            capture.wait()
            raise SystemExit(process_code)
        if line:
            event = sanitizer.parse(line)
            if event is not None:
                pending.append(event)
        now = time.monotonic()
        if pending and (len(pending) >= 100 or now - last_delivery >= 1):
            delivery_started = time.time()
            delivery.send(pending)
            sanitizer.suppress(delivery_started, time.time())
            pending = []
            last_delivery = now
        if now - last_heartbeat >= 5:
            delivery.heartbeat()
            last_heartbeat = now


if __name__ == "__main__":
    main()
