import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from visit_notifier import VisitStore, drain_logs, parse_visit, send_telegram, TelegramError


def event(ip="8.8.8.8", at=1000, **fields):
    return json.dumps(dict(ip=ip, at=at, host="www.ryanfamily.xyz", proto="https",
                          method="GET", path="/", status="200") | fields).encode() + b"\n"


class VisitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.store = VisitStore(self.path / "state.sqlite")

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def ingest(self, at, ip="8.8.8.8"):
        return self.store.ingest(event(ip, at), "test", int(at))

    def test_sliding_window_and_exact_boundary(self):
        self.assertTrue(self.ingest(1000))
        self.assertFalse(self.ingest(1599))
        self.assertFalse(self.ingest(1601))
        self.assertFalse(self.ingest(2200))
        self.assertTrue(self.ingest(2800))
        self.assertTrue(self.ingest(2801, "1.1.1.1"))
        self.assertEqual(self.store.summary()["pending"], 3)

    def test_restart_persists_seen_and_pending(self):
        self.ingest(1000)
        self.store.db.close()
        self.store = VisitStore(self.path / "state.sqlite")
        self.assertFalse(self.ingest(1001))
        self.assertEqual(self.store.summary()["pending"], 1)

    def test_late_write_does_not_shorten_window(self):
        self.ingest(2000)
        self.assertFalse(self.ingest(1000))
        self.assertFalse(self.ingest(2500))

    def test_only_external_document_requests(self):
        for fields in [dict(method="HEAD"), dict(path="/styles.css"), dict(path="/healthz"),
                       dict(status="404"), dict(status="308"), dict(host="other.example"),
                       dict(proto="http"), dict(ip="127.0.0.1"), dict(ip=""),
                       dict(ip="8.8.8.8,1.1.1.1"), dict(at="NaN")]:
            self.assertIsNone(parse_visit(event(**fields)), fields)
        self.assertIsNotNone(parse_visit(event(status="304", path="/index.html")))
        self.assertIsNone(parse_visit(b"garbage"))

    def test_ipv6_and_ipv4_mapped_normalization(self):
        self.assertEqual(parse_visit(event(ip="::ffff:8.8.8.8"))[0], "8.8.8.8")
        a = parse_visit(event(ip="2606:4700:4700:0000:0000:0000:0000:1111"))[0]
        b = parse_visit(event(ip="2606:4700:4700::1111"))[0]
        self.assertEqual(a, b)

    def test_partial_log_and_cursor_replay(self):
        file = self.path / "2026-10-08.jsonl"
        data = event()
        file.write_bytes(data[:-1])
        self.assertFalse(drain_logs(self.store, self.path))
        self.assertEqual(self.store.summary()["pending"], 0)
        file.write_bytes(data)
        self.assertTrue(drain_logs(self.store, self.path))
        self.assertTrue(drain_logs(self.store, self.path))
        self.assertEqual(self.store.summary()["visits"], 1)

    def test_retry_is_durable_and_success_removes_event(self):
        self.ingest(1000)
        record = self.store.pending(1000)
        self.store.retry(record[0], 1000, 30)
        self.assertIsNone(self.store.pending(1029))
        self.assertEqual(self.store.pending(1030)[3], 1)
        self.store.delivered(record[0], 1030)
        self.assertEqual(self.store.summary()["pending"], 0)
        self.assertEqual(self.store.summary()["delivered"], 1)

    def test_cleanup_keeps_recent_ip(self):
        self.ingest(1000)
        self.store.cleanup(1600)
        self.assertIsNotNone(self.store.db.execute("SELECT ip FROM seen").fetchone())
        self.store.cleanup(1601)
        self.assertIsNone(self.store.db.execute("SELECT ip FROM seen").fetchone())

    def test_failed_send_does_not_expose_token(self):
        with patch("visit_notifier.urllib.request.urlopen", side_effect=OSError("secret-url")):
            with self.assertRaises(TelegramError) as result:
                send_telegram("123:secret", "123", "8.8.8.8", 1000)
        self.assertNotIn("secret", str(result.exception))


if __name__ == "__main__":
    unittest.main()
