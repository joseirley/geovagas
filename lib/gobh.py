"""Fetch and normalize open GO BH opportunities for Vercel functions."""

import json
import os
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO_CACHE = os.path.join(ROOT, "data", "geocache.json")
SSL_CONTEXT = ssl.create_default_context()
USER_AGENT = "GeoVagas/1.0 (consulta de oportunidades públicas)"


def _json_get(url, timeout=12):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
        return json.loads(response.read().decode("utf-8"))


def _geocache():
    try:
        with open(GEO_CACHE, "r", encoding="utf-8") as source:
            return json.load(source)
    except (OSError, ValueError):
        return {}


def _coordinates(address, cache):
    item = cache.get((address or "").strip().upper())
    if not item:
        return None, None
    if item.get("fallback"):
        return None, None
    return item.get("lat"), item.get("lon")


def _text(value, default="Não informado"):
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get("nome") or value.get("descricao") or default
    return str(value).strip() or default


def _normalize(item, detail, cache):
    data = detail.get("dados") or item.get("dados") or {}
    ocupacao = data.get("ocupacao") or {}
    requisitos = data.get("requisitos") or {}
    horario_local = data.get("horario_local_trabalho") or {}
    info = data.get("informacoes_financeiras") or {}
    empregador = data.get("empregador") or {}
    vid = item.get("id") or detail.get("id")

    titulo = ocupacao.get("ocupacao_descricao") or ocupacao.get("descricao") or f"Vaga #{vid}"
    titulo = re.sub(r"\s+", " ", str(titulo)).strip()
    horario = _text(horario_local.get("horario_trabalho"))
    horario = {"manha": "Manhã", "manhã": "Manhã", "tarde": "Tarde", "indiferente": "Indiferente / A combinar"}.get(horario.casefold(), horario)
    carga_raw = horario_local.get("carga_horaria")
    if isinstance(carga_raw, dict):
        carga = carga_raw.get("nome") or (str(carga_raw.get("hora_semanal")) + " horas semanais" if carga_raw.get("hora_semanal") else "Não informado")
    else:
        carga = _text(carga_raw)
    salario = info.get("salario")
    try:
        salario_text = ("R$ {:,.2f}".format(float(salario))).replace(",", "X").replace(".", ",").replace("X", ".") if salario else "A combinar"
    except (ValueError, TypeError):
        salario_text = "R$ " + str(salario) if salario else "A combinar"
    local = _text(horario_local.get("municipio_local_trabalho"), "Belo Horizonte - MG")
    lat, lon = _coordinates(local, cache)
    return {
        "id": vid, "codigo": item.get("codigo", vid), "titulo": titulo,
        "empresa": _text(empregador.get("nome_fantasia"), "Prefeitura de Belo Horizonte"),
        "contratacao": _text(data.get("contratacao")), "escolaridade": _text(requisitos.get("escolaridade")),
        "horario": horario, "carga_horaria": carga, "local_trabalho": local, "salario": salario_text,
        "beneficios": info.get("outros_incentivos") or "", "descricao_detalhada": ocupacao.get("descricao", ""),
        "requisitos_detalhes": requisitos.get("descricao", ""), "data_cadastro": data.get("data_cadastro", ""),
        "link_gobh": f"https://gobh.pbh.gov.br/go/detalheOportunidade/{vid}", "lat": lat, "lon": lon,
    }


def fetch_vagas():
    """Read current open opportunities and enrich them with their detail records."""
    listing = _json_get("https://gobh-api.pbh.gov.br/api/vagas/?page=1&take=100&situacao=ABERTA")
    items = listing.get("results", [])
    cache = _geocache()

    def fetch_detail(item):
        try:
            detail = _json_get(f"https://gobh-api.pbh.gov.br/api/vagas/{item.get('id')}")
        except Exception:
            detail = item
        return _normalize(item, detail, cache)

    with ThreadPoolExecutor(max_workers=12) as pool:
        return list(pool.map(fetch_detail, items))
