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
import unicodedata
import re

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
        return None, None
    
    clean_addr = address_str.strip().upper()
    cached = cache.get(clean_addr)
    if cached and not cached.get("fallback"):
        return cached["lat"], cached["lon"]
    
    # The source address already contains its city. Avoid appending BH twice,
    # which caused Nominatim to miss valid addresses and cache the city center.
    place = clean_addr.rsplit(",", 1)[-1].strip()
    address_part = clean_addr.rsplit(",", 1)[0].strip() if "," in clean_addr else clean_addr
    city = place or "BELO HORIZONTE"
    queries = [
        f"{address_part}, {city}, Minas Gerais, Brasil",
        f"{address_part.split(' - ', 1)[0]}, {city}, Minas Gerais, Brasil",
    ]
    
    headers = {"User-Agent": "GeoVagas-App/1.0 (contato@geovagas.com.br)"}
    
    for q in dict.fromkeys(queries):
        params = urllib.parse.urlencode({"format": "jsonv2", "addressdetails": 1, "q": q, "limit": 3, "countrycodes": "br"})
        url = f"https://nominatim.openstreetmap.org/search?{params}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data and len(data) > 0:
                    for result in data:
                        result_address = result.get("address", {})
                        result_city = (result_address.get("city") or result_address.get("town") or result_address.get("municipality") or "").casefold()
                        if city.casefold() not in result_city and city.casefold() not in result.get("display_name", "").casefold():
                            continue
                        lat, lon = float(result["lat"]), float(result["lon"])
                        cache[clean_addr] = {"lat": lat, "lon": lon, "matched": q, "source": "nominatim"}
                        save_geocache(cache)
                        time.sleep(1.1) # Nominatim public usage limit
                        return lat, lon
        except Exception as e:
            print(f"Erro ao geocodificar '{q}': {e}")
            time.sleep(0.5)

    # Photon can resolve street names absent from Nominatim's address index.
    # Accept only results in the requested municipality and matching street.
    try:
        params = urllib.parse.urlencode({"q": address_str + ", Minas Gerais, Brasil", "limit": 10, "lang": "en"})
        req = urllib.request.Request(f"https://photon.komoot.io/api/?{params}", headers=headers)
        with urllib.request.urlopen(req, context=ssl_context, timeout=8) as resp:
            features = json.loads(resp.read().decode("utf-8")).get("features", [])
        wanted_street = address_part.split(",", 1)[0].split(" - ", 1)[0].strip()
        wanted_street = re.sub(r",?\s*\d+\s*$", "", wanted_street)
        norm = lambda value: " ".join("".join(c for c in unicodedata.normalize("NFKD", str(value).casefold()) if not unicodedata.combining(c)).split())
        wanted_words = set(norm(wanted_street).split())
        candidates = []
        for feature in features:
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [])
            result_city = props.get("city", "")
            result_street = props.get("street") or props.get("name") or ""
            result_words = set(norm(result_street).split())
            overlap = len(wanted_words & result_words) / max(1, len(wanted_words))
            if len(coords) < 2 or norm(city) not in norm(result_city) or props.get("countrycode", "").upper() != "BR" or overlap < 0.5:
                continue
            score = overlap
            if props.get("type") in {"street", "house"}:
                score += 0.2
            requested_number = re.search(r"\b(\d+)\b", address_part)
            if requested_number and props.get("housenumber") == requested_number.group(1):
                score += 0.5
            candidates.append((score, (float(coords[1]), float(coords[0])), props))
        if candidates:
            _, (lat, lon), props = max(candidates, key=lambda candidate: candidate[0])
            cache[clean_addr] = {"lat": lat, "lon": lon, "matched": props.get("name") or props.get("street"), "source": "photon"}
            save_geocache(cache)
            return lat, lon
    except Exception as e:
        print(f"Erro no geocoder alternativo para '{address_str}': {e}")

    # Keep unresolved locations out of the map instead of misplacing them at Praça Sete.
    cache[clean_addr] = {"lat": None, "lon": None, "fallback": True}
    save_geocache(cache)
    return None, None

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
