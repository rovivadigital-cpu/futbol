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

# TODAS LAS LIGAS (usando nombres para coincidencia parcial)
LIGAS_DESEADAS = [
    # CONMEBOL
    "libertadores",
    "sudamericana",
    # UEFA
    "champions league",
    "europa league",
    "europa conference league",
    "club world championship",
    # Inglaterra
    "premier league",
    "championship",
    "league one",
    # España
    "laliga",
    "laliga 2",
    # Alemania
    "bundesliga",
    "2. bundesliga",
    # Italia
    "serie a",
    "serie b",
    # Francia
    "ligue 1",
    "ligue 2",
    # USA
    "mls",
    "nwsl",
    # Arabia Saudita
    "saudi pro league",
    # Argentina
    "liga profesional",
    "primera nacional",
    # Australia
    "a-league",
    "npl capital football",
    # Austria
    "bundesliga",
    # Bélgica
    "pro league",
    # Bolivia
    "division profesional",
    # Brasil
    "brasileirao serie a",
    "brasileirao serie b",
    # Bulgaria
    "parva liga",
    # República Checa
    "1. liga",
    # Chile
    "primera division",
    # China
    "cfa super league",
    # Colombia
    "primera a apertura",
    "primera a clausura",
    "primera b",
    # Corea del Sur
    "k league 1",
    # Croacia
    "hnl",
    # Dinamarca
    "superliga",
    # Egipto
    "premier league",
    # Escocia
    "premiership",
    "championship",
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
    "j1 league",
    "j2 league",
    # Letonia
    "virsliga",
    # México
    "liga mx apertura",
    "liga mx clausura",
    # Noruega
    "eliteserien",
    # Países Bajos
    "eredivisie",
    "eerste divisie",
    # Polonia
    "ekstraklasa",
    # Rumania
    "superliga",
    # Sudáfrica
    "premiership",
    # Suecia
    "allsvenskan",
    "superettan",
    # Turquía
    "super lig",
    # Ucrania
    "premier league",
    # Suiza
    "super league",
]

# Palabras a EXCLUIR (para evitar ligas no deseadas como femenino, juvenil, etc.)
PALABRAS_EXCLUIR = [
    "women", "femenino", "femenina", "u19", "u20", "u21", "u23",
    "junior", "youth", "academy", "reserve", "sub", "femení",
    "womens", "futsal", "beach", "amateur", "cup", "copa"
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

def api_get(url: str, sport: str = "football", intentos: int = 4) -> dict:
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

def es_liga_deseada(nombre_liga: str) -> bool:
    """Verifica si el nombre de la liga coincide con alguna deseada"""
    if not nombre_liga:
        return False
    
    nombre_liga_lower = nombre_liga.lower()
    
    # Excluir ligas no deseadas
    for excluir in PALABRAS_EXCLUIR:
        if excluir in nombre_liga_lower:
            return False
    
    # Verificar si coincide con alguna liga deseada
    for deseada in LIGAS_DESEADAS:
        if deseada in nombre_liga_lower:
            return True
    
    return False

def es_partido_finalizado(evento: dict) -> bool:
    """Verifica si un partido ha finalizado"""
    status = evento.get("status", {})
    status_code = status.get("code")
    
    # Código 100 = finalizado en SofaScore
    if status_code == 100:
        return True
    
    # Verificar por descripción
    status_desc = str(status.get("description", "")).lower()
    finished_keywords = ["finished", "ended", "ft", "full time"]
    
    return any(keyword in status_desc for keyword in finished_keywords)

def procesar_dia_futbol(fecha: str) -> int:
    """Procesa todos los partidos de fútbol de una fecha específica"""
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    data = api_get(url, sport="football")
    
    if not data:
        logging.error(f"❌ No se pudo obtener datos para {fecha}")
        return 0

    eventos = data.get("events", [])
    logging.info(f"📊 Total eventos: {len(eventos)}")
    
    if not eventos:
        return 0
    
    # Filtrar partidos finalizados de ligas deseadas
    candidatos = []
    for e in eventos:
        if not es_partido_finalizado(e):
            continue
        
        # Obtener nombre de la liga
        tournament = e.get("tournament", {})
        nombre_liga = tournament.get("name", "")
        
        if es_liga_deseada(nombre_liga):
            candidatos.append(e)
    
    if not candidatos:
        # Mostrar sample de ligas disponibles
        ligas_vistas = set()
        for e in eventos[:15]:
            if es_partido_finalizado(e):
                t = e.get("tournament", {})
                ligas_vistas.add(t.get("name", "Unknown"))
        
        if ligas_vistas:
            logging.info(f"  ℹ️ Ligas disponibles (finalizados): {', '.join(list(ligas_vistas)[:8])}")
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

            home_goals = h_score.get("current", 0)
            away_goals = a_score.get("current", 0)
            
            # Si no hay current, intentar con normaltime
            if home_goals == 0:
                home_goals = h_score.get("normaltime", 0)
            if away_goals == 0:
                away_goals = a_score.get("normaltime", 0)
            
            tournament = evento.get("tournament", {})
            nombre_liga = tournament.get("name", "Unknown")
            
            partido = {
                "event_id": event_id,
                "liga": nombre_liga,
                "tourney_id": tournament.get("id"),
                "tourney_name": tournament.get("name"),
                "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "home_team_name": home.get("name"),
                "away_team_name": away.get("name"),
                "home_team_id": home.get("id"),
                "away_team_id": away.get("id"),
                "home_goals": int(home_goals) if home_goals else 0,
                "away_goals": int(away_goals) if away_goals else 0,
                "result": "H" if int(home_goals) > int(away_goals) else ("A" if int(away_goals) > int(home_goals) else "D"),
                "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            }

            buffer.append(partido)
            logging.info(f"  [{i:3d}/{len(candidatos)}] ✅ {home.get('name')} {home_goals}-{away_goals} {away.get('name')} | {nombre_liga}")

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
            if len(df_viejo) > 0:
                df_final = pd.concat([df_viejo, df_nuevo]).drop_duplicates(subset=["event_id"], keep="last")
                df_final.to_csv(archivo, index=False)
                logging.info(f"💾 CSV actualizado: {len(df_final)} registros")
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
    logging.info("🚀 INICIANDO SCRAPER DE FÚTBOL")
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
        logging.info(f"📈 Partidos guardados: {partidos}")
        
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
                print("🏆 PARTIDOS GUARDADOS (últimos 20):")
                print("="*80)
                for _, row in df.tail(20).iterrows():
                    print(f"  {row['tourney_date']} | {row['liga'][:40]:40} | {row['home_team_name']} {int(row['home_goals'])}-{int(row['away_goals'])} {row['away_team_name']}")
                print("="*80)
        except Exception as e:
            logging.warning(f"No se pudo leer el CSV: {e}")
    else:
        logging.info("ℹ️ No hay partidos guardados")
