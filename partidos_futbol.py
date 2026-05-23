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
GUARDAR_CADA_N_PARTIDOS = 5
PAUSA_ENTRE_REQUESTS = 0.6
CHROME_VERSIONS = ["chrome136", "chrome131", "chrome124"]

# ===================== CONFIG FÚTBOL =====================
ARCHIVO_FUTBOL = os.path.join(CARPETA_SALIDA, "futbol_historico.csv")

# LIGAS CON SU PAÍS (nombre de liga -> país)
LIGAS_CON_PAIS = {
    # CONMEBOL
    "libertadores": "Sudamérica",
    "sudamericana": "Sudamérica",
    # UEFA
    "champions league": "Europa",
    "europa league": "Europa",
    "europa conference league": "Europa",
    "club world championship": "Mundial",
    # Inglaterra
    "premier league": "Inglaterra",
    "championship": "Inglaterra",
    "league one": "Inglaterra",
    # España
    "laliga": "España",
    "laliga 2": "España",
    # Alemania
    "bundesliga": "Alemania",
    "2. bundesliga": "Alemania",
    # Italia
    "serie a": "Italia",
    "serie b": "Italia",
    # Francia
    "ligue 1": "Francia",
    "ligue 2": "Francia",
    # USA
    "mls": "Estados Unidos",
    "nwsl": "Estados Unidos",
    "mls next pro": "Estados Unidos",
    "usl championship": "Estados Unidos",
    # Arabia Saudita
    "saudi pro league": "Arabia Saudita",
    # Argentina
    "liga profesional": "Argentina",
    "primera nacional": "Argentina",
    # Australia
    "a-league": "Australia",
    "npl capital football": "Australia",
    # Austria
    "bundesliga": "Austria",
    # Bélgica
    "pro league": "Bélgica",
    # Bolivia
    "division profesional": "Bolivia",
    # Brasil
    "brasileirao serie a": "Brasil",
    "brasileirao serie b": "Brasil",
    # Bulgaria
    "parva liga": "Bulgaria",
    # República Checa
    "1. liga": "República Checa",
    "czech first league": "República Checa",
    # Chile
    "primera division": "Chile",
    # China
    "cfa super league": "China",
    # Colombia
    "primera a apertura": "Colombia",
    "primera a clausura": "Colombia",
    "primera b": "Colombia",
    # Corea del Sur
    "k league 1": "Corea del Sur",
    # Croacia
    "hnl": "Croacia",
    # Dinamarca
    "superliga": "Dinamarca",
    # Egipto
    "premier league": "Egipto",
    "egyptian premier league": "Egipto",
    # Escocia
    "premiership": "Escocia",
    "championship": "Escocia",
    "scottish premiership": "Escocia",
    # Eslovenia
    "prvaliga": "Eslovenia",
    # Estonia
    "premium liiga": "Estonia",
    # Finlandia
    "veikkausliiga": "Finlandia",
    # Grecia
    "super league": "Grecia",
    "stoiximan super league": "Grecia",
    # Indonesia
    "liga 1": "Indonesia",
    # Japón
    "j1 league": "Japón",
    "j2 league": "Japón",
    # Letonia
    "virsliga": "Letonia",
    # México
    "liga mx apertura": "México",
    "liga mx clausura": "México",
    # Noruega
    "eliteserien": "Noruega",
    # Países Bajos
    "eredivisie": "Países Bajos",
    "eerste divisie": "Países Bajos",
    # Polonia
    "ekstraklasa": "Polonia",
    # Rumania
    "superliga": "Rumania",
    # Sudáfrica
    "premiership": "Sudáfrica",
    # Suecia
    "allsvenskan": "Suecia",
    "superettan": "Suecia",
    "damallsvenskan": "Suecia",
    # Turquía
    "super lig": "Turquía",
    # Ucrania
    "premier league": "Ucrania",
    # Suiza
    "super league": "Suiza",
    # Otros
    "austrian bundesliga": "Austria",
    "swiss super league": "Suiza",
    "chinese super league": "China",
    "canadian premier league": "Canadá",
    "philippines football league": "Filipinas",
    "kazakhstan premier league": "Kazajistán",
    "bahrain premier league": "Baréin",
    "ghana premier league": "Ghana",
    "cyprus league": "Chipre",
    "serie a femminile": "Italia",
    "frauen-bundesliga": "Alemania",
    "prva liga": "Eslovenia",
    "niké liga": "Eslovaquia",
    "super liga": "Moldavia",
    "liga pro serie a": "Ecuador",
    "primera division": "Uruguay",
}

PALABRAS_EXCLUIR = [
    "women", "femenino", "femenina", "u19", "u20", "u21", "u23",
    "junior", "youth", "academy", "reserve", "sub", "femení",
    "womens", "futsal", "beach", "amateur", "cup", "u21", "u19"
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
    except Exception:
        return {}
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
            time.sleep(PAUSA_ENTRE_REQUESTS + random.uniform(0.2, 0.9))
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

# ===================== ESTADÍSTICAS =====================

def obtener_pais_liga(nombre_liga: str) -> str:
    """Devuelve el país de la liga según el nombre"""
    if not nombre_liga:
        return "Desconocido"
    
    nombre_liga_lower = nombre_liga.lower()
    
    for clave, pais in LIGAS_CON_PAIS.items():
        if clave in nombre_liga_lower:
            return pais
    
    return "Desconocido"

def parsear_estadisticas_completas(stats_data: dict) -> dict:
    resultado = {}
    
    if not stats_data:
        return resultado
    
    for periodo in stats_data.get("statistics", []):
        periodo_nombre = periodo.get("period", "ALL").upper()
        
        for grupo in periodo.get("groups", []):
            for item in grupo.get("statisticsItems", []):
                nombre_raw = item.get("name", "")
                nombre = nombre_raw.lower().replace(" ", "_").replace(".", "").replace("-", "_")
                
                home_val = item.get("home", {})
                away_val = item.get("away", {})
                
                if isinstance(home_val, dict):
                    home_final = home_val.get("value", home_val.get("total", 0))
                    home_total = home_val.get("total", home_val.get("value", 0))
                    if home_total and home_total != home_final:
                        resultado[f"{periodo_nombre}_{nombre}_home"] = f"{home_final}/{home_total}"
                    else:
                        resultado[f"{periodo_nombre}_{nombre}_home"] = home_final
                else:
                    resultado[f"{periodo_nombre}_{nombre}_home"] = home_val
                
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

def parsear_xg_detallado(shotmap_data: dict) -> dict:
    resultado = {
        "home_xg_total": 0,
        "away_xg_total": 0,
        "home_shots": 0,
        "away_shots": 0,
        "home_shots_on_target": 0,
        "away_shots_on_target": 0,
        "home_big_chances": 0,
        "away_big_chances": 0,
        "home_big_chances_missed": 0,
        "away_big_chances_missed": 0,
        "home_xg_1st_half": 0,
        "away_xg_1st_half": 0,
        "home_xg_2nd_half": 0,
        "away_xg_2nd_half": 0,
    }
    
    if not shotmap_data:
        return resultado
    
    summary = shotmap_data.get("summary", {})
    if summary:
        resultado["home_xg_total"] = summary.get("home", {}).get("xg", 0)
        resultado["away_xg_total"] = summary.get("away", {}).get("xg", 0)
        resultado["home_shots"] = summary.get("home", {}).get("shots", 0)
        resultado["away_shots"] = summary.get("away", {}).get("shots", 0)
        resultado["home_shots_on_target"] = summary.get("home", {}).get("onTarget", 0)
        resultado["away_shots_on_target"] = summary.get("away", {}).get("onTarget", 0)
        resultado["home_big_chances"] = summary.get("home", {}).get("bigChances", 0)
        resultado["away_big_chances"] = summary.get("away", {}).get("bigChances", 0)
        resultado["home_big_chances_missed"] = summary.get("home", {}).get("bigChancesMissed", 0)
        resultado["away_big_chances_missed"] = summary.get("away", {}).get("bigChancesMissed", 0)
    
    periods = shotmap_data.get("periods", {})
    if periods:
        for period, data in periods.items():
            if "1" in period or "FIRST" in period.upper():
                resultado["home_xg_1st_half"] = data.get("home", {}).get("xg", 0)
                resultado["away_xg_1st_half"] = data.get("away", {}).get("xg", 0)
            elif "2" in period or "SECOND" in period.upper():
                resultado["home_xg_2nd_half"] = data.get("home", {}).get("xg", 0)
                resultado["away_xg_2nd_half"] = data.get("away", {}).get("xg", 0)
    
    return resultado

# ===================== FILTROS =====================

def es_liga_deseada(nombre_liga: str) -> bool:
    if not nombre_liga:
        return False
    
    nombre_liga_lower = nombre_liga.lower()
    
    for excluir in PALABRAS_EXCLUIR:
        if excluir in nombre_liga_lower:
            return False
    
    for clave in LIGAS_CON_PAIS.keys():
        if clave in nombre_liga_lower:
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
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url, sport="football")
    
    if not data:
        logging.error(f"❌ No se pudo obtener datos para {fecha}")
        return 0

    eventos = data.get("events", [])
    logging.info(f"📊 Total eventos: {len(eventos)}")
    
    if not eventos:
        return 0
    
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

    logging.info(f"✅ {len(candidatos)} partidos encontrados")

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
            pais_liga = obtener_pais_liga(nombre_liga)
            
            # DATOS BÁSICOS (incluyendo país)
            partido = {
                "event_id": event_id,
                "pais": pais_liga,
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
            
            logging.info(f"  [{i:3d}/{len(candidatos)}] 📊 {home.get('name')} vs {away.get('name')} ({pais_liga})")
            
            # ESTADÍSTICAS
            stats_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics", sport="football")
            if stats_raw:
                partido.update(parsear_estadisticas_completas(stats_raw))
            
            # xG DETALLADO
            shotmap_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/shotmap", sport="football")
            if shotmap_raw:
                partido.update(parsear_xg_detallado(shotmap_raw))
            
            buffer.append(partido)
            
            home_xg = partido.get("home_xg_total", 0)
            away_xg = partido.get("away_xg_total", 0)
            logging.info(f"      ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | xG: {home_xg} - {away_xg} | {pais_liga}")

            if len(buffer) >= GUARDAR_CADA_N_PARTIDOS:
                append_to_csv(buffer, ARCHIVO_FUTBOL)
                buffer.clear()
                
        except Exception as e:
            logging.error(f"💥 Error evento {event_id}: {e}")

    if buffer:
        append_to_csv(buffer, ARCHIVO_FUTBOL)
    
    return len(candidatos)

def append_to_csv(partidos: list, archivo: str):
    if not partidos:
        return
    
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    df_nuevo = pd.DataFrame(partidos)
    
    if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
        try:
            df_viejo = pd.read_csv(archivo)
            if len(df_viejo) > 0:
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

def cargar_fechas_procesadas(archivo: str) -> set:
    if not os.path.exists(archivo) or os.path.getsize(archivo) == 0:
        return set()
    try:
        df = pd.read_csv(archivo)
        if 'tourney_date' in df.columns:
            return set(df['tourney_date'].dropna().unique())
    except Exception:
        pass
    return set()

# ===================== MAIN =====================

if __name__ == "__main__":
    logging.info("="*60)
    logging.info("🚀 INICIANDO SCRAPER DE FÚTBOL (CON PAÍS Y xG)")
    logging.info("="*60)
    logging.info(f"🎯 Ligas configuradas: {len(LIGAS_CON_PAIS)}")
    
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    
    fecha_inicio = datetime(2026, 1, 1).date()
    hoy = datetime.now().date()
    
    fechas_procesadas = cargar_fechas_procesadas(ARCHIVO_FUTBOL)
    
    todas_fechas = []
    fecha_actual = fecha_inicio
    while fecha_actual <= hoy:
        todas_fechas.append(fecha_actual)
        fecha_actual += timedelta(days=1)
    
    fechas_a_procesar = [f for f in todas_fechas if f.strftime("%Y-%m-%d") not in fechas_procesadas]
    
    logging.info(f"📅 Fecha inicio: {fecha_inicio}")
    logging.info(f"📅 Fecha actual: {hoy}")
    logging.info(f"📅 Días a procesar: {len(fechas_a_procesar)}")
    
    if not fechas_a_procesar:
        logging.info("✅ No hay fechas nuevas para procesar")
        exit(0)
    
    total_partidos = 0
    
    for idx, fecha in enumerate(fechas_a_procesar, 1):
        fecha_str = fecha.strftime("%Y-%m-%d")
        logging.info(f"\n{'='*50}")
        logging.info(f"📆 [{idx}/{len(fechas_a_procesar)}] Procesando fecha: {fecha_str}")
        logging.info(f"{'='*50}")
        
        partidos = procesar_dia_futbol(fecha_str)
        total_partidos += partidos
        logging.info(f"📈 Partidos guardados para {fecha_str}: {partidos}")
        
        if idx < len(fechas_a_procesar):
            pausa = random.uniform(3, 7)
            logging.info(f"⏱️  Esperando {pausa:.1f} segundos...")
            time.sleep(pausa)
    
    logging.info(f"\n{'='*60}")
    logging.info(f"✅ ¡SCRAPING COMPLETADO!")
    logging.info(f"{'='*60}")
    logging.info(f"⚽ Total partidos descargados: {total_partidos}")
    
    if os.path.exists(ARCHIVO_FUTBOL) and os.path.getsize(ARCHIVO_FUTBOL) > 0:
        try:
            df = pd.read_csv(ARCHIVO_FUTBOL)
            logging.info(f"📊 Total en CSV: {len(df)} partidos")
            
            print("\n" + "="*80)
            print("🏆 PARTIDOS POR PAÍS:")
            print("="*80)
            if 'pais' in df.columns:
                paises_count = df['pais'].value_counts()
                for pais, count in paises_count.items():
                    print(f"  {pais}: {count} partidos")
            
            print("\n" + "="*80)
            print("📋 EJEMPLO DE DATOS (últimos 5):")
            print("="*80)
            if len(df) > 0:
                for _, row in df.tail(5).iterrows():
                    print(f"  {row.get('tourney_date', 'N/A')} | {row.get('pais', 'N/A'):15} | {row.get('liga', 'N/A')[:30]:30} | {row.get('home_team_name', 'N/A')} {int(row.get('home_goals', 0))}-{int(row.get('away_goals', 0))} {row.get('away_team_name', 'N/A')}")
                
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV: {e}")
