"""JobSpy adapter, normalization, date validation and short-lived query cache."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import os
import re
import threading
import time as time_module
import unicodedata
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


HOURS_OLD = 144
RESULTS_WANTED = 100
CACHE_TTL_SECONDS = 3600
SUPPORTED_SITES = {"linkedin", "indeed", "glassdoor"}
SITE_CONFIG = {
    "linkedin": {"country_indeed": None},
    "indeed": {"country_indeed": "Brazil"},
    "glassdoor": {"country_indeed": "Brazil"},
}
_CACHE = {}
_CACHE_LOCK = threading.Lock()
_GEO_CACHE = {}
_GEOCODE_LOCK = threading.Lock()
_LAST_GEOCODE_AT = 0.0
_GEO_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "external_geocache.json")
_STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}
def _fold(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in value if not unicodedata.combining(char)).casefold().strip()


_STATE_CODES = {_fold(v): k for k, v in _STATE_NAMES.items()}


def normalize_state(value):
    """Return a Brazilian state abbreviation only for recognized state values."""
    raw = _fold(value)
    for part in re.split(r"[,;/|]", raw):
        part = re.sub(r"^(estado de|estado|state of|state)\s+", "", part.strip())
        part = re.sub(r"\s+(brasil|brazil|br)$", "", part).strip()
        code = re.sub(r"[^a-z]", "", part).upper()
        if code in _STATE_NAMES:
            return code
        if part in _STATE_CODES:
            return _STATE_CODES[part]
    for code, name in _STATE_NAMES.items():
        if re.search(rf"(?:^|\W){re.escape(_fold(name))}(?:\W|$)", raw):
            return code
    return None


def classify_date(value, now=None):
    """Return (status, UTC timestamp). Date-only values are confirmed only when
    their entire UTC calendar day falls within the 144-hour window.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    if value is None or str(value).strip() == "":
        return "unconfirmed", None

    date_only = False
    parsed = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min, tzinfo=timezone.utc)
        date_only = True
    else:
        raw = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            date_only = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                return "unconfirmed", None
    if parsed is None:
        return "unconfirmed", None
    if parsed.tzinfo is None:
        if date_only:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            # Naive timestamps have no explicit timezone and cannot be verified.
            return "unconfirmed", None
    parsed = parsed.astimezone(timezone.utc)
    if parsed > now:
        return "future", parsed.isoformat()
    cutoff = now - timedelta(hours=HOURS_OLD)
    if date_only:
        return ("recent", parsed.isoformat()) if parsed >= cutoff else ("unconfirmed", parsed.isoformat())
    if parsed >= cutoff:
        return "recent", parsed.isoformat()
    return "old", parsed.isoformat()


def _as_text(value):
    if value is None:
        return ""
    try:
        # pandas.NA / NaN
        if value != value:
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _safe_url(value):
    raw = _as_text(value)
    try:
        parts = urlsplit(raw)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return ""
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))
    except ValueError:
        return ""


def _normalize_record(row, site, now):
    normalized_columns = {str(key).casefold(): value for key, value in row.items()}
    get = normalized_columns.get
    raw_date = get("date_posted")
    date_status, published_utc = classify_date(raw_date, now)
    city = _as_text(get("city"))
    state = normalize_state(get("state"))
    country = _as_text(get("country"))
    location = _as_text(get("location"))
    parts = [part.strip() for part in re.split(r"[,;/|]", location) if part.strip()]
    if not state:
        for part in parts:
            state = normalize_state(part)
            if state:
                break
    if not city and parts:
        candidates = [part for part in parts if not normalize_state(part) and _fold(part) not in {"brasil", "brazil", "br", "remote", "remoto"}]
        if candidates and (state or len(candidates) > 1):
            city = candidates[0]
    if not location:
        location = ", ".join(part for part in (city, state, country) if part)
    return {
        "title": _as_text(get("title")) or "Cargo não informado",
        "company": _as_text(get("company")) or "Empresa não informada",
        "location": location,
        "city": city,
        "state": state or "",
        "country": country,
        "date_posted": raw_date.isoformat() if isinstance(raw_date, (date, datetime)) else _as_text(raw_date),
        "date_posted_utc": published_utc,
        "job_url": _safe_url(get("job_url")),
        "job_url_direct": _safe_url(get("job_url_direct")),
        "source": site,
        "date_status": date_status,
        "latitude": None,
        "longitude": None,
    }


def _geocode_municipality(city, state):
    """Resolve a municipality center with state/country constraints; cache is
    request-process local and results are rejected unless the returned city and
    state match the requested municipality.
    """
    if not city or not state:
        return None, None
    global _LAST_GEOCODE_AT
    key = (_fold(city), state)
    with _GEOCODE_LOCK:
        if key in _GEO_CACHE:
            return _GEO_CACHE[key]
        try:
            with open(_GEO_CACHE_FILE, "r", encoding="utf-8") as cache_file:
                persistent = json.load(cache_file)
            cached = persistent.get(f"{key[0]}|{state}")
            if cached:
                coordinates = (float(cached[0]), float(cached[1]))
                _GEO_CACHE[key] = coordinates
                return coordinates
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            persistent = {}
        # Respect Nominatim's public service rate limit across concurrent requests.
        wait = 1.1 - (time_module.monotonic() - _LAST_GEOCODE_AT)
        if wait > 0:
            time_module.sleep(wait)
        _LAST_GEOCODE_AT = time_module.monotonic()
        query = f"{city}, {_STATE_NAMES[state]}, Brazil"
        request = Request(
            "https://nominatim.openstreetmap.org/search?" +
            urlencode({"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 3, "countrycodes": "br"}),
            headers={"User-Agent": "GeoVagas/1.0 (consulta de oportunidades públicas)"},
        )
        coordinates = None, None
        try:
            with urlopen(request, timeout=3) as response:
                results = json.loads(response.read().decode("utf-8"))
            wanted_city = _fold(city)
            wanted_state = state
            for result in results:
                address = result.get("address", {})
                returned_names = {
                    _fold(address.get(name, "")) for name in
                    ("city", "town", "municipality", "village", "county")
                }
                if wanted_city not in returned_names or normalize_state(address.get("state", "")) != wanted_state:
                    continue
                lat, lon = float(result["lat"]), float(result["lon"])
                if -34 <= lat <= 6 and -74 <= lon <= -34:
                    coordinates = lat, lon
                    break
        except Exception:
            pass
        _GEO_CACHE[key] = coordinates
        if coordinates[0] is not None:
            persistent[f"{key[0]}|{state}"] = coordinates
            try:
                os.makedirs(os.path.dirname(_GEO_CACHE_FILE), exist_ok=True)
                temp_file = _GEO_CACHE_FILE + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as cache_file:
                    json.dump(persistent, cache_file, ensure_ascii=False)
                os.replace(temp_file, _GEO_CACHE_FILE)
            except OSError:
                pass
        return coordinates


def _query_cache_key(site, term, location, fetch_description):
    return (site, _fold(term), _fold(location), HOURS_OLD, RESULTS_WANTED, bool(fetch_description))


def search_jobs(site, search_term, location, fetch_description=False, now=None):
    """Query exactly one JobSpy platform, validate, geocode, and cache output."""
    site = str(site or "").casefold().strip()
    if site not in SUPPORTED_SITES:
        raise ValueError("Plataforma inválida. Use linkedin, indeed ou glassdoor.")
    term, location = str(search_term or "").strip(), str(location or "").strip()
    if not term:
        raise ValueError("Informe um cargo ou palavra-chave para pesquisar.")
    if len(term) > 160 or len(location) > 160:
        raise ValueError("Os campos de busca devem ter no máximo 160 caracteres.")
    key = _query_cache_key(site, term, location, fetch_description)
    current_time = time_module.time()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and current_time - cached[0] < CACHE_TTL_SECONDS:
            return dict(cached[1], cached=True)

    from jobspy import scrape_jobs

    kwargs = {
        "site_name": [site], "search_term": term, "location": location or "Brazil",
        "hours_old": HOURS_OLD, "results_wanted": RESULTS_WANTED,
        "fetch_description": bool(fetch_description), "verbose": 0,
    }
    if SITE_CONFIG[site]["country_indeed"]:
        kwargs["country_indeed"] = SITE_CONFIG[site]["country_indeed"]
    frame = scrape_jobs(**kwargs)
    collected_at = (now or datetime.now(timezone.utc))
    if collected_at.tzinfo is None:
        collected_at = collected_at.replace(tzinfo=timezone.utc)
    collected_at = collected_at.astimezone(timezone.utc)
    rows = frame.to_dict(orient="records") if hasattr(frame, "to_dict") else list(frame or [])
    normalized = [_normalize_record(row, site, collected_at) for row in rows[:RESULTS_WANTED]]

    # Deduplicate only by validated normalized ad URL; retain same-title postings.
    unique, seen_urls = [], set()
    for job in normalized:
        url = job["job_url"]
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique.append(job)
    recent = sorted((job for job in unique if job["date_status"] == "recent"), key=lambda job: job["date_posted_utc"], reverse=True)
    unconfirmed = [job for job in unique if job["date_status"] == "unconfirmed"]
    locations = {}
    # Only geocode records visible by default. This avoids waiting for cities
    # belonging to unconfirmed postings; those remain available in the table.
    map_candidates = recent
    city_counts = {}
    for job in map_candidates:
        if job["city"] and job["state"]:
            key_loc = (_fold(job["city"]), job["state"])
            city_counts[key_loc] = city_counts.get(key_loc, 0) + 1
    # Geocode every distinct municipality so all confirmed locations can be
    # represented by one aggregate circle. Coordinates are cached per process.
    resolved_keys = sorted(city_counts, key=lambda item: city_counts[item], reverse=True)
    for key_loc in resolved_keys:
        sample = next(job for job in map_candidates if (_fold(job["city"]), job["state"]) == key_loc)
        locations[key_loc] = _geocode_municipality(sample["city"], sample["state"])
    for key_loc in city_counts:
        locations.setdefault(key_loc, (None, None))
    for job in map_candidates:
        key_loc = (_fold(job["city"]), job["state"]) if job["city"] and job["state"] else None
        if key_loc:
            job["latitude"], job["longitude"] = locations[key_loc]

    status = "sem_resultados" if not unique else "concluida"
    payload = {
        "source": site, "status": status, "collected_count": len(unique),
        "recent_count": len(recent), "unconfirmed_count": len(unconfirmed),
        "recent_jobs": recent[:RESULTS_WANTED], "unconfirmed_jobs": unconfirmed[:RESULTS_WANTED],
        "map_unlocated_count": sum(job["latitude"] is None for job in recent),
        "collected_at": collected_at.isoformat(), "hours_old": HOURS_OLD,
        "results_wanted": RESULTS_WANTED, "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "cached": False,
    }
    with _CACHE_LOCK:
        _CACHE[key] = (current_time, payload)
        # Bound process memory if many distinct searches are submitted.
        if len(_CACHE) > 64:
            oldest = min(_CACHE, key=lambda entry: _CACHE[entry][0])
            _CACHE.pop(oldest, None)
    return payload
