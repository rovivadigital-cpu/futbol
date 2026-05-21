import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import time
import json
import random
from curl_cffi import requests as cffi_requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===================== CONFIG GENERAL =====================
CARPETA_SALIDA = "datos"
ARCHIVO_COOKIES = os.path.join(CARPETA_SALIDA, "cookies.txt")
GUARDAR_CADA_N_PARTIDOS = 10
PAUSA_ENTRE_REQUESTS = 0.9
ESTADOS_FINALIZADOS = {"finished", "completed", "ended", "closed", "final", "done"}
CHROME_VERSIONS = ["chrome136", "chrome131", "chrome124"]

# ===================== CONFIG TENIS =====================
ARCHIVO_TENIS = os.path.join(CARPETA_SALIDA, "tenis_historico.csv")
CIRCUITOS_NOMBRES = ["atp", "wta", "challenger"]

# ===================== CONFIG FÚTBOL =====================
ARCHIVO_FUTBOL = os.path.join(CARPETA_SALIDA, "futbol_historico.csv")

# Ligas con sus tournament IDs de Sofascore
LIGAS_FUTBOL = {
    "CONMEBOL Libertadores":        87760,
    "UEFA Champions League":        76953,
    "Club World Championship":      69619,
    "UEFA Europa League":           76984,
    "UEFA Conference League":       76960,
    "Premier League":               76986,
    "Championship":                 77347,
    "League One":                   77352,
    "La Liga":                      77559,
    "LaLiga 2":                     77558,
    "Bundesliga":                   77333,
    "2. Bundesliga":                77354,
    "Serie A":                      76457,
    "Serie B":                      79502,
    "Ligue 1":                      77356,
    "Ligue 2":                      77357,
    "MLS":                          86668,
    "NWSL":                         88711,
    "CONMEBOL Sudamericana":        87770,
    "Saudi Pro League":             80443,
    "Liga Profesional Argentina":   87913,
    "Primera Nacional Argentina":   87940,
    "A-League Men":                 82603,
    "NPL Capital Football":         90775,
    "Austrian Bundesliga":          77382,
    "Belgian Pro League":           77040,
    "Bolivian División Profesional":92509,
    "Brasileirao Serie A":          87678,
    "Brasileirao Serie B":          89840,
    "Bulgarian Parva Liga":         76882,
    "Czech 1. Liga":                77019,
    "Chilean Primera División":     88493,
    "Chinese Super League":         90049,
    "Colombia Primera A Apertura":  88503,
    "Colombia Primera A Clausura":  77825,
    "Colombia Primera B":           89001,
    "K League 1":                   88606,
    "HNL Croatia":                  76980,
    "Danish Superliga":             76491,
    "Egyptian Premier League":      79317,
    "Scottish Premiership":         77128,
    "Scottish Championship":        77037,
    "Slovenian PrvaLiga":           77283,
    "Estonian Premium Liiga":       89137,
    "Finnish Veikkausliiga":        87930,
    "Greek Super League":           78175,
    "Indonesian Liga 1":            78590,
    "J1 League":                    87931,
    "J2 League":                    87932,
    "Latvian Virsliga":             89428,
    "Liga MX Apertura":             76500,
    "Liga MX Clausura":             87699,
    "Norwegian Eliteserien":        87809,
    "Eredivisie":                   77012,
    "Eerste Divisie":               77156,
    "Ekstraklasa":                  76477,
    "Romanian Superliga":           77312,
    "South African Premiership":    79701,
    "Allsvenskan":                  87925,
    "Superettan":                   87924,
    "Turkish Süper Lig":            77805,
    "Ukrainian Premier League":     77625,
    "Swiss Super League":           77152,
}

# Set de IDs para filtrado rápido
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

def api_get(url: str, sport: str = "football", intentos: int = 4) -> dict:
    global SESSION, _403_consecutivos
    if "/event/" in url:
        event_part = url.split("/event/")[1].split("/")[0]
        SESSION.headers.update({"Referer": f"https://www.sofascore.com/{sport}/match/{event_part}"})
    else:
        SESSION.headers.update({"Referer": f"https://www.sofascore.com/{sport}"})

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

# ===================== UTILIDADES COMPARTIDAS =====================

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

def es_partido_finalizado(evento: dict) -> bool:
    s = evento.get("status", {})
    return str(s.get("type") or s.get("description") or "").lower() in ESTADOS_FINALIZADOS

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

# ===================== MÓDULO TENIS =====================

def parsear_marcador_detallado(detalles: dict, home_wins: bool) -> str:
    if not detalles:
        return "N/A"
    event = detalles.get("event") or detalles
    sets_list = None
    for path in [
        lambda e: e.get("score", {}).get("sets"),
        lambda e: e.get("sets"),
        lambda e: e.get("eventScore", {}).get("sets"),
        lambda e: e.get("periods"),
    ]:
        res = path(event)
        if isinstance(res, list) and len(res) > 0:
            sets_list = res
            break

    if sets_list:
        scores = []
        for s in sets_list:
            h = s.get("homeScore") if s.get("homeScore") is not None else s.get("games", {}).get("home")
            if h is None:
                h = s.get("value")
            a = s.get("awayScore") if s.get("awayScore") is not None else s.get("games", {}).get("away")
            if a is None:
                a = s.get("value")
            if h is not None and a is not None:
                scores.append(f"{int(h)}-{int(a)}" if home_wins else f"{int(a)}-{int(h)}")
        if scores:
            return " ".join(scores)

    for key in ["displayScore", "scoreString", "currentScore"]:
        val = event.get(key)
        if val and isinstance(val, str):
            return val.strip()

    h_obj = event.get("homeScore")
    a_obj = event.get("awayScore")
    h_s = h_obj.get("current") if isinstance(h_obj, dict) else h_obj
    a_s = a_obj.get("current") if isinstance(a_obj, dict) else a_obj
    if home_wins:
        return f"{h_s if h_s is not None else '?'}-{a_s if a_s is not None else '?'}"
    else:
        return f"{a_s if a_s is not None else '?'}-{h_s if h_s is not None else '?'}"

def es_partido_sencillos(evento: dict) -> bool:
    return not any(x in str(evento).lower() for x in ["doubles", "dobles", "mixed", "mixtos"])

def detectar_circuito(evento: dict):
    t = evento.get("tournament", {})
    texto = (str(t.get("category", {}).get("name", "")) + str(t.get("name", ""))).lower()
    for c in CIRCUITOS_NOMBRES:
        if c in texto:
            return c.upper()
    return None

def procesar_dia_tenis(fecha: str) -> int:
    url = f"https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{fecha}"
    data = api_get(url, sport="tennis")
    if not data:
        return 0

    eventos = data.get("events", [])
    candidatos = [
        (e, detectar_circuito(e))
        for e in eventos
        if es_partido_finalizado(e) and es_partido_sencillos(e) and detectar_circuito(e)
    ]

    buffer = []
    for i, (evento, circuito) in enumerate(candidatos, 1):
        event_id = evento.get("id")
        try:
            home = evento.get("homeTeam", {})
            away = evento.get("awayTeam", {})
            h_score = evento.get("homeScore", {}) or {}
            a_score = evento.get("awayScore", {}) or {}

            home_sets = h_score.get("current") or h_score.get("display") or 0
            away_sets = a_score.get("current") or a_score.get("display") or 0
            home_wins = int(home_sets) > int(away_sets)

            detalles = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}", sport="tennis")
            detailed_score = parsear_marcador_detallado(detalles, home_wins)
            stats_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics", sport="tennis")

            partido = {
                "event_id": event_id,
                "circuito": circuito,
                "tourney_id": evento.get("tournament", {}).get("id"),
                "tourney_name": evento.get("tournament", {}).get("name"),
                "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "surface": evento.get("groundType") or "Unknown",
                "home_player_id": home.get("id"),
                "away_player_id": away.get("id"),
                "home_wins": 1 if home_wins else 0,
                "winner_id": home.get("id") if home_wins else away.get("id"),
                "winner_name": home.get("name") if home_wins else away.get("name"),
                "loser_id": away.get("id") if home_wins else home.get("id"),
                "loser_name": away.get("name") if home_wins else home.get("name"),
                "winner_sets": int(home_sets) if home_wins else int(away_sets),
                "loser_sets": int(away_sets) if home_wins else int(home_sets),
                "detailed_score": detailed_score,
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }

            if stats_raw:
                partido.update(parsear_estadisticas(stats_raw))

            buffer.append(partido)
            logging.info(f"  [TENIS {i:3d}/{len(candidatos)}] ✅ {partido['winner_name']} def. {partido['loser_name']} → {detailed_score}")

            if len(buffer) >= GUARDAR_CADA_N_PARTIDOS:
                append_to_csv(buffer, ARCHIVO_TENIS)
                buffer.clear()

        except Exception as e:
            logging.error(f"💥 Error tenis evento {event_id}: {e}")

    if buffer:
        append_to_csv(buffer, ARCHIVO_TENIS)
    return len(candidatos)

# ===================== MÓDULO FÚTBOL =====================

def obtener_nombre_liga(evento: dict) -> str:
    """Devuelve el nombre legible de la liga desde el mapa LIGAS_FUTBOL."""
    t_id = evento.get("tournament", {}).get("uniqueTournament", {}).get("id") \
        or evento.get("tournament", {}).get("id")
    for nombre, lid in LIGAS_FUTBOL.items():
        if lid == t_id:
            return nombre
    return evento.get("tournament", {}).get("name", "Unknown")

def es_liga_objetivo(evento: dict) -> bool:
    """Verifica si el partido pertenece a una de las ligas configuradas."""
    t = evento.get("tournament", {})
    t_id = t.get("uniqueTournament", {}).get("id") or t.get("id")
    return t_id in LIGAS_IDS_SET

def parsear_goles_detallados(incidents_data: dict) -> dict:
    """
    Extrae goleadores del endpoint /incidents.
    Devuelve columnas: home_scorers, away_scorers, home_own_goals, away_own_goals
    """
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
        team = inc.get("isHome")  # True = home, False = away
        player = inc.get("player", {})
        player_name = player.get("name", "?") if player else "?"
        minute = inc.get("time", "?")
        tag = f"{player_name}({minute}')"

        if inc_type == "goal":
            is_own = inc.get("incidentClass", "").lower() == "owngoal"
            if is_own:
                # Own goal: anota para el equipo contrario
                if team:
                    away_og.append(tag)   # home jugador mete en su arco → punto para away
                else:
                    home_og.append(tag)
            else:
                if team:
                    home_scorers.append(tag)
                else:
                    away_scorers.append(tag)

        elif inc_type == "card":
            card_class = inc.get("incidentClass", "").lower()
            if card_class in ("red", "yellowred"):
                if team:
                    home_red.append(tag)
                else:
                    away_red.append(tag)

    resultado["home_scorers"] = "; ".join(home_scorers)
    resultado["away_scorers"] = "; ".join(away_scorers)
    resultado["home_own_goals"] = "; ".join(home_og)
    resultado["away_own_goals"] = "; ".join(away_og)
    resultado["home_red_cards_players"] = "; ".join(home_red)
    resultado["away_red_cards_players"] = "; ".join(away_red)
    return resultado

def procesar_dia_futbol(fecha: str) -> int:
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url, sport="football")
    if not data:
        return 0

    eventos = data.get("events", [])
    candidatos = [e for e in eventos if es_partido_finalizado(e) and es_liga_objetivo(e)]

    if not candidatos:
        return 0

    logging.info(f"  → {len(candidatos)} partidos de fútbol encontrados para {fecha}")

    buffer = []
    for i, evento in enumerate(candidatos, 1):
        event_id = evento.get("id")
        try:
            home = evento.get("homeTeam", {})
            away = evento.get("awayTeam", {})
            h_score = evento.get("homeScore", {}) or {}
            a_score = evento.get("awayScore", {}) or {}

            # Goles normales (full time)
            home_goals = h_score.get("current", h_score.get("normaltime", 0)) or 0
            away_goals = a_score.get("current", a_score.get("normaltime", 0)) or 0

            # Resultado extra time / penalties
            home_et = h_score.get("overtime")
            away_et = a_score.get("overtime")
            home_pen = h_score.get("penalties")
            away_pen = a_score.get("penalties")

            # HT score
            home_ht = h_score.get("period1", "?")
            away_ht = a_score.get("period1", "?")

            liga_nombre = obtener_nombre_liga(evento)

            # Fetch detallado: estadísticas + incidentes
            stats_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics", sport="football")
            incidents_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/incidents", sport="football")

            partido = {
                "event_id": event_id,
                "liga": liga_nombre,
                "tourney_id": evento.get("tournament", {}).get("uniqueTournament", {}).get("id")
                              or evento.get("tournament", {}).get("id"),
                "tourney_name": evento.get("tournament", {}).get("name"),
                "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "season": evento.get("season", {}).get("name", "Unknown"),
                # Equipos
                "home_team_id": home.get("id"),
                "home_team_name": home.get("name"),
                "away_team_id": away.get("id"),
                "away_team_name": away.get("name"),
                # Resultado
                "home_goals": int(home_goals),
                "away_goals": int(away_goals),
                "home_ht": home_ht,
                "away_ht": away_ht,
                "home_et": home_et,
                "away_et": away_et,
                "home_pen": home_pen,
                "away_pen": away_pen,
                "result": "H" if int(home_goals) > int(away_goals) else ("A" if int(away_goals) > int(home_goals) else "D"),
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }

            # Estadísticas detalladas
            if stats_raw:
                partido.update(parsear_estadisticas(stats_raw))

            # Goleadores y tarjetas rojas
            partido.update(parsear_goles_detallados(incidents_raw))

            buffer.append(partido)
            logging.info(
                f"  [FUTBOL {i:3d}/{len(candidatos)}] ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} ({liga_nombre})"
            )

            if len(buffer) >= GUARDAR_CADA_N_PARTIDOS:
                append_to_csv(buffer, ARCHIVO_FUTBOL)
                buffer.clear()

        except Exception as e:
            logging.error(f"💥 Error fútbol evento {event_id}: {e}")

    if buffer:
        append_to_csv(buffer, ARCHIVO_FUTBOL)
    return len(candidatos)

# ===================== MAIN =====================

if __name__ == "__main__":
    logging.info("🚀 Iniciando Scraper Profesional v3 (Tenis + Fútbol)...")

    # Fechas tenis
    ultima_fecha_tenis = ultima_fecha_csv(ARCHIVO_TENIS)
    # Fechas fútbol (CSV separado)
    ultima_fecha_futbol = ultima_fecha_csv(ARCHIVO_FUTBOL)

    hoy = datetime.now().date()

    fechas_tenis = [
        (ultima_fecha_tenis + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((hoy - ultima_fecha_tenis).days + 1)
    ]
    fechas_futbol = [
        (ultima_fecha_futbol + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((hoy - ultima_fecha_futbol).days + 1)
    ]

    # Unión de fechas a procesar (sin duplicados, ordenadas)
    todas_fechas = sorted(set(fechas_tenis) | set(fechas_futbol))

    total_tenis = 0
    total_futbol = 0

    for idx, fecha in enumerate(todas_fechas, 1):
        logging.info(f"══════ Día {idx}/{len(todas_fechas)}: {fecha} ══════")

        if fecha in set(fechas_tenis):
            logging.info(f"  🎾 Procesando tenis...")
            total_tenis += procesar_dia_tenis(fecha)

        if fecha in set(fechas_futbol):
            logging.info(f"  ⚽ Procesando fútbol...")
            total_futbol += procesar_dia_futbol(fecha)

        time.sleep(random.uniform(10, 20))

    logging.info(f"✅ ¡Completado! Tenis: {total_tenis} partidos | Fútbol: {total_futbol} partidos")
