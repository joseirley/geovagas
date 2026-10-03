"""
Servidor HTTP leve para o GeoVagas em HTML/JS com endpoints de API para vagas e sincronização.
Não depende de pacotes externos, usando a biblioteca padrão do Python.
"""

import http.server
import socketserver
import os
import json
import webbrowser
import scraper

PORT = 8501
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "vagas.json")

class GeoVagasHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # Rota principal
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        # Rota de dados das vagas
        if self.path == "/api/vagas":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            vagas = scraper.get_vagas_cached()
            self.wfile.write(json.dumps(vagas, ensure_ascii=False).encode("utf-8"))
            return

        # Demais arquivos estáticos (static/, logo/, etc.)
        return super().do_GET()

    def do_POST(self):
        # Sincronização forçada com o GO BH
        if self.path == "/api/sync":
            try:
                vagas = scraper.scrape_vagas()
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "total": len(vagas)}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def run_server():
    # Garantir que os dados existem antes de abrir
    if not os.path.exists(DATA_FILE):
        print("Coletando vagas iniciais da Prefeitura de Belo Horizonte...")
        scraper.scrape_vagas()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), GeoVagasHandler) as httpd:
        print("========================================================")
        print("       GEOVAGAS INICIADO COM SUCESSO!                  ")
        print("========================================================")
        print(f"  URL Local: http://localhost:{PORT}")
        print("  Pressione Ctrl+C para encerrar o servidor.")
        print("========================================================")
        
        # Abrir navegador automaticamente
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except Exception:
            pass

        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
