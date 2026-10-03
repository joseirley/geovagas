"""
Módulo de raspagem e geocodificação de vagas do GO BH para a plataforma GeoVagas.
"""

import os
import json
import time
import re
import urllib.request
import urllib.parse
import ssl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
VAGAS_FILE = os.path.join(DATA_DIR, "vagas.json")
GEOCACHE_FILE = os.path.join(DATA_DIR, "geocache.json")

os.makedirs(DATA_DIR, exist_ok=True)

# SSL context permissivo
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def load_geocache():
    if os.path.exists(GEOCACHE_FILE):
        try:
            with open(GEOCACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_geocache(cache):
    with open(GEOCACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def geocode_address(address_str, cache):
    """
    Localiza latitude e longitude para o endereço de trabalho.
    Usa cache para evitar chamadas de rede repetidas.
    """
    if not address_str:
        return -19.9208, -43.9378 # Praça Sete (Centro de BH como fallback)
    
    clean_addr = address_str.strip().upper()
    if clean_addr in cache:
        return cache[clean_addr]["lat"], cache[clean_addr]["lon"]
    
    # Tentativas de busca do mais específico ao mais geral
    queries = [
        f"{clean_addr}, Belo Horizonte, MG, Brasil",
    ]
    
    # Se tem traço ou vírgula, tenta logradouro + número
    if "-" in clean_addr:
        parts = clean_addr.split("-")
        queries.append(f"{parts[0].strip()}, Belo Horizonte, MG, Brasil")
    
    headers = {"User-Agent": "GeoVagas-App/1.0 (contato@geovagas.com.br)"}
    
    for q in queries:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(q)}&limit=1"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    cache[clean_addr] = {"lat": lat, "lon": lon, "matched": q}
                    save_geocache(cache)
                    time.sleep(1.0) # Respeito ao limite do Nominatim
                    return lat, lon
        except Exception as e:
            print(f"Erro ao geocodificar '{q}': {e}")
            time.sleep(0.5)

    # Fallback padrão caso não encontre nas buscas do OpenStreetMap
    # Centro de Belo Horizonte (Praça Sete / Afonso Pena) com leve variação aleatória para não sobrepor
    default_lat, default_lon = -19.9208, -43.9378
    cache[clean_addr] = {"lat": default_lat, "lon": default_lon, "fallback": True}
    save_geocache(cache)
    return default_lat, default_lon

def scrape_vagas(progress_callback=None):
    """
    Coleta todas as vagas ativas do GO BH e seus detalhes completos.
    """
    cache = load_geocache()
    vagas_processadas = []
    
    url_base = "https://gobh-api.pbh.gov.br/api/vagas/?page=1&take=100&situacao=ABERTA"
    req = urllib.request.Request(url_base, headers={"User-Agent": "Mozilla/5.0"})
    
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
    except Exception as e:
        print(f"Erro ao acessar API de vagas: {e}")
        # Se falhar e existir cache local anterior, usa ele
        if os.path.exists(VAGAS_FILE):
            with open(VAGAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    total = len(results)
    print(f"Encontradas {total} vagas abertas no GO BH. Coletando detalhes e geolocalização...")

    for idx, item in enumerate(results):
        vid = item.get("id")
        detalhe_url = f"https://gobh-api.pbh.gov.br/api/vagas/{vid}"
        
        try:
            req_d = urllib.request.Request(detalhe_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_d, context=ssl_context, timeout=8) as r_det:
                detail = json.loads(r_det.read().decode("utf-8"))
        except Exception as e:
            print(f"Erro ao buscar detalhes da vaga {vid}: {e}")
            detail = item

        dados = detail.get("dados", {})
        ocupacao = dados.get("ocupacao", {})
        requisitos = dados.get("requisitos", {})
        horario_local = dados.get("horario_local_trabalho", {})
        info_fin = dados.get("informacoes_financeiras", {})
        empregador = dados.get("empregador", {})

        # Extração e normalização dos campos
        titulo = ocupacao.get("ocupacao_descricao") or ocupacao.get("descricao") or f"Vaga #{vid}"
        # Limpar títulos muito longos ou com quebras de linha
        titulo = titulo.strip().replace("\r\n", " ").replace("\n", " ")
        
        empresa = empregador.get("nome_fantasia") or "Prefeitura de Belo Horizonte"
        
        contratacao = dados.get("contratacao") or "Não informado"
        escolaridade = requisitos.get("escolaridade") or "Não informado"
        
        horario = horario_local.get("horario_trabalho") or "Não informado"
        if horario.strip().lower() == "indiferente":
            horario = "Indiferente / A combinar"
        elif horario.strip().lower() == "manha" or horario.strip().lower() == "manhã":
            horario = "Manhã"
        elif horario.strip().lower() == "tarde":
            horario = "Tarde"
            
        carga_horaria_raw = horario_local.get("carga_horaria")
        if isinstance(carga_horaria_raw, dict):
            carga_horaria = carga_horaria_raw.get("nome") or str(carga_horaria_raw.get("hora_semanal", "")) + " horas semanais"
        elif isinstance(carga_horaria_raw, str) and carga_horaria_raw.strip():
            carga_horaria = carga_horaria_raw.strip()
        else:
            carga_horaria = "Não informado"

        local_trabalho = horario_local.get("municipio_local_trabalho") or "Belo Horizonte - MG"
        
        salario = info_fin.get("salario")
        if salario:
            try:
                sal_float = float(salario)
                salario_fmt = f"R$ {sal_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except ValueError:
                salario_fmt = f"R$ {salario}"
        else:
            salario_fmt = "A combinar"

        beneficios = info_fin.get("outros_incentivos") or ""

        # Geocodificação
        lat, lon = geocode_address(local_trabalho, cache)

        vaga_dict = {
            "id": vid,
            "codigo": item.get("codigo", vid),
            "titulo": titulo,
            "empresa": empresa,
            "contratacao": contratacao,
            "escolaridade": escolaridade,
            "horario": horario,
            "carga_horaria": carga_horaria,
            "local_trabalho": local_trabalho,
            "salario": salario_fmt,
            "beneficios": beneficios,
            "descricao_detalhada": ocupacao.get("descricao", ""),
            "requisitos_detalhes": requisitos.get("descricao", ""),
            "data_cadastro": dados.get("data_cadastro", ""),
            "link_gobh": f"https://gobh.pbh.gov.br/go/detalheOportunidade/{vid}",
            "lat": lat,
            "lon": lon
        }

        vagas_processadas.append(vaga_dict)
        if progress_callback:
            progress_callback(idx + 1, total)

    # Salva arquivo consolidado
    with open(VAGAS_FILE, "w", encoding="utf-8") as f:
        json.dump(vagas_processadas, f, ensure_ascii=False, indent=2)

    print(f"Raspagem concluída! {len(vagas_processadas)} vagas salvas em {VAGAS_FILE}")
    return vagas_processadas

def get_vagas_cached():
    if os.path.exists(VAGAS_FILE):
        try:
            with open(VAGAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return scrape_vagas()

if __name__ == "__main__":
    scrape_vagas()
