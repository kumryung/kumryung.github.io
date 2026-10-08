"""Durable Nginx visit ingestion and Telegram notifications; stdlib only."""
import datetime as dt
import ipaddress
import json
import math
import re
import socket
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

WINDOW = 600
HOST = "www.ryanfamily.xyz"
KST = dt.timezone(dt.timedelta(hours=9))


def parse_visit(raw):
    """Only successful homepage GETs from the existing Cloudflare tunnel."""
    try:
        event = json.loads(raw)
        if (event.get("host") != HOST or event.get("proto") != "https"
                or event.get("method") != "GET" or event.get("path") not in ("/", "/index.html")
                or str(event.get("status")) not in ("200", "304")):
            return None
        address = ipaddress.ip_address(event["ip"])
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if not address.is_global:
            return None
        timestamp = float(event["at"])
        if not math.isfinite(timestamp) or timestamp <= 0:
            return None
        return str(address), timestamp
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


class VisitStore:
    def __init__(self, path):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS seen(ip TEXT PRIMARY KEY, last_seen REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS cursors(source TEXT PRIMARY KEY, offset INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS outbox(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT NOT NULL, visited REAL NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, next_try REAL NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS metrics(name TEXT PRIMARY KEY, value REAL NOT NULL);
        """)

    def offset(self, source):
        with self.lock:
            row = self.db.execute("SELECT offset FROM cursors WHERE source=?", (source,)).fetchone()
            return row[0] if row else 0

    def ingest(self, raw, source, offset):
        visit = parse_visit(raw)
        queued = False
        with self.lock, self.db:
            if visit:
                ip, timestamp = visit
                previous = self.db.execute("SELECT last_seen FROM seen WHERE ip=?", (ip,)).fetchone()
                # Late log writes must never move the window backwards.
                if previous is None or timestamp - previous[0] >= WINDOW:
                    self.db.execute("INSERT INTO outbox(ip,visited) VALUES (?,?)", (ip, timestamp))
                    queued = True
                self.db.execute("""INSERT INTO seen(ip,last_seen) VALUES (?,?)
                    ON CONFLICT(ip) DO UPDATE SET last_seen=MAX(last_seen,excluded.last_seen)""", (ip, timestamp))
                self.db.execute("""INSERT INTO metrics VALUES ('visits',1)
                    ON CONFLICT(name) DO UPDATE SET value=value+1""")
                if not queued:
                    self.db.execute("""INSERT INTO metrics VALUES ('suppressed',1)
                        ON CONFLICT(name) DO UPDATE SET value=value+1""")
            self.db.execute("""INSERT INTO cursors VALUES (?,?)
                ON CONFLICT(source) DO UPDATE SET offset=excluded.offset""", (source, offset))
        return queued

    def pending(self, now):
        with self.lock:
            return self.db.execute("SELECT id,ip,visited,attempts FROM outbox WHERE next_try<=? ORDER BY id LIMIT 1", (now,)).fetchone()

    def delivered(self, event_id, now):
        with self.lock, self.db:
            self.db.execute("DELETE FROM outbox WHERE id=?", (event_id,))
            self.db.execute("INSERT INTO metrics VALUES ('delivered',1) ON CONFLICT(name) DO UPDATE SET value=value+1")
            self.db.execute("INSERT INTO metrics VALUES ('last_sent',?) ON CONFLICT(name) DO UPDATE SET value=excluded.value", (now,))

    def retry(self, event_id, now, delay):
        with self.lock, self.db:
            self.db.execute("UPDATE outbox SET attempts=attempts+1,next_try=? WHERE id=?", (now + delay, event_id))

    def cleanup(self, now):
        with self.lock, self.db:
            self.db.execute("DELETE FROM seen WHERE last_seen<?", (now - WINDOW,))

    def summary(self):
        with self.lock:
            values = dict(self.db.execute("SELECT name,value FROM metrics"))
            values["pending"] = self.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0]
            return values


def drain_logs(store, folder):
    # Daily files survive notifier restarts. Cursor + dedup + outbox commit together.
    caught_up = True
    for file in sorted(folder.glob("*.jsonl")):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.jsonl", file.name):
            continue
        stat = file.stat()
        source = f"{file.name}:{stat.st_ino}"
        offset = store.offset(source)
        if stat.st_size < offset:
            raise RuntimeError("Visit log was truncated; preserve cursor and inspect")
        with file.open("rb") as stream:
            stream.seek(offset)
            for _ in range(2000):
                line = stream.readline(8192)
                if not line:
                    break
                if not line.endswith(b"\n"):
                    caught_up = False
                    break
                store.ingest(line, source, stream.tell())
            if stream.tell() < stat.st_size:
                caught_up = False
            consumed = stream.tell() == stat.st_size and store.offset(source) == stat.st_size
        # Only completed old daily files; never rotate/truncate the active file.
        if consumed and time.time() - stat.st_mtime > 172800:
            file.unlink()
            with store.lock, store.db:
                store.db.execute("DELETE FROM cursors WHERE source=?", (source,))
    return caught_up


class TelegramError(Exception):
    def __init__(self, code, retry_after=0):
        self.code = code
        self.retry_after = retry_after


def send_telegram(token, chat_id, ip, timestamp):
    moment = dt.datetime.fromtimestamp(timestamp, KST).strftime("%Y-%m-%d %H:%M:%S KST")
    message = (f"🌐 라이언패밀리 홈페이지 방문\n\nIP: {ip}\n시각: {moment}\n"
               f"페이지: https://{HOST}/\n\n최근 10분 동안 방문이 없었던 IP입니다.")
    payload = json.dumps({"chat_id": chat_id, "text": message,
                          "link_preview_options": {"is_disabled": True}}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.loads(response.read(65536))
    except urllib.error.HTTPError as error:
        retry_after = 0
        if error.code == 429:
            try:
                retry_after = int(json.loads(error.read(65536)).get("parameters", {}).get("retry_after", 0))
            except (ValueError, TypeError):
                pass
        raise TelegramError(error.code, retry_after) from None
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, ValueError):
        raise TelegramError("network") from None
    if not result.get("ok"):
        raise TelegramError(result.get("error_code", "api"))
    return result["result"]["message_id"]


def sender_loop(store, token, chat_id):
    while True:
        event = store.pending(time.time())
        if not event:
            time.sleep(0.5)
            continue
        event_id, ip, timestamp, attempts = event
        try:
            message_id = send_telegram(token, chat_id, ip, timestamp)
            store.delivered(event_id, time.time())
            print(json.dumps({"event": "telegram_sent", "message_id": message_id}), flush=True)
            time.sleep(1.1)
        except TelegramError as error:
            delay = max(error.retry_after, min(300, 5 * 2 ** min(attempts, 6)))
            store.retry(event_id, time.time(), delay)
            # Never log the URL, token, full exception, IP, or message payload.
            print(json.dumps({"event": "telegram_retry", "code": error.code, "retry_in": delay}), flush=True)


def main():
    heartbeat = Path("/tmp/notifier-heartbeat")
    if "--health" in sys.argv:
        try:
            return 0 if time.time() - float(heartbeat.read_text()) < 90 else 1
        except (OSError, ValueError):
            return 1
    token = Path("/run/secrets/telegram_bot_token").read_text().strip()
    chat_id = Path("/run/secrets/telegram_chat_id").read_text().strip()
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]{20,}", token) or not re.fullmatch(r"-?\d+", chat_id):
        print("Invalid Telegram secret configuration", flush=True)
        return 1
    store = VisitStore("/state/visits.sqlite3")
    sender = threading.Thread(target=sender_loop, args=(store, token, chat_id), daemon=True)
    sender.start()
    print(json.dumps({"event": "notifier_ready", "window_seconds": WINDOW}), flush=True)
    last_cleanup = 0
    while True:
        caught_up = drain_logs(store, Path("/logs"))
        now = time.time()
        if caught_up and now - last_cleanup >= 60:
            store.cleanup(now)
            last_cleanup = now
        if not sender.is_alive():
            raise RuntimeError("Notification sender stopped")
        heartbeat.write_text(str(now))
        time.sleep(0.5 if not caught_up else 1)


if __name__ == "__main__":
    sys.exit(main())
