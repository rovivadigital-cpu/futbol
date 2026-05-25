import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import time
import json
import random
from curl_cffi import requests as cffi_requests

# Configuración de logs detallada
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===================== CONFIG GENERAL =====================
CARPETA_SALIDA        = "datos"
ARCHIVO_COOKIES       = os.path.join(CARPETA_SALIDA, "cookies.txt")
ARCHIVO_FUTBOL        = os.path.join(CARPETA_SALIDA, "futbol_historico.csv")
GUARDAR_CADA_N        = 5
ARCHIVO_CHECKPOINT    = os.path.join(CARPETA_SALIDA, "checkpoint.json")
PAUSA_BASE            = 0.8
CHROME_VERSIONS       = ["chrome136", "chrome131", "chrome124"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
]

COLUMNAS_BBDD = [
    "event_id", "pais", "liga", "tourney_id", "tourney_name", "tourney_season", "tourney_date", 
    "round", "round_number", "home_team_id", "home_team_name", "away_team_id", "away_team_name", 
    "home_goals", "away_goals", "home_ht_goals", "away_ht_goals", "home_et_goals", "away_et_goals", 
    "home_pen_goals", "away_pen_goals", "result", "scrape_date",
    "ALL_ball_possession_home", "ALL_ball_possession_away", 
    "ALL_expected_goals_home", "ALL_expected_goals_away",
    "ALL_big_chances_home", "ALL_big_chances_away", 
    "ALL_total_shots_home", "ALL_total_shots_away",
    "ALL_goalkeeper_saves_home", "ALL_goalkeeper_saves_away", 
    "ALL_corner_kicks_home", "ALL_corner_kicks_away",
    "ALL_fouls_home", "ALL_fouls_away", 
    "ALL_passes_home", "ALL_passes_away", 
    "ALL_yellow_cards_home", "ALL_yellow_cards_away", 
    "ALL_shots_on_target_home", "ALL_shots_on_target_away", 
    "ALL_offsides_home", "ALL_offsides_away", 
    "ALL_accurate_passes_home", "ALL_accurate_passes_away",
    "ALL_red_cards_home", "ALL_red_cards_away"
]

MAPEO_ESTADISTICAS = {
    "ball possession": "ball_possession", "expected goals": "expected_goals",
    "big chances": "big_chances", "total shots": "total_shots",
    "goalkeeper saves": "goalkeeper_saves", "corner kicks": "corner_kicks",
    "fouls": "fouls", "passes": "passes", "yellow cards": "yellow_cards",
    "shots on target": "shots_on_target", "offsides": "offsides",
    "accurate passes": "accurate_passes", "red cards": "red_cards",
}

TORNEOS_IDS = { 
    17: {"nombre": "Premier League", "pais": "England"},
18: {"nombre": "Championship", "pais": "England"},
24: {"nombre": "League One", "pais": "England"},
25: {"nombre": "League Two", "pais": "England"},
19: {"nombre": "FA Cup", "pais": "England"},
841: {"nombre": "Algerian Ligue 1", "pais": "Algeria"},
155: {"nombre": "Liga Profesional de Fútbol", "pais": "Argentina"},
703: {"nombre": "Primera Nacional", "pais": "Argentina"},
1347: {"nombre": "Primera B Metropolitana", "pais": "Argentina"},
136: {"nombre": "A-League Men", "pais": "Australia"},
1894: {"nombre": "A-League Women", "pais": "Australia"},
1260: {"nombre": "NPL Capital Football", "pais": "Australia"},
1268: {"nombre": "NPL Queensland", "pais": "Australia"},
709: {"nombre": "Misli Premier League", "pais": "Azerbaijan"},
846: {"nombre": "Bahraini Premier League", "pais": "Bahrain"},
13331: {"nombre": "Bangladesh Football League", "pais": "Bangladesh"},
16736: {"nombre": "División Profesional", "pais": "Bolivia"},
325: {"nombre": "Brasileirão Betano", "pais": "Brazil"},
390: {"nombre": "Brasileirão Série B", "pais": "Brazil"},
1281: {"nombre": "Brasileirão Série C", "pais": "Brazil"},
22106: {"nombre": "Première Division de N’Djaména", "pais": "Chad"},
11653: {"nombre": "Liga de Primera", "pais": "Chile"},
649: {"nombre": "Chinese Super League", "pais": "China"},
782: {"nombre": "Chinese League 1", "pais": "China"},
11539: {"nombre": "Primera A, Apertura", "pais": "Colombia"},
11536: {"nombre": "Primera A, Finalización", "pais": "EColombia"},
1238: {"nombre": "Categoría Primera B", "pais": "Colombia"},
240: {"nombre": "LigaPro Serie A", "pais": "Ecuador"},
808: {"nombre": "Egyptian Premier League", "pais": "Egypt"},
309: {"nombre": "World Cup Qual. OFC", "pais": "Oceania"},
1222: {"nombre": "OFC Champions League", "pais": "Oceania"},
704: {"nombre": "Erovnuli Liga", "pais": "Georgia"},
1054: {"nombre": "CAF Champions League", "pais": "Africa"},
463: {"nombre": "AFC Champions League Elite", "pais": "Asia"},
7: {"nombre": "UEFA Champions League", "pais": "Europe"},
679: {"nombre": "UEFA Europa League", "pais": "Europe"},
17015: {"nombre": "UEFA Conference League", "pais": "Europe"},
696: {"nombre": "UEFA Women's Champions League", "pais": "Europe"},
140: {"nombre": "CONCACAF Gold Cup", "pais": "North & Central America"},
11454: {"nombre": "Campeones Cup", "pais": "North & Central America"},
498: {"nombre": "CONCACAF Champions Cup", "pais": "North & Central America"},
13783: {"nombre": "Leagues Cup", "pais": "North & Central America"},
384: {"nombre": "CONMEBOL Libertadores", "pais": "South America"},
480: {"nombre": "CONMEBOL Sudamericana", "pais": "South America"},
133: {"nombre": "Copa América", "pais": "South America"},
10602: {"nombre": "Copa Libertadores Femenina", "pais": "South America"},
1015: {"nombre": "Indonesia Super League", "pais": "Indonesia"},
20708: {"nombre": "UEFA-CONMEBOL Club Challenge", "pais": "World"},
16: {"nombre": "FIFA World Cup", "pais": "World"},
23674: {"nombre": "FIFA Intercontinental Cup", "pais": "World"},
851: {"nombre": "International Friendly Games", "pais": "World"},
290: {"nombre": "FIFA Women's World Cup", "pais": "World"},
915: {"nombre": "Persian Gulf Pro League", "pais": "Iran"},
206: {"nombre": "Israeli Premier League", "pais": "Israel"},
196: {"nombre": "J1 League", "pais": "Japan"},
402: {"nombre": "J2 League", "pais": "Japan"},
682: {"nombre": "Kazakhstan Premier League", "pais": "Kazakhstan"},
1002: {"nombre": "Zain Premier League", "pais": "Kuwait"},
594: {"nombre": "New Zealand National League", "pais": "New Zealand"},
200: {"nombre": "NIFL Premiership", "pais": "Northern Ireland"},
11540: {"nombre": "Primera División, Apertura", "pais": "Paraguay"},
11541: {"nombre": "Primera División, Clausura", "pais": "Paraguay"},
406: {"nombre": "Liga 1", "pais": "Peru"},
825: {"nombre": "Stars League", "pais": "Qatar"},
955: {"nombre": "Saudi Pro League", "pais": "Saudi Arabia"},
36: {"nombre": "Scottish Premiership", "pais": "Scotland"},
206: {"nombre": "Scottish Championship", "pais": "Scotland"},
358: {"nombre": "South African Premier Division", "pais": "South Africa"},
52: {"nombre": "Trendyol Süper Lig", "pais": "Turkey"},
971: {"nombre": "UAE Pro League", "pais": "United Arab Emirates"},
278: {"nombre": "Liga AUF Uruguaya", "pais": "Uruguay"},
13470: {"nombre": "Canadian Premier League", "pais": "Canada"},
11621: {"nombre": "Liga MX, Apertura", "pais": "Mexico"},
11620: {"nombre": "Liga MX, Clausura", "pais": "Mexico"},
11611: {"nombre": "Liga de Expansión MX, Apertura", "pais": "Mexico"},
11612: {"nombre": "Liga de Expansión MX, Clausura", "pais": "Mexico"},
242: {"nombre": "MLS", "pais": "USA"},
13363: {"nombre": "USL Championship", "pais": "USA"},
18641: {"nombre": "MLS Next Pro", "pais": "USA"},
1690: {"nombre": "NWSL", "pais": "USA"},
197: {"nombre": "Virsliga", "pais": "Latvia"},
198: {"nombre": "TOPLYGA", "pais": "Lithuania"},
211: {"nombre": "Niké Liga", "pais": "Slovakia"},
8: {"nombre": "LaLiga", "pais": "Spain"},
54: {"nombre": "LaLiga 2", "pais": "Spain"},
20: {"nombre": "Eliteserien", "pais": "Norway"},
22: {"nombre": "Norwegian 1st Division", "pais": "Norway"},
202: {"nombre": "Ekstraklasa", "pais": "Poland"},
238: {"nombre": "Liga Portugal Betclic", "pais": "Portugal"},
152: {"nombre": "SuperLiga României", "pais": "Romania"},
40: {"nombre": "Allsvenskan", "pais": "Sweden"},
46: {"nombre": "Superettan", "pais": "Sweden"},
67: {"nombre": "Ettan, Norra", "pais": "Sweden"},
68: {"nombre": "Ettan, Södra", "pais": "Sweden"},
214: {"nombre": "Damallsvenskan", "pais": "Sweden"},
218: {"nombre": "Ukrainian Premier League", "pais": "Ukraine"},
37: {"nombre": "VriendenLoterij Eredivisie", "pais": "Netherlands"},
131: {"nombre": "Eerste Divisiee", "pais": "Netherlands"},
215: {"nombre": "Swiss Super League", "pais": "Switzerland"},
185: {"nombre": "Stoiximan Super League", "pais": "Greece"},
38: {"nombre": "Pro League", "pais": "Belgium"},
9: {"nombre": "Challenger Pro League", "pais": "Belgium"},
178: {"nombre": "Premium Liiga", "pais": "Estonia"},
678: {"nombre": "Esiliiga", "pais": "Estonia"},
41: {"nombre": "Veikkausliiga", "pais": "Finland"},
55: {"nombre": "Ykkösliiga", "pais": "Finland"},
34: {"nombre": "Ligue 1", "pais": "France"},
182: {"nombre": "Ligue 2", "pais": "France"},
35: {"nombre": "Bundesliga", "pais": "Germany"},
44: {"nombre": "2. Bundesliga", "pais": "Germany"},
192: {"nombre": "Premier Division", "pais": "Ireland"},
23: {"nombre": "Serie A", "pais": "Italy"},
53: {"nombre": "Serie B", "pais": "Italy"},
45: {"nombre": "Austrian Bundesliga", "pais": "Austria"},
247: {"nombre": "Parva Liga", "pais": "Bulgaria"},
1135: {"nombre": "Vtora Liga", "pais": "Bulgaria"},
205: {"nombre": "FNL", "pais": "Czech Republic"},
39: {"nombre": "Danish Superliga", "pais": "Denmark"},
170: {"nombre": "HNL", "pais": "Croatia"},
}
IDS_DESEADOS = set(TORNEOS_IDS.keys())

def _cargar_cookies() -> dict:
    if not os.path.exists(ARCHIVO_COOKIES): return {}
    try:
        with open(ARCHIVO_COOKIES, "r", encoding="utf-8") as f:
            cont = f.read().strip()
        if cont.startswith("["):
            data = json.loads(cont)
            return {item.get("name"): item.get("value") for item in data if item.get("name")}
    except Exception: pass
    return {}

def _nueva_sesion() -> cffi_requests.Session:
    impersonate = random.choice(CHROME_VERSIONS)
    ua = random.choice(USER_AGENTS)
    s = cffi_requests.Session(impersonate=impersonate)
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "User-Agent": ua,
        "Origin": "https://www.sofascore.com",
        "Referer": "https://www.sofascore.com/football",
    })
    cookies = _cargar_cookies()
    if cookies: s.cookies.update(cookies)
    return s

SESSION = _nueva_sesion()
_403_consecutivos = 0

def api_get(url: str, intentos: int = 3) -> dict:
    global SESSION, _403_consecutivos
    for i in range(1, intentos + 1):
        try:
            time.sleep(PAUSA_BASE + random.uniform(0.2, 0.9))
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
        except Exception as e:
            logging.error(f"Error en {url}: {e}")
    return {}

def es_partido_finalizado(evento: dict) -> bool:
    status = evento.get("status", {})
    if status.get("code") == 100: return True
    desc = str(status.get("description", "")).lower()
    return any(k in desc for k in ["finished", "ended", "ft", "full time"])

def parsear_estadisticas_compactas(stats_data: dict) -> dict:
    resultado = {}
    if not stats_data or "statistics" not in stats_data: return resultado
    
    # Buscamos el periodo que represente el TOTAL
    periodos = stats_data.get("statistics", [])
    periodo_total = None
    
    for p in periodos:
        p_name = str(p.get("period", "")).lower()
        if p_name == "total" or p_name == "all" or p_name == "overall":
            periodo_total = p
            break
    
    # Si no encontramos un periodo marcado como total, tomamos el primero disponible
    if not periodo_total and periodos:
        periodo_total = periodos[0]
    
    if not periodo_total: return resultado

    for grupo in periodo_total.get("groups", []):
        for item in grupo.get("statisticsItems", []):
            nombre_api = item.get("name", "").lower()
            if nombre_api in MAPEO_ESTADISTICAS:
                col_name = MAPEO_ESTADISTICAS[nombre_api]
                for lado in ("home", "away"):
                    val = item.get(lado, {})
                    resultado[f"ALL_{col_name}_{lado}"] = val.get("value", 0) if isinstance(val, dict) else val
    return resultado

def parsear_xg_compacto(shotmap_data: dict) -> dict:
    resultado = {}
    if not shotmap_data: return resultado
    summary = shotmap_data.get("summary", {})
    if summary:
        for lado in ("home", "away"):
            s = summary.get(lado, {})
            resultado[f"ALL_expected_goals_{lado}"] = s.get("xg", 0)
    return resultado

def procesar_dia(fecha: str) -> int:
    logging.info(f"📅 Consultando fecha: {fecha}...")
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url)
    if not data: return 0
    
    eventos_brutos = data.get("events", [])
    eventos = [e for e in eventos_brutos if e.get("tournament", {}).get("uniqueTournament", {}).get("id") in IDS_DESEADOS and es_partido_finalizado(e)]
    
    if not eventos: 
        logging.info(f"   ∅ Sin partidos finalizados.")
        return 0

    logging.info(f"   🎯 {len(eventos)} partidos para descargar.")
    buffer = []
    for i, evento in enumerate(eventos, 1):
        event_id = evento.get("id")
        try:
            home, away = evento.get("homeTeam", {}), evento.get("awayTeam", {})
            h_sc, a_sc = evento.get("homeScore", {}) or {}, evento.get("awayScore", {}) or {}
            hg = h_sc.get("current", h_sc.get("normaltime", 0)) or 0
            ag = a_sc.get("current", a_sc.get("normaltime", 0)) or 0
            ut = evento.get("tournament", {}).get("uniqueTournament", {})
            info = TORNEOS_IDS[ut.get("id")]

            partido = {
                "event_id": event_id, "pais": info["pais"], "liga": info["nombre"],
                "tourney_id": ut.get("id"), "tourney_name": ut.get("name"),
                "tourney_season": evento.get("season", {}).get("name", ""), "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "round_number": evento.get("roundInfo", {}).get("round", 0),
                "home_team_id": home.get("id"), "home_team_name": home.get("name"),
                "away_team_id": away.get("id"), "away_team_name": away.get("name"),
                "home_goals": int(hg), "away_goals": int(ag),
                "home_ht_goals": h_sc.get("period1", 0), "away_ht_goals": a_sc.get("period1", 0),
                "home_et_goals": h_sc.get("overtime"), "away_et_goals": a_sc.get("overtime"),
                "home_pen_goals": h_sc.get("penalties"), "away_pen_goals": a_sc.get("penalties"),
                "result": "H" if int(hg) > int(ag) else ("A" if int(ag) > int(hg) else "D"),
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }

            stats = parsear_estadisticas_compactas(api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"))
            xg = parsear_xg_compacto(api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/shotmap"))
            partido.update(stats)
            partido.update(xg)

            fila_ordenada = {col: partido.get(col, 0) for col in COLUMNAS_BBDD}
            buffer.append(fila_ordenada)
            logging.info(f"      ✅ {i}/{len(eventos)}: {home.get('name')} vs {away.get('name')} OK")

            if len(buffer) >= GUARDAR_CADA_N:
                _append_csv(buffer)
                buffer.clear()
        except Exception as e: 
            logging.error(f"💥 Error evento {event_id}: {e}")
    
    if buffer: _append_csv(buffer)
    return len(eventos)

def _cargar_checkpoint() -> set:
    if not os.path.exists(ARCHIVO_CHECKPOINT): return set()
    try:
        with open(ARCHIVO_CHECKPOINT, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def _guardar_checkpoint(fechas_listas: set):
    with open(ARCHIVO_CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(sorted(fechas_listas), f)

def _append_csv(partidos: list):
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    df_new = pd.DataFrame(partidos, columns=COLUMNAS_BBDD)
    if os.path.exists(ARCHIVO_FUTBOL) and os.path.getsize(ARCHIVO_FUTBOL) > 0:
        try:
            df_old = pd.read_csv(ARCHIVO_FUTBOL)
            if set(df_old.columns) != set(COLUMNAS_BBDD):
                df_old = pd.DataFrame(columns=COLUMNAS_BBDD)
            df_all = pd.concat([df_old, df_new], ignore_index=True).drop_duplicates(subset=["event_id"], keep="last")
            df_all.to_csv(ARCHIVO_FUTBOL, index=False, columns=COLUMNAS_BBDD)
        except Exception as e:
            logging.error(f"Error al unir CSV: {e}")
            df_new.to_csv(ARCHIVO_FUTBOL, index=False, columns=COLUMNAS_BBDD)
    else:
        df_new.to_csv(ARCHIVO_FUTBOL, index=False, columns=COLUMNAS_BBDD)

if __name__ == "__main__":
    logging.info("🚀 SCRAPER FÚTBOL ANTI-BOT v2.9 — FIXED STATS + CHECKPOINT")
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    fecha_inicio = datetime(2026, 1, 1).date()
    hoy = datetime.now().date()

    todas_fechas = []
    f = fecha_inicio
    while f <= hoy:
        todas_fechas.append(f.strftime("%Y-%m-%d"))
        f += timedelta(days=1)

    # ── CHECKPOINT: cargar fechas ya completadas ──
    completadas = _cargar_checkpoint()

    # Si no hay checkpoint, leer el CSV existente para no repetir días ya descargados
    if not completadas and os.path.exists(ARCHIVO_FUTBOL) and os.path.getsize(ARCHIVO_FUTBOL) > 0:
        try:
            df_existente = pd.read_csv(ARCHIVO_FUTBOL, usecols=["tourney_date"])
            fechas_en_csv = set(df_existente["tourney_date"].dropna().astype(str).unique())
            completadas = fechas_en_csv
            _guardar_checkpoint(completadas)
            logging.info(f"📂 CSV existente detectado: {len(completadas)} días ya descargados, generando checkpoint...")
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV para checkpoint: {e}")

    pendientes = [d for d in todas_fechas if d not in completadas]

    if completadas:
        logging.info(f"♻️  Retomando: {len(completadas)} días listos, {len(pendientes)} pendientes.")
    else:
        logging.info("🆕 Sin datos previos, comenzando desde cero.")

    random.shuffle(pendientes)
    logging.info(f"📅 Procesando {len(pendientes)} días pendientes de {len(todas_fechas)} totales...")

    total_descargados = 0
    for idx, fecha_str in enumerate(pendientes, 1):
        logging.info(f"[Día {idx}/{len(pendientes)}]")
        n = procesar_dia(fecha_str)
        total_descargados += n
        # Marcar fecha como completada y guardar checkpoint
        completadas.add(fecha_str)
        _guardar_checkpoint(completadas)
        time.sleep(random.uniform(2, 5))

    logging.info(f"✅ Proceso Completado. Total partidos esta sesión: {total_descargados}")
