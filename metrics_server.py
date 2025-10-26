#!/usr/bin/env python3
"""C3 metrics server stub.

This lightweight HTTP server serves two endpoints for health and metrics.
It reads a `baseline_summary.json` or `obfuscated_summary.json` file generated
by the demo and exposes its contents (with an added `uptime_s` field) via JSON.

Endpoints:
  /healthz   → returns {"ok": true, "uptime_s": <seconds>}
  /metrics   → returns the summary with an added `uptime_s` field

Usage:
    python3 metrics_server.py --baseline path/to/baseline_summary.json --port 18022
    # or
    python3 metrics_server.py --obfuscated path/to/obfuscated_summary.json --port 18022

Stop the server with Ctrl+C.
"""

import argparse
import json
import time
import http.server
import socketserver
from typing import Any, Dict


class MetricsHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler serving health and metrics endpoints."""
    start_time: float = time.time()
    summary: Dict[str, Any] = {}

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split('?', 1)[0]
        uptime = int(time.time() - MetricsHandler.start_time)
        if path == '/healthz':
            self._send_json({'ok': True, 'uptime_s': uptime})
        elif path == '/metrics':
            metrics = MetricsHandler.summary.copy()
            metrics['uptime_s'] = uptime
            self._send_json(metrics)
        else:
            self._send_json({'error': 'not found'}, status=404)


def run_server(summary: Dict[str, Any], port: int) -> None:
    """Start the HTTP server on the given port with the provided summary dict."""
    MetricsHandler.summary = summary
    MetricsHandler.start_time = time.time()
    with socketserver.TCPServer(('', port), MetricsHandler) as httpd:
        print(f"C3 metrics server listening on port {port}")
        httpd.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description='C3 metrics server stub')
    parser.add_argument('--baseline', help='Path to baseline_summary.json')
    parser.add_argument('--obfuscated', help='Path to obfuscated_summary.json')
    parser.add_argument('--port', type=int, default=18022, help='Port to serve on (default: 18022)')
    args = parser.parse_args()

    summary = {}
    summary_path = args.obfuscated or args.baseline
    if summary_path:
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary = json.load(f)
        except Exception:
            pass
    run_server(summary, args.port)


if __name__ == '__main__':
    main()
