from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import json, os, ssl, subprocess, time

UZEX_URLS = ["https://uzex.uz/", "https://www.uzex.uz/"]
HOST, PORT = "127.0.0.1", 8000
sync_data = {"server_epoch_ms": None, "local_monotonic_ms": None, "source": None,
             "last_sync_utc": None, "round_trip_ms": None, "error": None}

def parse_http_date(value):
    if not value:
        return None
    dt = parsedate_to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp() * 1000

def fetch_date_with_urllib(url):
    request = Request(
        url + ("&" if "?" in url else "?") + f"clock_sync={int(time.time()*1000)}",
        method="GET",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "close",
        },
    )
    before = time.monotonic() * 1000
    with urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
        date_header = response.headers.get("Date")
        response.read(256)
    after = time.monotonic() * 1000
    epoch = parse_http_date(date_header)
    if epoch is None:
        raise RuntimeError("No HTTP Date header was returned.")
    return epoch, (before + after) / 2, after - before

def fetch_date_with_curl(url):
    null_device = "NUL" if os.name == "nt" else "/dev/null"
    command = ["curl", "-L", "-sS", "--max-time", "20", "--connect-timeout", "10",
               "-A", "Mozilla/5.0", "-H", "Accept-Encoding: identity",
               "-H", "Cache-Control: no-cache", "-D", "-", "-o", null_device,
               url + ("&" if "?" in url else "?") + f"clock_sync={int(time.time()*1000)}"]
    before = time.monotonic() * 1000
    done = subprocess.run(command, capture_output=True, text=True, timeout=25, check=False)
    after = time.monotonic() * 1000
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or "curl request failed")
    dates = [line.split(":",1)[1].strip() for line in done.stdout.splitlines() if line.lower().startswith("date:")]
    if not dates:
        raise RuntimeError("curl response did not contain a Date header")
    return parse_http_date(dates[-1]), (before + after) / 2, after - before

def sync_with_uzex():
    errors = []
    for url in UZEX_URLS:
        for method_name, method in (("Python GET", fetch_date_with_urllib), ("curl GET", fetch_date_with_curl)):
            try:
                epoch, midpoint, round_trip = method(url)
                sync_data.update({"server_epoch_ms": epoch, "local_monotonic_ms": midpoint,
                                  "source": url, "last_sync_utc": datetime.now(timezone.utc).isoformat(),
                                  "round_trip_ms": round(round_trip, 1), "method": method_name, "error": None})
                return
            except Exception as exc:
                errors.append(f"{method_name} {url}: {exc}")
    sync_data["error"] = " | ".join(errors)

def current_epoch_ms():
    if sync_data["server_epoch_ms"] is None:
        return None
    return sync_data["server_epoch_ms"] + (time.monotonic()*1000 - sync_data["local_monotonic_ms"])

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/time"):
            sync_with_uzex()
            payload = {"epoch_ms": current_epoch_ms(), "source": sync_data.get("source"),
                       "last_sync_utc": sync_data.get("last_sync_utc"),
                       "round_trip_ms": sync_data.get("round_trip_ms"),
                       "method": sync_data.get("method"), "error": sync_data.get("error")}
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200 if payload["epoch_ms"] else 502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        super().do_GET()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Open http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
