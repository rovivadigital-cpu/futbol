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
    "champions league", "europa league", "europa conference league",
    "premier league", "championship",
    "laliga", "laliga 2",
    "bundesliga", "2. bundesliga",
    "serie a", "serie b",
    "ligue 1", "ligue 2",
    "mls", "nwsl",
    "saudi pro league",
    "liga profesional", "primera nacional",
    "pro league", "brasileirao serie a", "brasileirao serie b",
    "primera a apertura", "primera a clausura",
    "k league 1", "hnl", "superliga",
    "premiership", "veikkausliiga",
    "j1 league", "j2 league", "virsliga",
    "liga mx apertura", "liga mx clausura",
    "eliteserien", "eredivisie", "ekstraklasa", "allsvenskan",
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

# ===================== CÁLCULO DE XG ESTIMADO =====================

def calcular_xG_estimado(stats: dict) -> dict:
    """
    Calcula xG cuando no está disponible en los datos originales
    Basado en big chances y tiros a puerta
    """
    # Si ya tiene xG, no calcular
    if stats.get("expected_goals_home") is not None and stats.get("expected_goals_away") is not None:
        return {
            "expected_goals_home": stats.get("expected_goals_home"),
            "expected_goals_away": stats.get("expected_goals_away")
        }
    
    # Obtener estadísticas disponibles
    tiros_puerta_home = stats.get("shots_on_target_home", 0)
    tiros_puerta_away = stats.get("shots_on_target_away", 0)
    big_chances_home = stats.get("big_chances_home", 0)
    big_chances_away = stats.get("big_chances_away", 0)
    tiros_totales_home = stats.get("total_shots_home", 0)
    tiros_totales_away = stats.get("total_shots_away", 0)
    
    # Si tiene big chances (más preciso)
    if big_chances_home > 0 or big_chances_away > 0:
        xG_home = (tiros_puerta_home * 0.28) + (big_chances_home * 0.35)
        xG_away = (tiros_puerta_away * 0.28) + (big_chances_away * 0.35)
    else:
        # Solo con tiros a puerta
        xG_home = tiros_puerta_home * 0.30
        xG_away = tiros_puerta_away * 0.30
    
    # Limitar valores razonables
    xG_home = min(max(xG_home, 0.0), 5.0)
    xG_away = min(max(xG_away, 0.0), 5.0)
    
    return {
        "expected_goals_home": round(xG_home, 2),
        "expected_goals_away": round(xG_away, 2)
    }

# ===================== ESTADÍSTICAS CLAVE (SOLO LO NECESARIO) =====================

def parsear_estadisticas_clave(event_id: int) -> dict:
    """
    Extrae SOLO las estadísticas más importantes para predicción
    Features: xG, tiros, big chances, posesión, pases precisos
    """
    resultado = {}
    
    # Solo un endpoint - el de estadísticas normales
    url_stats = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    stats_data = api_get(url_stats, sport="football")
    
    if not stats_data:
        return resultado
    
    # Estadísticas clave para el modelo (las que pediste + algunas útiles)
    estadisticas_deseadas = [
        "expected_goals",      # xG - LA MÁS IMPORTANTE
        "total_shots",
        "shots_on_target",
        "big_chances",
        "ball_possession",
        "accurate_passes",
        "passes",              # Para calcular precisión si es necesario
        "goalkeeper_saves",    # Calidad defensiva
        "fouls",               # Disciplina
        "yellow_cards",        # Disciplina
        "corner_kicks",        # Dominio
        "offsides",            # Tipo de ataque
    ]
    
    for periodo in stats_data.get("statistics", []):
        periodo_nombre = periodo.get("period", "ALL").upper()
        
        # Solo nos interesa el período completo (ALL)
        if periodo_nombre != "ALL":
            continue
        
        for grupo in periodo.get("groups", []):
            for item in grupo.get("statisticsItems", []):
                nombre_raw = item.get("name", "")
                nombre = nombre_raw.lower().replace(" ", "_").replace(".", "").replace("-", "_")
                
                # Solo guardar las estadísticas que nos interesan
                if nombre not in estadisticas_deseadas:
                    continue
                
                home_val = item.get("home", {})
                away_val = item.get("away", {})
                
                # Valor home
                if isinstance(home_val, dict):
                    resultado[f"{nombre}_home"] = home_val.get("value", home_val.get("total", 0))
                else:
                    resultado[f"{nombre}_home"] = home_val
                
                # Valor away
                if isinstance(away_val, dict):
                    resultado[f"{nombre}_away"] = away_val.get("value", away_val.get("total", 0))
                else:
                    resultado[f"{nombre}_away"] = away_val
    
    # Calcular xG si no está presente
    xg_calculado = calcular_xG_estimado(resultado)
    if "expected_goals_home" not in resultado:
        resultado["expected_goals_home"] = xg_calculado["expected_goals_home"]
    if "expected_goals_away" not in resultado:
        resultado["expected_goals_away"] = xg_calculado["expected_goals_away"]
    
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
    """Procesa todos los partidos de fútbol de una fecha con estadísticas clave"""
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
            
            # DATOS BÁSICOS DEL PARTIDO (incluyendo resultado para target)
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
                "result": "H" if int(home_goals) > int(away_goals) else ("A" if int(away_goals) > int(home_goals) else "D"),
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }
            
            # ESTADÍSTICAS CLAVE PARA EL MODELO
            logging.info(f"  [{i:3d}/{len(candidatos)}] 📊 {home.get('name')} vs {away.get('name')}")
            
            stats = parsear_estadisticas_clave(event_id)
            if stats:
                partido.update(stats)
            
            buffer.append(partido)
            
            # Mostrar resumen de features importantes
            xg_h = partido.get('expected_goals_home', 'N/A')
            xg_a = partido.get('expected_goals_away', 'N/A')
            shots_h = partido.get('total_shots_home', 'N/A')
            shots_a = partido.get('total_shots_away', 'N/A')
            logging.info(f"      ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | xG: {xg_h}-{xg_a} | Tiros: {shots_h}-{shots_a}")

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
    logging.info("🚀 INICIANDO SCRAPER DE FÚTBOL (VERSIÓN PREDICCIÓN ML)")
    logging.info("="*60)
    logging.info(f"🎯 Ligas configuradas: {len(LIGAS_DESEADAS)}")
    logging.info("📊 Features a recolectar:")
    logging.info("   • expected_goals_home/away (xG)")
    logging.info("   • total_shots_home/away")
    logging.info("   • shots_on_target_home/away")
    logging.info("   • big_chances_home/away")
    logging.info("   • ball_possession_home")
    logging.info("   • accurate_passes_home/away")
    logging.info("   • goalkeeper_saves_home/away (opcional)")
    logging.info("   • fouls, yellow_cards, corner_kicks, offsides")
    
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    
    # ========== CONFIGURAR DÍAS A DESCARGAR ==========
    # Cambia el número 5 por la cantidad de días que quieras
    DIAS_A_DESCARGAR = 5  # <--- MODIFICA ESTE NÚMERO
    
    hoy = datetime.now().date()
    fechas_a_procesar = []
    
    for i in range(DIAS_A_DESCARGAR):
        fecha = hoy - timedelta(days=i)
        fechas_a_procesar.append(fecha.strftime("%Y-%m-%d"))
    
    logging.info(f"📅 Rango de fechas: {fechas_a_procesar[-1]} → {fechas_a_procesar[0]}")
    logging.info(f"📅 Procesando {len(fechas_a_procesar)} días")
    
    total_partidos = 0
    
    for idx, fecha in enumerate(fechas_a_procesar, 1):
        logging.info(f"\n{'='*50}")
        logging.info(f"📆 [{idx}/{len(fechas_a_procesar)}] Procesando fecha: {fecha}")
        logging.info(f"{'='*50}")
        
        partidos = procesar_dia_futbol(fecha)
        total_partidos += partidos
        logging.info(f"📈 Partidos guardados hoy: {partidos}")
        
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
            print("📋 FEATURES DISPONIBLES PARA TU MODELO ML:")
            print("="*80)
            
            # Mostrar las features clave
            features_clave = [
                'expected_goals_home', 'expected_goals_away',
                'total_shots_home', 'total_shots_away',
                'shots_on_target_home', 'shots_on_target_away',
                'big_chances_home', 'big_chances_away',
                'ball_possession_home',
                'accurate_passes_home', 'accurate_passes_away',
                'home_goals', 'away_goals', 'result'
            ]
            
            print("\n✅ Features disponibles para entrenamiento:")
            for f in features_clave:
                if f in df.columns:
                    print(f"  ✓ {f}")
                else:
                    print(f"  ✗ {f} (no disponible)")
            
            # Mostrar un ejemplo
            if len(df) > 0:
                print("\n" + "="*80)
                print("🏆 EJEMPLO DE DATOS PARA ML:")
                print("="*80)
                ultimo = df.iloc[-1]
                print(f"  Liga: {ultimo.get('liga', 'N/A')}")
                print(f"  Partido: {ultimo.get('home_team_name', 'N/A')} vs {ultimo.get('away_team_name', 'N/A')}")
                print(f"  Resultado: {int(ultimo.get('home_goals', 0))} - {int(ultimo.get('away_goals', 0))} ({ultimo.get('result', 'N/A')})")
                print(f"\n  Features:")
                print(f"    xG: {ultimo.get('expected_goals_home', 'N/A')} - {ultimo.get('expected_goals_away', 'N/A')}")
                print(f"    Tiros totales: {ultimo.get('total_shots_home', 'N/A')} - {ultimo.get('total_shots_away', 'N/A')}")
                print(f"    Tiros a puerta: {ultimo.get('shots_on_target_home', 'N/A')} - {ultimo.get('shots_on_target_away', 'N/A')}")
                print(f"    Big chances: {ultimo.get('big_chances_home', 'N/A')} - {ultimo.get('big_chances_away', 'N/A')}")
                print(f"    Posesión: {ultimo.get('ball_possession_home', 'N/A')}%")
                print(f"    Pases precisos: {ultimo.get('accurate_passes_home', 'N/A')} - {ultimo.get('accurate_passes_away', 'N/A')}")
                
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV: {e}")
