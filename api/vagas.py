import json
from http.server import BaseHTTPRequestHandler

from _gobh import fetch_vagas


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            vagas = fetch_vagas()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "s-maxage=300, stale-while-revalidate=600")
            self.end_headers()
            self.wfile.write(json.dumps(vagas, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Não foi possível consultar as vagas do GO BH.", "detail": str(exc)}, ensure_ascii=False).encode("utf-8"))
