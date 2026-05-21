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

# Nombres de las ligas que queremos (sin IDs hardcodeados)
LIGAS_DESEADAS = [
    "Premier League",
    "LaLiga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "UEFA Champions League",
    "CONMEBOL Libertadores",
    "MLS",
    "Eredivisie",
    "Brasileirao Serie A",
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

# Diccionario que se llenará dinámicamente con los IDs correctos
LIGAS_OBJETIVO = {}  # nombre -> id
LIGAS_IDS_SET = set()

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
                logging.warning(f"⚠️ 403 en {url} (intento {i})")
                if _403_consecutivos >= 3:
                    time.sleep(120 * i)
                    SESSION = _nueva_sesion()
                    _403_consecutivos = 0
                else:
                    time.sleep(20 * i)
            elif r.status_code == 429:
                logging.warning(f"⚠️ 429 Too Many Requests en {url}")
                time.sleep(90 * i)
            elif r.status_code == 404:
                return {}
            else:
                logging.warning(f"⚠️ Status {r.status_code} en {url}")
                time.sleep(10 * i)
        except Exception as e:
            logging.error(f"Error en {url}: {e}")
            time.sleep(10 * i)
    return {}

def obtener_ids_ligas():
    """Obtiene los IDs correctos de las ligas desde la API"""
    global LIGAS_OBJETIVO, LIGAS_IDS_SET
    
    logging.info("🔍 Obteniendo IDs de ligas desde la API...")
    
    # Obtener torneos de fútbol
    url = "https://api.sofascore.com/api/v1/config/tournaments/football"
    data = api_get(url, sport="football")
    
    if not data:
        logging.error("❌ No se pudieron obtener los torneos")
        return False
    
    tournaments = data.get("tournaments", [])
    logging.info(f"📊 Total torneos encontrados: {len(tournaments)}")
    
    # Buscar las ligas que nos interesan
    encontradas = 0
    for tourney in tournaments:
        nombre = tourney.get("name", "")
        tourney_id = tourney.get("id")
        
        # Verificar si es una liga que nos interesa
        for liga_deseada in LIGAS_DESEADAS:
            if liga_deseada.lower() in nombre.lower():
                LIGAS_OBJETIVO[nombre] = tourney_id
                LIGAS_IDS_SET.add(tourney_id)
                encontradas += 1
                logging.info(f"  ✅ {nombre}: {tourney_id}")
                break
    
    logging.info(f"🎯 Ligas objetivo encontradas: {encontradas}")
    return encontradas > 0

def es_liga_objetivo(evento: dict) -> bool:
    """Verifica si el partido pertenece a una liga objetivo"""
    tournament = evento.get("tournament", {})
    
    # Intentar obtener el ID del torneo
    t_id = tournament.get("uniqueTournament", {}).get("id")
    if not t_id:
        t_id = tournament.get("id")
    
    return t_id in LIGAS_IDS_SET

def obtener_nombre_liga(evento: dict) -> str:
    """Devuelve el nombre de la liga"""
    tournament = evento.get("tournament", {})
    return tournament.get("name", "Unknown")

def es_partido_finalizado(evento: dict) -> bool:
    """Verifica si un partido ha finalizado"""
    status = evento.get("status", {})
    status_code = status.get("code")
    
    # Código 100 = finalizado en SofaScore
    if status_code == 100:
        return True
    
    # Verificar por descripción
    status_desc = str(status.get("description", "")).lower()
    finished_keywords = ["finished", "ended", "ft", "full time", "after et", "after penalties"]
    
    return any(keyword in status_desc for keyword in finished_keywords)

def procesar_dia_futbol(fecha: str) -> int:
    """Procesa todos los partidos de fútbol de una fecha específica"""
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url, sport="football")
    
    if not data:
        logging.error(f"❌ No se pudo obtener datos para {fecha}")
        return 0

    eventos = data.get("events", [])
    logging.info(f"📊 Total eventos en API para {fecha}: {len(eventos)}")
    
    if not eventos:
        return 0
    
    # Filtrar partidos finalizados de ligas objetivo
    candidatos = []
    for e in eventos:
        if es_partido_finalizado(e) and es_liga_objetivo(e):
            candidatos.append(e)
    
    if not candidatos:
        finalizados = [e for e in eventos if es_partido_finalizado(e)]
        ligas_encontradas = set()
        for e in eventos[:20]:
            t = e.get("tournament", {})
            ligas_encontradas.add(t.get("name", "Unknown"))
        
        logging.info(f"  ℹ️ Partidos finalizados: {len(finalizados)}")
        logging.info(f"  ℹ️ Ligas disponibles: {', '.join(list(ligas_encontradas)[:5])}")
        return 0

    logging.info(f"✅ {len(candidatos)} partidos encontrados para {fecha}")

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

            partido = {
                "event_id": event_id,
                "liga": obtener_nombre_liga(evento),
                "tourney_id": evento.get("tournament", {}).get("id"),
                "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "home_team_name": home.get("name"),
                "away_team_name": away.get("name"),
                "home_team_id": home.get("id"),
                "away_team_id": away.get("id"),
                "home_goals": int(home_goals),
                "away_goals": int(away_goals),
                "result": "H" if int(home_goals) > int(away_goals) else ("A" if int(away_goals) > int(home_goals) else "D"),
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }

            buffer.append(partido)
            logging.info(f"  [{i:3d}/{len(candidatos)}] ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | {partido['liga']}")

            if len(buffer) >= GUARDAR_CADA_N_PARTIDOS:
                append_to_csv(buffer, ARCHIVO_FUTBOL)
                buffer.clear()

        except Exception as e:
            logging.error(f"💥 Error evento {event_id}: {e}")

    if buffer:
        append_to_csv(buffer, ARCHIVO_FUTBOL)
    
    return len(candidatos)

def append_to_csv(partidos: list, archivo: str):
    """Guarda partidos en CSV evitando duplicados"""
    if not partidos:
        return
    
    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    df_nuevo = pd.DataFrame(partidos)
    
    if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
        try:
            df_viejo = pd.read_csv(archivo)
            df_final = pd.concat([df_viejo, df_nuevo]).drop_duplicates(subset=["event_id"], keep="last")
            df_final.to_csv(archivo, index=False)
            logging.info(f"💾 CSV actualizado: {len(df_final)} registros")
        except Exception as e:
            logging.error(f"Error al leer CSV: {e}")
            df_nuevo.to_csv(archivo, index=False)
    else:
        df_nuevo.to_csv(archivo, index=False)
        logging.info(f"💾 CSV creado con {len(df_nuevo)} registros")

# ===================== MAIN =====================

if __name__ == "__main__":
    logging.info("="*60)
    logging.info("🚀 INICIANDO SCRAPER DE FÚTBOL")
    logging.info("="*60)
    
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    
    # Obtener IDs de ligas primero
    if not obtener_ids_ligas():
        logging.error("❌ No se pudieron obtener las ligas objetivo. Saliendo...")
        exit(1)
    
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
            pausa = random.uniform(3, 7)
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
            
            if len(df) > 0:
                print("\n" + "="*80)
                print("🏆 PARTIDOS GUARDADOS:")
                print("="*80)
                for _, row in df.iterrows():
                    print(f"  {row['tourney_date']} | {row['liga']:35} | {row['home_team_name']} {int(row['home_goals'])}-{int(row['away_goals'])} {row['away_team_name']}")
                print("="*80)
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV: {e}")
    else:
        logging.info("ℹ️ No hay partidos para mostrar")
