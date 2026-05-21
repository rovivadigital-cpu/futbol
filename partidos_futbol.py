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
PAUSA_ENTRE_REQUESTS = 1.5
CHROME_VERSIONS = ["chrome136", "chrome131", "chrome124"]

# ===================== CONFIG FÚTBOL =====================
ARCHIVO_FUTBOL = os.path.join(CARPETA_SALIDA, "futbol_historico.csv")

# TODAS LAS LIGAS
LIGAS_DESEADAS = [
    "libertadores", "sudamericana",
    "champions league", "europa league", "europa conference league", "club world championship",
    "premier league", "championship", "league one",
    "laliga", "laliga 2",
    "bundesliga", "2. bundesliga",
    "serie a", "serie b",
    "ligue 1", "ligue 2",
    "mls", "nwsl",
    "saudi pro league",
    "liga profesional", "primera nacional",
    "a-league", "npl capital football",
    "pro league", "division profesional",
    "brasileirao serie a", "brasileirao serie b",
    "parva liga", "1. liga", "primera division", "cfa super league",
    "primera a apertura", "primera a clausura", "primera b",
    "k league 1", "hnl", "superliga",
    "premiership", "championship", "prvaliga", "premium liiga",
    "veikkausliiga", "super league", "liga 1",
    "j1 league", "j2 league", "virsliga",
    "liga mx apertura", "liga mx clausura",
    "eliteserien", "eredivisie", "eerste divisie",
    "ekstraklasa", "allsvenskan", "superettan", "super lig", "super league",
]

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

# ===================== ESTADÍSTICAS =====================

def parsear_estadisticas_completas(stats_data: dict) -> dict:
    """
    Extrae TODAS las estadísticas del partido
    """
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
    """Procesa todos los partidos de fútbol de una fecha con estadísticas"""
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
        ligas_vistas = set()
        for e in eventos[:15]:
            if es_partido_finalizado(e):
                t = e.get("tournament", {})
                ligas_vistas.add(t.get("name", "Unknown"))
        if ligas_vistas:
            logging.info(f"  ℹ️ Ligas disponibles: {', '.join(list(ligas_vistas)[:8])}")
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
            
            # SOLO ESTADÍSTICAS (sin incidents ni lineups)
            logging.info(f"  [{i:3d}/{len(candidatos)}] 📊 {home.get('name')} vs {away.get('name')}")
            
            stats_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics", sport="football")
            if stats_raw:
                partido.update(parsear_estadisticas_completas(stats_raw))
            
            buffer.append(partido)
            logging.info(f"      ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | {len(partido)} campos")

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

# ===================== MAIN =====================

if __name__ == "__main__":
    logging.info("="*60)
    logging.info("🚀 INICIANDO SCRAPER DE FÚTBOL (SOLO ESTADÍSTICAS)")
    logging.info("="*60)
    logging.info(f"🎯 Ligas configuradas: {len(LIGAS_DESEADAS)}")
    
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    
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
        logging.info(f"📈 Partidos guardados: {partidos}")
        
        if idx < len(fechas_a_procesar):
            pausa = random.uniform(3, 6)
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
            logging.info(f"📊 Columnas totales: {len(df.columns)}")
            
            print("\n" + "="*80)
            print("📋 EJEMPLO DE ESTADÍSTICAS DISPONIBLES:")
            print("="*80)
            
            # Mostrar columnas de estadísticas
            stats_cols = [c for c in df.columns if any(x in c.lower() for x in 
                         ['possession', 'shots', 'passes', 'fouls', 'corners', 'offsides'])]
            
            if stats_cols:
                print("\nEstadísticas disponibles en el CSV:")
                for col in stats_cols[:15]:
                    print(f"  • {col}")
                if len(stats_cols) > 15:
                    print(f"  ... y {len(stats_cols)-15} columnas más")
            
            # Mostrar un ejemplo
            if len(df) > 0:
                print("\n" + "="*80)
                print("🏆 EJEMPLO DE PARTIDO:")
                print("="*80)
                ultimo = df.iloc[-1]
                print(f"  Liga: {ultimo.get('liga', 'N/A')}")
                print(f"  Partido: {ultimo.get('home_team_name', 'N/A')} {int(ultimo.get('home_goals', 0))} - {int(ultimo.get('away_goals', 0))} {ultimo.get('away_team_name', 'N/A')}")
                
                # Mostrar algunas estadísticas
                if 'ALL_possession_home' in df.columns:
                    print(f"  Posesión: {ultimo.get('ALL_possession_home', 'N/A')}% - {ultimo.get('ALL_possession_away', 'N/A')}%")
                if 'ALL_total_shots_home' in df.columns:
                    print(f"  Tiros: {ultimo.get('ALL_total_shots_home', 'N/A')} - {ultimo.get('ALL_total_shots_away', 'N/A')}")
                if 'ALL_accurate_passes_home' in df.columns:
                    print(f"  Pases completados: {ultimo.get('ALL_accurate_passes_home', 'N/A')} - {ultimo.get('ALL_accurate_passes_away', 'N/A')}")
                
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV: {e}")
