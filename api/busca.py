"""Independent on-demand search endpoint for LinkedIn, Indeed and Glassdoor."""

import json
import logging
from urllib.parse import parse_qs, urlsplit

from http.server import BaseHTTPRequestHandler

from lib.external_jobs import search_jobs


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            query = parse_qs(urlsplit(self.path).query)
            result = search_jobs(
                query.get("site", [""])[0],
                query.get("search_term", [""])[0],
                query.get("location", [""])[0],
                query.get("fetch_description", ["false"])[0].lower() == "true",
                offset=query.get("offset", ["0"])[0],
            )
            self._respond(200, result)
        except ValueError as exc:
            self._respond(400, {"error": str(exc)})
        except Exception:
            logging.exception("Falha inesperada na consulta de vagas")
            self._respond(502, {
                "error": "Não foi possível consultar esta plataforma no momento.",
            })

    def _respond(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
