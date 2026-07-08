from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
from threading import Event, Thread
from typing import Sequence

from .analyser import AnalysisError, analyze_database
from .reporting import report_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="database-analyser-web",
        description="Serve a simple web overview for a SQL dump or database file.",
    )
    parser.add_argument("database_path", help="Path to the .sql dump or database file")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    public_dir = Path(__file__).resolve().parents[2] / "public"
    report_ready = Event()
    report_payload: dict[str, object] = {"ready": False}

    def load_report() -> None:
        try:
            report = analyze_database(args.database_path)
        except AnalysisError as exc:
            report_payload.clear()
            report_payload.update({"ready": False, "error": str(exc)})
        else:
            report_payload.clear()
            report_payload.update({"ready": True, "report": report_to_dict(report)})
        finally:
            report_ready.set()

    Thread(target=load_report, daemon=True).start()

    handler = partial(_build_handler, public_dir=public_dir, report_state=report_payload, report_ready=report_ready)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Serving database overview at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


def _build_handler(*args, public_dir: Path, report_state: dict[str, object], report_ready: Event, **kwargs):
    class ReportHandler(SimpleHTTPRequestHandler):
        def __init__(self, *handler_args, **handler_kwargs):
            super().__init__(*handler_args, directory=str(public_dir), **handler_kwargs)

        def do_GET(self) -> None:
            if self.path.rstrip("/") == "/api/report":
                if not report_ready.is_set():
                    payload = json.dumps({"ready": False}).encode("utf-8")
                    self.send_response(202)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if report_state.get("error"):
                    payload = json.dumps({"ready": False, "error": report_state["error"]}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                payload = json.dumps(report_state["report"]).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return

            if self.path == "/":
                self.path = "/index.html"

            super().do_GET()

    return ReportHandler(*args, **kwargs)


if __name__ == "__main__":
    raise SystemExit(main())