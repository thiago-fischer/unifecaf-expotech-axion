import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector import (  # noqa: E402
    CAPTURE_PATH,
    Delivery,
    Sanitizer,
    dumpcap_command,
    normalize_path,
)


def row(*values: object) -> str:
    return ",".join(f'"{value}"' for value in values)


class SanitizerTests(unittest.TestCase):
    def test_normalizes_ids_and_removes_query(self) -> None:
        self.assertEqual(
            normalize_path("/orders/123/executions?token=secret"), "/orders/{id}/executions"
        )

    def test_correlates_http_without_payload(self) -> None:
        parser = Sanitizer()
        self.assertIsNone(parser.parse(row(10, 1000, 51000, 8000, 4, 100, "GET", "/orders/12?x=1")))
        event = parser.parse(row(11, 1000.125, 8000, 51000, 4, 90, "", "", 200, 10))
        assert event is not None
        self.assertEqual(event["http_path"], "/orders/{id}")
        self.assertEqual(event["latency_ms"], 125.0)
        serialized = str(event)
        self.assertNotIn("x=1", serialized)
        self.assertNotIn("payload", serialized)

    def test_ignores_ingestion_stream_to_prevent_feedback(self) -> None:
        parser = Sanitizer()
        self.assertIsNone(parser.parse(row(20, 1000, 52000, 8000, 8, 120, "POST", CAPTURE_PATH)))
        self.assertIsNone(parser.parse(row(21, 1000.1, 8000, 52000, 8, 80, "", "", 204, 20)))

    def test_emits_postgresql_metadata_and_tcp_flags(self) -> None:
        parser = Sanitizer()
        event = parser.parse(row(30, 1000, 50100, 5432, 9, 70))
        assert event is not None
        self.assertEqual(event["protocol"], "PostgreSQL")
        self.assertNotIn("http_path", event)

    def test_capture_streams_to_stdout_without_pcap_path(self) -> None:
        command = dumpcap_command()
        self.assertEqual(command[command.index("-w") + 1], "-")

    def test_suppresses_traffic_caused_by_metric_persistence(self) -> None:
        parser = Sanitizer()
        parser.suppress(999.5, 1000.1)
        self.assertIsNone(parser.parse(row(40, 1000, 50100, 5432, 10, 90)))

    def test_retries_exact_same_batch_after_transient_failure(self) -> None:
        payloads: list[bytes] = []

        class Response:
            status = 204

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        def send(request: object, timeout: int) -> Response:
            self.assertEqual(timeout, 3)
            payloads.append(request.data)  # type: ignore[attr-defined]
            if len(payloads) == 1:
                raise URLError("temporária")
            return Response()

        delivery = Delivery("token-local", "http://127.0.0.1:8000")
        event = {
            "observed_at": "2026-11-14T19:00:00-03:00",
            "source_service": "frontend",
            "destination_service": "backend",
            "source_port": 51000,
            "destination_port": 8000,
            "protocol": "HTTP",
            "tcp_stream": 1,
            "frame_length": 100,
        }
        with patch("collector.urlopen", side_effect=send), patch("collector.time.sleep"):
            delivery.send([event])
        self.assertEqual(payloads[0], payloads[1])
        self.assertEqual(json.loads(payloads[0])["events"][0]["sequence"], 1)


if __name__ == "__main__":
    unittest.main()
