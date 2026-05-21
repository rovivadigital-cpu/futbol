import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import time
import json
import random
from curl_cffi import requests as cffi_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===================== CONFIG =====================
CARPETA_SALIDA = "datos"
ARCHIVO_FUTBOL = os.path.join(CARPETA_SALIDA, "futbol_historico.csv")
ARCHIVO_COOKIES = os.path.join(CARPETA_SALIDA, "cookies.txt")
GUARDAR_CADA_N_PARTIDOS = 10
PAUSA_ENTRE_REQUESTS = 0.9
ESTADOS_FINALIZADOS = {"finished", "completed", "ended", "closed", "final", "done"}
CHROME_VERSIONS = ["chrome136", "chrome131", "chrome124"]

LIGAS_FUTBOL = {
    "CONMEBOL Libertadores":         87760,
    "UEFA Champions League":         76953,
    "Club World Championship":       69619,
    "UEFA Europa League":            76984,
    "UEFA Conference League":        76960,
    "Premier League":                76986,
    "Championship":                  77347,
    "League One":                    77352,
    "La Liga":                       77559,
    "LaLiga 2":                      77558,
    "Bundesliga":                    77333,
    "2. Bundesliga":                 77354,
    "Serie A":                       76457,
    "Serie B":                       79502,
    "Ligue 1":                       77356,
    "Ligue 2":                       77357,
    "MLS":                           86668,
    "NWSL":                          88711,
    "CONMEBOL Sudamericana":         87770,
    "Saudi Pro League":              80443,
    "Liga Profesional Argentina":    87913,
    "Primera Nacional Argentina":    87940,
    "A-League Men":                  82603,
    "NPL Capital Football":          90775,
    "Austrian Bundesliga":           77382,
    "Belgian Pro League":            77040,
    "Bolivian División Profesional": 92509,
    "Brasileirao Serie A":           87678,
    "Brasileirao Serie B":           89840,
    "Bulgarian Parva Liga":          76882,
    "Czech 1. Liga":                 77019,
    "Chilean Primera División":      88493,
    "Chinese Super League":          90049,
    "Colombia Primera A Apertura":   88503,
    "Colombia Primera A Clausura":   77825,
    "Colombia Primera B":            89001,
    "K League 1":                    88606,
    "HNL Croatia":                   76980,
    "Danish Superliga":              76491,
    "Egyptian Premier League":       79317,
    "Scottish Premiership":          77128,
    "Scottish Championship":         77037,
    "Slovenian PrvaLiga":            77283,
    "Estonian Premium Liiga":        89137,
    "Finnish Veikkausliiga":         87930,
    "Greek Super League":            78175,
    "Indonesian Liga 1":             78590,
    "J1 League":                     87931,
    "J2 League":                     87932,
    "Latvian Virsliga":              89428,
    "Liga MX Apertura":              76500,
    "Liga MX Clausura":              87699,
    "Norwegian Eliteserien":         87809,
    "Eredivisie":                    77012,
    "Eerste Divisie":                77156,
    "Ekstraklasa":                   76477,
    "Romanian Superliga":            77312,
    "South African Premiership":     79701,
    "Allsvenskan":                   87925,
    "Superettan":                    87924,
    "Turkish Süper Lig":             77805,
    "Ukrainian Premier League":      77625,
    "Swiss Super League":            77152,
}

LIGAS_IDS_SET = set(LIGAS_FUTBOL.values())

HEADERS_BASE = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,es-CO;q=0.5,ar;q=0.4",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/football",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0",
    "sec-ch-ua": '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "priority": "u=1, i",
    "Connection": "keep-alive",
}

# ===================== SESIÓN Y API =====================

def _cargar_cookies() -> dict:
    if not os.path.exists(ARCHIVO_COOKIES):
        return {}
    try:
        with open(ARCHIVO_COOKIES, "r", encoding="utf-8") as f:
            cont = f.read().strip()
        if cont.startswith("["):
            data = json.loads(cont)
            return {item.get("name"): item.get("value") for item in data if item.get("name")}
        else:
            cookies = {}
            for par in cont.split(";"):
                if "=" in par:
                    k, v = par.strip().split("=", 1)
                    cookies[k] = v
            return cookies
    except Exception as e:
        logging.error(f"Error cookies: {e}")
        return {}

def _nueva_sesion() -> cffi_requests.Session:
    impersonate = random.choice(CHROME_VERSIONS)
    s = cffi_requests.Session(impersonate=impersonate)
    cookies = _cargar_cookies()
    if cookies:
        s.cookies.update(cookies)
    s.headers.update(HEADERS_BASE)
    return s

SESSION = _nueva_sesion()
_403_consecutivos = 0

def api_get(url: str, intentos: int = 4) -> dict:
    global SESSION, _403_consecutivos
    if "/event/" in url:
        event_part = url.split("/event/")[1].split("/")[0]
        SESSION.headers.update({"Referer": f"https://www.sofascore.com/football/match/{event_part}"})
    else:
        SESSION.headers.update({"Referer": "https://www.sofascore.com/football"})

    for i in range(1, intentos + 1):
        try:
            time.sleep(PAUSA_ENTRE_REQUESTS + random.uniform(0.3, 0.9))
            r = SESSION.get(url, timeout=30)
            if r.status_code == 200:
                _403_consecutivos = 0
                return r.json()
            elif r.status_code == 403:
                _403_consecutivos += 1
                if _403_consecutivos >= 3:
                    time.sleep(120 * i)
                    SESSION = _nueva_sesion()
                    _403_consecutivos = 0
                else:
                    time.sleep(20 * i)
            elif r.status_code == 429:
                time.sleep(90 * i)
            elif r.status_code == 404:
                return {}
            else:
                time.sleep(10 * i)
        except Exception as e:
            logging.error(f"Error en {url}: {e}")
            time.sleep(10 * i)
    return {}

# ===================== UTILIDADES =====================

def formatear_valor(val):
    if isinstance(val, dict):
        v = val.get("value", 0)
        t = val.get("total", 0)
        return f"{v}/{t} ({(v/t)*100:.0f}%)" if t > 0 else f"{v}/{t}"
    return val

def parsear_estadisticas(stats_data: dict) -> dict:
    resultado = {}
    for periodo in stats_data.get("statistics", []):
        p_name = periodo.get("period", "ALL").upper()
        for grupo in periodo.get("groups", []):
            for item in grupo.get("statisticsItems", []):
                nombre = item.get("name", "").replace(" ", "_").replace(".", "").lower()
                resultado[f"{p_name}_{nombre}_home"] = formatear_valor(item.get("home"))
                resultado[f"{p_name}_{nombre}_away"] = formatear_valor(item.get("away"))
    return resultado

def parsear_goles_detallados(incidents_data: dict) -> dict:
    resultado = {
        "home_scorers": "",
        "away_scorers": "",
        "home_own_goals": "",
        "away_own_goals": "",
        "home_red_cards_players": "",
        "away_red_cards_players": "",
    }
    if not incidents_data:
        return resultado

    home_scorers, away_scorers = [], []
    home_og, away_og = [], []
    home_red, away_red = [], []

    for inc in incidents_data.get("incidents", []):
        inc_type = inc.get("incidentType", "").lower()
        team = inc.get("isHome")
        player = inc.get("player", {})
        player_name = player.get("name", "?") if player else "?"
        minute = inc.get("time", "?")
        tag = f"{player_name}({minute}')"

        if inc_type == "goal":
            is_own = inc.get("incidentClass", "").lower() == "owngoal"
            if is_own:
                (away_og if team else home_og).append(tag)
            else:
                (home_scorers if team else away_scorers).append(tag)
        elif inc_type == "card":
            if inc.get("incidentClass", "").lower() in ("red", "yellowred"):
                (home_red if team else away_red).append(tag)

    resultado["home_scorers"] = "; ".join(home_scorers)
    resultado["away_scorers"] = "; ".join(away_scorers)
    resultado["home_own_goals"] = "; ".join(home_og)
    resultado["away_own_goals"] = "; ".join(away_og)
    resultado["home_red_cards_players"] = "; ".join(home_red)
    resultado["away_red_cards_players"] = "; ".join(away_red)
    return resultado

def es_partido_finalizado(evento: dict) -> bool:
    s = evento.get("status", {})
    return str(s.get("type") or s.get("description") or "").lower() in ESTADOS_FINALIZADOS

def es_liga_objetivo(evento: dict) -> bool:
    t = evento.get("tournament", {})
    t_id = t.get("uniqueTournament", {}).get("id") or t.get("id")
    return t_id in LIGAS_IDS_SET

def obtener_nombre_liga(evento: dict) -> str:
    t_id = evento.get("tournament", {}).get("uniqueTournament", {}).get("id") \
        or evento.get("tournament", {}).get("id")
    for nombre, lid in LIGAS_FUTBOL.items():
        if lid == t_id:
            return nombre
    return evento.get("tournament", {}).get("name", "Unknown")

def append_to_csv(partidos: list, archivo: str):
    if not partidos:
        return
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    df_nuevo = pd.DataFrame(partidos)
    if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
        try:
            df_viejo = pd.read_csv(archivo)
            df_final = pd.concat([df_viejo, df_nuevo]).drop_duplicates(subset=["event_id"], keep="last")
        except:
            df_final = df_nuevo
    else:
        df_final = df_nuevo
    df_final.to_csv(archivo, index=False)

def ultima_fecha_csv(archivo: str):
    if not os.path.exists(archivo) or os.path.getsize(archivo) == 0:
        return datetime(2026, 1, 1).date()
    try:
        df = pd.read_csv(archivo)
        return pd.to_datetime(df["tourney_date"]).max().date()
    except:
        return datetime(2026, 1, 1).date()

# ===================== PROCESAMIENTO =====================

def procesar_dia_futbol(fecha: str) -> int:
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url)
    if not data:
        return 0

    eventos = data.get("events", [])
    candidatos = [e for e in eventos if es_partido_finalizado(e) and es_liga_objetivo(e)]

    if not candidatos:
        if eventos:
            muestra = eventos[:3]
            for e in muestra:
                s = e.get("status", {})
                t = e.get("tournament", {})
                t_id = t.get("uniqueTournament", {}).get("id") or t.get("id")
                logging.info(
                    f"  [DEBUG] status_type={s.get("type")!r} status_desc={s.get("description")!r} "
                    f"t_id={t_id!r} t_name={t.get("name")!r} in_set={t_id in LIGAS_IDS_SET}"
                )
        else:
            logging.info(f"  [DEBUG] API devolvio 0 eventos para {fecha}")
        logging.info(f"  → Sin partidos finalizados en ligas objetivo para {fecha}")
        return 0

    logging.info(f"  → {len(candidatos)} partidos encontrados para {fecha}")

    buffer = []
    for i, evento in enumerate(candidatos, 1):
        event_id = evento.get("id")
        try:
            home = evento.get("homeTeam", {})
            away = evento.get("awayTeam", {})
            h_score = evento.get("homeScore", {}) or {}
            a_score = evento.get("awayScore", {}) or {}

            home_goals = h_score.get("current", h_score.get("normaltime", 0)) or 0
            away_goals = a_score.get("current", a_score.get("normaltime", 0)) or 0
            home_ht    = h_score.get("period1", "?")
            away_ht    = a_score.get("period1", "?")
            home_et    = h_score.get("overtime")
            away_et    = a_score.get("overtime")
            home_pen   = h_score.get("penalties")
            away_pen   = a_score.get("penalties")

            liga_nombre = obtener_nombre_liga(evento)

            stats_raw    = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics")
            incidents_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/incidents")

            partido = {
                "event_id":        event_id,
                "liga":            liga_nombre,
                "tourney_id":      evento.get("tournament", {}).get("uniqueTournament", {}).get("id")
                                   or evento.get("tournament", {}).get("id"),
                "tourney_name":    evento.get("tournament", {}).get("name"),
                "tourney_date":    fecha,
                "round":           evento.get("roundInfo", {}).get("name", "Unknown"),
                "season":          evento.get("season", {}).get("name", "Unknown"),
                "home_team_id":    home.get("id"),
                "home_team_name":  home.get("name"),
                "away_team_id":    away.get("id"),
                "away_team_name":  away.get("name"),
                "home_goals":      int(home_goals),
                "away_goals":      int(away_goals),
                "home_ht":         home_ht,
                "away_ht":         away_ht,
                "home_et":         home_et,
                "away_et":         away_et,
                "home_pen":        home_pen,
                "away_pen":        away_pen,
                "result":          "H" if int(home_goals) > int(away_goals) else ("A" if int(away_goals) > int(home_goals) else "D"),
                "scrape_date":     datetime.now().strftime("%Y-%m-%d"),
            }

            if stats_raw:
                partido.update(parsear_estadisticas(stats_raw))

            partido.update(parsear_goles_detallados(incidents_raw))

            buffer.append(partido)
            logging.info(f"  [{i:3d}/{len(candidatos)}] ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | {liga_nombre}")

            if len(buffer) >= GUARDAR_CADA_N_PARTIDOS:
                append_to_csv(buffer, ARCHIVO_FUTBOL)
                buffer.clear()

        except Exception as e:
            logging.error(f"💥 Error evento {event_id}: {e}")

    if buffer:
        append_to_csv(buffer, ARCHIVO_FUTBOL)
    return len(candidatos)

# ===================== MAIN =====================
