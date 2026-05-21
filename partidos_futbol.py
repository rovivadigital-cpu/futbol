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
GUARDAR_CADA_N_PARTIDOS = 5  # Guardar cada 5 partidos (por las estadísticas)
PAUSA_ENTRE_REQUESTS = 2.0  # Mayor pausa para evitar bloqueos
CHROME_VERSIONS = ["chrome136", "chrome131", "chrome124"]

# ===================== CONFIG FÚTBOL =====================
ARCHIVO_FUTBOL = os.path.join(CARPETA_SALIDA, "futbol_historico.csv")

# TODAS LAS LIGAS (usando nombres para coincidencia parcial)
LIGAS_DESEADAS = [
    # CONMEBOL
    "libertadores", "sudamericana",
    # UEFA
    "champions league", "europa league", "europa conference league", "club world championship",
    # Inglaterra
    "premier league", "championship", "league one",
    # España
    "laliga", "laliga 2",
    # Alemania
    "bundesliga", "2. bundesliga",
    # Italia
    "serie a", "serie b",
    # Francia
    "ligue 1", "ligue 2",
    # USA
    "mls", "nwsl",
    # Arabia Saudita
    "saudi pro league",
    # Argentina
    "liga profesional", "primera nacional",
    # Australia
    "a-league", "npl capital football",
    # Austria
    "bundesliga",
    # Bélgica
    "pro league",
    # Bolivia
    "division profesional",
    # Brasil
    "brasileirao serie a", "brasileirao serie b",
    # Bulgaria
    "parva liga",
    # República Checa
    "1. liga",
    # Chile
    "primera division",
    # China
    "cfa super league",
    # Colombia
    "primera a apertura", "primera a clausura", "primera b",
    # Corea del Sur
    "k league 1",
    # Croacia
    "hnl",
    # Dinamarca
    "superliga",
    # Egipto
    "premier league",
    # Escocia
    "premiership", "championship",
    # Eslovenia
    "prvaliga",
    # Estonia
    "premium liiga",
    # Finlandia
    "veikkausliiga",
    # Grecia
    "super league",
    # Indonesia
    "liga 1",
    # Japón
    "j1 league", "j2 league",
    # Letonia
    "virsliga",
    # México
    "liga mx apertura", "liga mx clausura",
    # Noruega
    "eliteserien",
    # Países Bajos
    "eredivisie", "eerste divisie",
    # Polonia
    "ekstraklasa",
    # Rumania
    "superliga",
    # Sudáfrica
    "premiership",
    # Suecia
    "allsvenskan", "superettan",
    # Turquía
    "super lig",
    # Ucrania
    "premier league",
    # Suiza
    "super league",
]

# Palabras a EXCLUIR
PALABRAS_EXCLUIR = [
    "women", "femenino", "femenina", "u19", "u20", "u21", "u23",
    "junior", "youth", "academy", "reserve", "sub", "femení",
    "womens", "futsal", "beach", "amateur", "cup"
]

HEADERS_BASE = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/football",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
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

def api_get(url: str, sport: str = "football", intentos: int = 3) -> dict:
    global SESSION, _403_consecutivos
    
    for i in range(1, intentos + 1):
        try:
            time.sleep(PAUSA_ENTRE_REQUESTS + random.uniform(0.5, 1.5))
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

# ===================== ESTADÍSTICAS DETALLADAS =====================

def formatear_estadistica(val):
    """Formatea valores de estadísticas"""
    if isinstance(val, dict):
        v = val.get("value", 0)
        t = val.get("total", 0)
        if t > 0:
            return f"{v}/{t} ({round((v/t)*100)}%)"
        return f"{v}/{t}"
    return val if val is not None else 0

def parsear_estadisticas_completas(stats_data: dict) -> dict:
    """
    Extrae TODAS las estadísticas del partido
    Incluye: posesión, tiros, pases, faltas, tarjetas, etc.
    """
    resultado = {}
    
    if not stats_data:
        return resultado
    
    for periodo in stats_data.get("statistics", []):
        periodo_nombre = periodo.get("period", "ALL").upper()
        
        for grupo in periodo.get("groups", []):
            for item in grupo.get("statisticsItems", []):
                nombre_raw = item.get("name", "")
                # Limpiar nombre para usarlo como columna
                nombre = nombre_raw.lower().replace(" ", "_").replace(".", "").replace("-", "_")
                
                home_val = item.get("home", {})
                away_val = item.get("away", {})
                
                # Valor para home
                if isinstance(home_val, dict):
                    home_final = home_val.get("value", home_val.get("total", 0))
                    home_total = home_val.get("total", home_val.get("value", 0))
                    if home_total and home_total != home_final:
                        resultado[f"{periodo_nombre}_{nombre}_home"] = f"{home_final}/{home_total}"
                    else:
                        resultado[f"{periodo_nombre}_{nombre}_home"] = home_final
                else:
                    resultado[f"{periodo_nombre}_{nombre}_home"] = home_val
                
                # Valor para away
                if isinstance(away_val, dict):
                    away_final = away_val.get("value", away_val.get("total", 0))
                    away_total = away_val.get("total", away_val.get("value", 0))
                    if away_total and away_total != away_final:
                        resultado[f"{periodo_nombre}_{nombre}_away"] = f"{away_final}/{away_total}"
                    else:
                        resultado[f"{periodo_nombre}_{nombre}_away"] = away_final
                else:
                    resultado[f"{periodo_nombre}_{nombre}_away"] = away_val
    
    return resultado

def parsear_goleadores(incidents_data: dict) -> dict:
    """Extrae goleadores, asistencias, tarjetas rojas y amarillas"""
    resultado = {
        "home_goal_scorers": "",
        "away_goal_scorers": "",
        "home_goal_minutes": "",
        "away_goal_minutes": "",
        "home_assists": "",
        "away_assists": "",
        "home_yellow_cards": "",
        "away_yellow_cards": "",
        "home_red_cards": "",
        "away_red_cards": "",
        "home_own_goals": "",
        "away_own_goals": "",
        "total_goals": 0,
        "total_cards": 0,
    }
    
    if not incidents_data:
        return resultado

    home_scorers = []
    away_scorers = []
    home_minutes = []
    away_minutes = []
    home_assists_list = []
    away_assists_list = []
    home_yellow = []
    away_yellow = []
    home_red = []
    away_red = []
    home_og = []
    away_og = []
    
    for inc in incidents_data.get("incidents", []):
        inc_type = inc.get("incidentType", "").lower()
        is_home = inc.get("isHome", False)
        player = inc.get("player", {})
        player_name = player.get("name", "Unknown") if player else "Unknown"
        minute = inc.get("time", 0)
        added_time = inc.get("addedTime", 0)
        
        # Minuto con tiempo añadido
        minute_str = f"{minute}'"
        if added_time:
            minute_str = f"{minute}+{added_time}'"
        
        if inc_type == "goal":
            is_own = inc.get("incidentClass", "").lower() == "owngoal"
            
            if is_own:
                if is_home:
                    away_og.append(f"{player_name} ({minute_str})")
                else:
                    home_og.append(f"{player_name} ({minute_str})")
            else:
                if is_home:
                    home_scorers.append(player_name)
                    home_minutes.append(minute_str)
                else:
                    away_scorers.append(player_name)
                    away_minutes.append(minute_str)
                
                # Asistencia
                assist = inc.get("assist", {})
                assist_name = assist.get("name", "") if assist else ""
                if assist_name:
                    if is_home:
                        home_assists_list.append(f"{assist_name} ({minute_str})")
                    else:
                        away_assists_list.append(f"{assist_name} ({minute_str})")
        
        elif inc_type == "card":
            card_class = inc.get("incidentClass", "").lower()
            if card_class == "yellow":
                if is_home:
                    home_yellow.append(f"{player_name} ({minute_str})")
                else:
                    away_yellow.append(f"{player_name} ({minute_str})")
            elif card_class in ["red", "yellowred"]:
                if is_home:
                    home_red.append(f"{player_name} ({minute_str})")
                else:
                    away_red.append(f"{player_name} ({minute_str})")
    
    resultado["home_goal_scorers"] = "; ".join(home_scorers)
    resultado["away_goal_scorers"] = "; ".join(away_scorers)
    resultado["home_goal_minutes"] = "; ".join(home_minutes)
    resultado["away_goal_minutes"] = "; ".join(away_minutes)
    resultado["home_assists"] = "; ".join(home_assists_list)
    resultado["away_assists"] = "; ".join(away_assists_list)
    resultado["home_yellow_cards"] = "; ".join(home_yellow)
    resultado["away_yellow_cards"] = "; ".join(away_yellow)
    resultado["home_red_cards"] = "; ".join(home_red)
    resultado["away_red_cards"] = "; ".join(away_red)
    resultado["home_own_goals"] = "; ".join(home_og)
    resultado["away_own_goals"] = "; ".join(away_og)
    resultado["total_goals"] = len(home_scorers) + len(away_scorers) + len(home_og) + len(away_og)
    resultado["total_cards"] = len(home_yellow) + len(away_yellow) + len(home_red) + len(away_red)
    
    return resultado

def parsear_alineaciones(lineup_data: dict) -> dict:
    """Extrae formaciones y titulares"""
    resultado = {
        "home_formation": "",
        "away_formation": "",
        "home_starting_xi": "",
        "away_starting_xi": "",
        "home_subs": "",
        "away_subs": "",
    }
    
    if not lineup_data:
        return resultado
    
    # Formaciones
    resultado["home_formation"] = lineup_data.get("home", {}).get("formation", "")
    resultado["away_formation"] = lineup_data.get("away", {}).get("formation", "")
    
    # Titulares
    home_xi = []
    for player in lineup_data.get("home", {}).get("startingXI", []):
        name = player.get("player", {}).get("name", "")
        if name:
            home_xi.append(name)
    resultado["home_starting_xi"] = "; ".join(home_xi[:11])
    
    away_xi = []
    for player in lineup_data.get("away", {}).get("startingXI", []):
        name = player.get("player", {}).get("name", "")
        if name:
            away_xi.append(name)
    resultado["away_starting_xi"] = "; ".join(away_xi[:11])
    
    # Suplentes
    home_subs = []
    for player in lineup_data.get("home", {}).get("substitutes", []):
        name = player.get("player", {}).get("name", "")
        if name:
            home_subs.append(name)
    resultado["home_subs"] = "; ".join(home_subs[:7])
    
    away_subs = []
    for player in lineup_data.get("away", {}).get("substitutes", []):
        name = player.get("player", {}).get("name", "")
        if name:
            away_subs.append(name)
    resultado["away_subs"] = "; ".join(away_subs[:7])
    
    return resultado

# ===================== FILTROS =====================

def es_liga_deseada(nombre_liga: str) -> bool:
    if not nombre_liga:
        return False
    
    nombre_liga_lower = nombre_liga.lower()
    
    for excluir in PALABRAS_EXCLUIR:
        if excluir in nombre_liga_lower:
            return False
    
    for deseada in LIGAS_DESEADAS:
        if deseada in nombre_liga_lower:
            return True
    
    return False

def es_partido_finalizado(evento: dict) -> bool:
    status = evento.get("status", {})
    status_code = status.get("code")
    
    if status_code == 100:
        return True
    
    status_desc = str(status.get("description", "")).lower()
    finished_keywords = ["finished", "ended", "ft", "full time"]
    
    return any(keyword in status_desc for keyword in finished_keywords)

# ===================== PROCESAMIENTO =====================

def procesar_dia_futbol(fecha: str) -> int:
    """Procesa todos los partidos de fútbol de una fecha con estadísticas completas"""
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url, sport="football")
    
    if not data:
        logging.error(f"❌ No se pudo obtener datos para {fecha}")
        return 0

    eventos = data.get("events", [])
    logging.info(f"📊 Total eventos: {len(eventos)}")
    
    if not eventos:
        return 0
    
    # Filtrar partidos
    candidatos = []
    for e in eventos:
        if not es_partido_finalizado(e):
            continue
        
        tournament = e.get("tournament", {})
        nombre_liga = tournament.get("name", "")
        
        if es_liga_deseada(nombre_liga):
            candidatos.append(e)
    
    if not candidatos:
        return 0

    logging.info(f"✅ {len(candidatos)} partidos encontrados (descargando estadísticas...)")

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
            
            if home_goals == 0:
                home_goals = h_score.get("display", 0)
            if away_goals == 0:
                away_goals = a_score.get("display", 0)
            
            tournament = evento.get("tournament", {})
            nombre_liga = tournament.get("name", "Unknown")
            
            # DATOS BÁSICOS
            partido = {
                "event_id": event_id,
                "liga": nombre_liga,
                "tourney_id": tournament.get("id"),
                "tourney_name": tournament.get("name"),
                "tourney_season": evento.get("season", {}).get("name", ""),
                "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "round_number": evento.get("roundInfo", {}).get("round", 0),
                "home_team_id": home.get("id"),
                "home_team_name": home.get("name"),
                "away_team_id": away.get("id"),
                "away_team_name": away.get("name"),
                "home_goals": int(home_goals) if home_goals else 0,
                "away_goals": int(away_goals) if away_goals else 0,
                "home_ht_goals": h_score.get("period1", 0),
                "away_ht_goals": a_score.get("period1", 0),
                "home_et_goals": h_score.get("overtime"),
                "away_et_goals": a_score.get("overtime"),
                "home_pen_goals": h_score.get("penalties"),
                "away_pen_goals": a_score.get("penalties"),
                "result": "H" if int(home_goals) > int(away_goals) else ("A" if int(away_goals) > int(home_goals) else "D"),
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }
            
            # ESTADÍSTICAS DETALLADAS
            logging.info(f"  [{i:3d}/{len(candidatos)}] 📊 Descargando estadísticas: {home.get('name')} vs {away.get('name')}")
            
            stats_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics", sport="football")
            if stats_raw:
                partido.update(parsear_estadisticas_completas(stats_raw))
            
            # GOLEADORES Y TARJETAS
            incidents_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/incidents", sport="football")
            if incidents_raw:
                partido.update(parsear_goleadores(incidents_raw))
            
            # ALINEACIONES
            lineup_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/lineups", sport="football")
            if lineup_raw:
                partido.update(parsear_alineaciones(lineup_raw))
            
            buffer.append(partido)
            logging.info(f"      ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | {len(partido)} campos guardados")

            if len(buffer) >= GUARDAR_CADA_N_PARTIDOS:
                append_to_csv(buffer, ARCHIVO_FUTBOL)
                buffer.clear()
                
        except Exception as e:
            logging.error(f"💥 Error evento {event_id}: {e}")

    if buffer:
        append_to_csv(buffer, ARCHIVO_FUTBOL)
    
    return len(candidatos)

def append_to_csv(partidos: list, archivo: str):
    """Guarda partidos en CSV con todas las columnas"""
    if not partidos:
        return
    
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    df_nuevo = pd.DataFrame(partidos)
    
    if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
        try:
            df_viejo = pd.read_csv(archivo)
            if len(df_viejo) > 0:
                # Combinar y eliminar duplicados
                df_final = pd.concat([df_viejo, df_nuevo], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=["event_id"], keep="last")
                df_final.to_csv(archivo, index=False)
                logging.info(f"💾 CSV actualizado: {len(df_final)} registros | +{len(df_nuevo)} nuevos")
            else:
                df_nuevo.to_csv(archivo, index=False)
                logging.info(f"💾 CSV creado con {len(df_nuevo)} registros")
        except Exception as e:
            logging.error(f"Error al leer CSV: {e}")
            df_nuevo.to_csv(archivo, index=False)
    else:
        df_nuevo.to_csv(archivo, index=False)
        logging.info(f"💾 CSV creado con {len(df_nuevo)} registros")

# ===================== MAIN =====================

if __name__ == "__main__":
    logging.info("="*60)
    logging.info("🚀 INICIANDO SCRAPER DE FÚTBOL (ESTADÍSTICAS COMPLETAS)")
    logging.info("="*60)
    logging.info(f"🎯 Ligas configuradas: {len(LIGAS_DESEADAS)}")
    
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    
    # Usar la fecha actual del servidor
    hoy = datetime.now().date()
    ayer = hoy - timedelta(days=1)
    
    logging.info(f"📅 Fecha del servidor: {hoy}")
    logging.info(f"📅 Procesando partidos de: {ayer} y {hoy}")
    
    fechas_a_procesar = [ayer.strftime("%Y-%m-%d"), hoy.strftime("%Y-%m-%d")]
    total_partidos = 0
    
    for idx, fecha in enumerate(fechas_a_procesar, 1):
        logging.info(f"\n{'='*50}")
        logging.info(f"📆 [{idx}/2] Procesando fecha: {fecha}")
        logging.info(f"{'='*50}")
        
        partidos = procesar_dia_futbol(fecha)
        total_partidos += partidos
        logging.info(f"📈 Partidos guardados para {fecha}: {partidos}")
        
        if idx < len(fechas_a_procesar):
            pausa = random.uniform(5, 10)
            logging.info(f"⏱️  Esperando {pausa:.1f} segundos...")
            time.sleep(pausa)
    
    # Resumen final
    logging.info(f"\n{'='*60}")
    logging.info(f"✅ ¡SCRAPING COMPLETADO!")
    logging.info(f"{'='*60}")
    logging.info(f"⚽ Total partidos descargados: {total_partidos}")
    
    if os.path.exists(ARCHIVO_FUTBOL) and os.path.getsize(ARCHIVO_FUTBOL) > 0:
        try:
            df = pd.read_csv(ARCHIVO_FUTBOL)
            logging.info(f"📊 Total en CSV: {len(df)} partidos")
            logging.info(f"📊 Columnas totales: {len(df.columns)}")
            
            # Mostrar columnas disponibles
            print("\n" + "="*80)
            print("📋 COLUMNAS DISPONIBLES EN EL CSV:")
            print("="*80)
            cols = list(df.columns)
            for i, col in enumerate(sorted(cols)):
                print(f"  {i+1:3d}. {col}")
            
            print("\n" + "="*80)
            print("🏆 EJEMPLO DE PARTIDO (último):")
            print("="*80)
            ultimo = df.iloc[-1]
            print(f"  Liga: {ultimo.get('liga', 'N/A')}")
            print(f"  Partido: {ultimo.get('home_team_name', 'N/A')} {int(ultimo.get('home_goals', 0))} - {int(ultimo.get('away_goals', 0))} {ultimo.get('away_team_name', 'N/A')}")
            print(f"  Goleadores local: {ultimo.get('home_goal_scorers', 'N/A')}")
            print(f"  Goleadores visita: {ultimo.get('away_goal_scorers', 'N/A')}")
            print(f"  Tarjetas amarillas local: {ultimo.get('home_yellow_cards', 'N/A')}")
            print(f"  Tarjetas rojas: {ultimo.get('home_red_cards', 'N/A')} / {ultimo.get('away_red_cards', 'N/A')}")
            
            # Mostrar estadísticas si existen
            stats_cols = [c for c in cols if 'possession' in c.lower() or 'shots' in c.lower() or 'pass' in c.lower()]
            if stats_cols:
                print(f"\n  Estadísticas disponibles: {', '.join(stats_cols[:5])}...")
                
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV: {e}")
    else:
        logging.info("ℹ️ No hay partidos guardados")
