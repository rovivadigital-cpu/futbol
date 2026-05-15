import pandas as pd
from datetime import datetime, timedelta
import logging
import os
import time
import json
from curl_cffi import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CARPETA_SALIDA = "datos"
ARCHIVO_PARTIDOS = os.path.join(CARPETA_SALIDA, "tenis_historico.csv")
ARCHIVO_CHECKPOINT = os.path.join(CARPETA_SALIDA, "checkpoint.json")  # Nuevo: guarda progreso
CIRCUITOS_NOMBRES = ["atp", "wta", "challenger"]
PAUSA_ENTRE_REQUESTS = 0.6

# CONFIGURACIÓN DE CHECKPOINTS
CHECKPOINT_POR_DIA = True           # Guardar después de cada día
CHECKPOINT_POR_PARTIDOS = 50        # Guardar cada 50 partidos (False para desactivar)
CHECKPOINT_POR_CIRCUITO = False      # Guardar después de cada circuito

ESTADOS_FINALIZADOS = ["finished", "completed", "ended", "closed", "final", "done"]

def _session():
    s = requests.Session(impersonate="chrome120")
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.sofascore.com/tennis",
        "Origin": "https://www.sofascore.com",
    })
    return s

SESSION = _session()

def cargar_checkpoint():
    """Carga el último estado del procesamiento"""
    if os.path.exists(ARCHIVO_CHECKPOINT):
        try:
            with open(ARCHIVO_CHECKPOINT, 'r') as f:
                checkpoint = json.load(f)
            logging.info(f"✅ Checkpoint cargado: última fecha procesada {checkpoint.get('ultima_fecha', 'N/A')}, "
                        f"total partidos: {checkpoint.get('total_partidos_acumulados', 0)}")
            return checkpoint
        except Exception as e:
            logging.warning(f"Error cargando checkpoint: {e}")
    return {"ultima_fecha": None, "ultimo_indice_dia": -1, "total_partidos_acumulados": 0}

def guardar_checkpoint(fecha_actual, indice_dia, total_partidos):
    """Guarda el progreso actual"""
    checkpoint = {
        "ultima_fecha": fecha_actual,
        "ultimo_indice_dia": indice_dia,
        "total_partidos_acumulados": total_partidos,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open(ARCHIVO_CHECKPOINT, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        logging.debug(f"💾 Checkpoint guardado: {fecha_actual} - {total_partidos} partidos")
    except Exception as e:
        logging.warning(f"Error guardando checkpoint: {e}")

def guardar_por_checkpoint(partidos_pendientes, archivo, checkpoint_counter, motivo):
    """Guarda los partidos si se alcanza un checkpoint"""
    if not partidos_pendientes:
        return 0
    
    guardados = 0
    
    # Guardar por número de partidos
    if CHECKPOINT_POR_PARTIDOS and len(partidos_pendientes) >= CHECKPOINT_POR_PARTIDOS:
        append_to_csv(partidos_pendientes, archivo)
        guardados = len(partidos_pendientes)
        partidos_pendientes.clear()
        logging.info(f"🎯 Checkpoint por partidos ({CHECKPOINT_POR_PARTIDOS}): guardados {guardados} partidos")
    
    return guardados

def api_get(url: str, intentos: int = 3) -> dict:
    for intento in range(1, intentos + 1):
        try:
            time.sleep(PAUSA_ENTRE_REQUESTS)
            resp = SESSION.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                espera = 60 * intento
                logging.warning(f"Rate limit 429 -> esperando {espera}s...")
                time.sleep(espera)
            elif resp.status_code == 403:
                logging.warning(f"403 en {url} (intento {intento}/{intentos}). SofaScore bloqueó la request.")
                time.sleep(15 * intento)
            elif resp.status_code == 404:
                logging.debug(f"404 en {url} (no encontrado)")
                return {}
            else:
                logging.warning(f"HTTP {resp.status_code} en {url}")
                return {}
        except Exception as e:
            logging.warning(f"Excepcion en {url} (intento {intento}/{intentos}): {e}")
            time.sleep(5 * intento)
    return {}

def formatear_valor(val):
    if isinstance(val, dict):
        v = val.get("value", 0)
        t = val.get("total", 0)
        if t and t > 0:
            perc = (v / t) * 100
            return f"{v}/{t} ({perc:.0f}%)"
        return f"{v}/{t} (0%)"
    return val

def es_partido_sencillos(evento: dict) -> bool:
    tourney_name = evento.get("tournament", {}).get("name", "").lower()
    cat_name = evento.get("tournament", {}).get("category", {}).get("name", "").lower()
    round_name = evento.get("roundInfo", {}).get("name", "").lower()

    palabras_dobles = ["doubles", "dobles", "mixed", "mixtos", "double", "doble"]
    for palabra in palabras_dobles:
        if palabra in tourney_name or palabra in cat_name or palabra in round_name:
            return False

    home_name = evento.get("homeTeam", {}).get("name", "")
    away_name = evento.get("awayTeam", {}).get("name", "")

    indicadores_dobles = ["&", "/", " and ", " y "]
    for indicador in indicadores_dobles:
        if indicador in home_name or indicador in away_name:
            return False

    return True

def detectar_circuito(evento: dict):
    tournament = evento.get("tournament", {})
    categoria = tournament.get("category", {})

    if not isinstance(categoria, dict):
        return None

    cat_name = categoria.get("name", "").lower()
    cat_slug = categoria.get("slug", "").lower()
    tourney_name = tournament.get("name", "").lower()

    for circuito in CIRCUITOS_NOMBRES:
        if circuito in cat_name or circuito in cat_slug or circuito in tourney_name:
            return circuito.upper()

    return None

def get_estado(evento: dict) -> str:
    status = evento.get("status", {})

    if isinstance(status, str):
        return status.lower()

    if isinstance(status, dict):
        for campo in ["type", "name", "description", "code"]:
            valor = status.get(campo)
            if isinstance(valor, dict):
                return valor.get("name", "unknown").lower()
            elif isinstance(valor, str):
                return valor.lower()

    return "unknown"

def es_partido_finalizado(evento: dict) -> bool:
    estado = get_estado(evento)
    return estado in ESTADOS_FINALIZADOS

def get_eventos_del_dia(fecha):
    url = f"https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{fecha}"
    data = api_get(url)
    return data.get('events', [])

def parsear_estadisticas(stats_data: dict) -> dict:
    resultado = {}
    for periodo in stats_data.get("statistics", []):
        periodo_nombre = periodo.get("period", "ALL").upper()
        for grupo in periodo.get("groups", []):
            for item in grupo.get("statisticsItems", []):
                nombre = item.get("name", "").replace(" ", "_").lower()
                resultado[f"{periodo_nombre}_{nombre}_home"] = formatear_valor(item.get("home"))
                resultado[f"{periodo_nombre}_{nombre}_away"] = formatear_valor(item.get("away"))
    return resultado

def get_marcador_detallado(event_id: int, home_wins: bool) -> dict:
    url = f"https://api.sofascore.com/api/v1/event/{event_id}"
    data = api_get(url)
    evento = data.get("event", {})

    resultado = {}

    home_score = evento.get("homeScore", {})
    away_score = evento.get("awayScore", {})

    sets_jugados = []
    for i in range(1, 6):  # máximo 5 sets
        key = f"period{i}"
        home_games = home_score.get(key)
        away_games = away_score.get(key)
        if home_games is None or away_games is None:
            break
        if home_wins:
            sets_jugados.append(f"{home_games}-{away_games}")
        else:
            sets_jugados.append(f"{away_games}-{home_games}")

    resultado["score_detallado"] = " ".join(sets_jugados)
    resultado["num_sets"] = len(sets_jugados)

    for i, set_score in enumerate(sets_jugados, 1):
        partes = set_score.split("-")
        resultado[f"set{i}_winner"] = int(partes[0])
        resultado[f"set{i}_loser"] = int(partes[1])

    return resultado

def procesar_dia(fecha, checkpoint_counter):
    """Procesa un día completo con checkpoint interno"""
    eventos = get_eventos_del_dia(fecha)

    logging.info(f"📊 Total eventos encontrados en {fecha}: {len(eventos)}")

    categorias = {}
    for e in eventos:
        cat = e.get("tournament", {}).get("category", {}).get("name", "Unknown")
        categorias[cat] = categorias.get(cat, 0) + 1

    logging.info(f"Categorías encontradas: {categorias}")

    candidatos = []
    eventos_no_finalizados = 0
    eventos_dobles = 0
    eventos_filtrados = 0

    for evento in eventos:
        if not es_partido_finalizado(evento):
            eventos_no_finalizados += 1
            continue

        if not es_partido_sencillos(evento):
            eventos_dobles += 1
            continue

        circuito_nombre = detectar_circuito(evento)
        if circuito_nombre is None:
            eventos_filtrados += 1
            continue

        candidatos.append((evento, circuito_nombre))

    logging.info(f"  - No finalizados: {eventos_no_finalizados}")
    logging.info(f"  - Dobles/Mixtos: {eventos_dobles}")
    logging.info(f"  - Sin circuito detectado: {eventos_filtrados}")
    logging.info(f"  ✅ Partidos a procesar: {len(candidatos)}")

    partidos_dia = []
    checkpoint_counter_local = 0
    
    for i, (evento, circuito_nombre) in enumerate(candidatos, 1):
        try:
            event_id = evento.get("id")
            tournament_data = evento.get("tournament", {})
            home_team = evento.get("homeTeam", {})
            away_team = evento.get("awayTeam", {})

            home_id, home_name = home_team.get("id"), home_team.get("name")
            away_id, away_name = away_team.get("id"), away_team.get("name")

            home_score = evento.get("homeScore", {}).get("current", 0) or 0
            away_score = evento.get("awayScore", {}).get("current", 0) or 0
            home_wins = home_score > away_score

            winner_name, loser_name = (home_name, away_name) if home_wins else (away_name, home_name)
            winner_id, loser_id = (home_id, away_id) if home_wins else (away_id, home_id)

            surface = evento.get("groundType")
            if not surface:
                surface = tournament_data.get("groundType")
            if not surface:
                surface = evento.get("tournament", {}).get("surface", "Unknown")

            partido = {
                "event_id": event_id,
                "circuito": circuito_nombre,
                "tourney_id": tournament_data.get("id"),
                "tourney_name": tournament_data.get("name", "Unknown"),
                "tourney_date": fecha,
                "round": evento.get("roundInfo", {}).get("name", "Unknown"),
                "surface": surface,
                "winner_id": winner_id,
                "winner_name": winner_name,
                "loser_id": loser_id,
                "loser_name": loser_name,
                "winner_sets": home_score if home_wins else away_score,
                "loser_sets": away_score if home_wins else home_score,
                "scrape_date": datetime.now().strftime("%Y%m%d"),
            }

            # Marcador detallado por set
            try:
                marcador = get_marcador_detallado(event_id, home_wins)
                partido.update(marcador)
            except Exception as e:
                logging.debug(f"No se pudo obtener marcador detallado para evento {event_id}: {e}")

            # Estadísticas detalladas
            try:
                stats_raw = api_get(f"https://api.sofascore.com/api/v1/event/{event_id}/statistics")
                if stats_raw:
                    partido.update(parsear_estadisticas(stats_raw))
            except Exception as e:
                logging.debug(f"No se pudieron obtener estadísticas para evento {event_id}: {e}")

            partidos_dia.append(partido)
            checkpoint_counter_local += 1
            checkpoint_counter += 1
            
            logging.info(f"  [{i}/{len(candidatos)}] {winner_name} vs {loser_name} ({circuito_nombre}) | {partido.get('score_detallado', 'N/A')}")

            # Checkpoint cada N partidos dentro del mismo día
            if CHECKPOINT_POR_PARTIDOS and checkpoint_counter_local >= CHECKPOINT_POR_PARTIDOS:
                append_to_csv(partidos_dia, ARCHIVO_PARTIDOS)
                logging.info(f"🎯 Checkpoint intra-día: guardados {len(partidos_dia)} partidos de {fecha}")
                partidos_dia.clear()
                checkpoint_counter_local = 0

        except Exception as e:
            logging.warning(f"Error procesando evento {evento.get('id')}: {e}")
            continue

    # Guardar lo que queda del día
    if partidos_dia:
        append_to_csv(partidos_dia, ARCHIVO_PARTIDOS)
        logging.info(f"📅 Día {fecha} completado: {len(partidos_dia)} partidos guardados")
    
    return checkpoint_counter

def append_to_csv(partidos, archivo):
    if not partidos:
        logging.debug("No hay partidos para agregar")
        return

    os.makedirs(os.path.dirname(archivo), exist_ok=True)
    df_nuevo = pd.DataFrame(partidos)

    if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
        try:
            df_viejo = pd.read_csv(archivo)
            # Evitar duplicados por event_id
            df_combinado = pd.concat([df_viejo, df_nuevo])
            df_final = df_combinado.drop_duplicates(subset=["event_id"], keep='last')
            logging.info(f"📝 CSV actualizado: +{len(df_nuevo)} nuevos (total: {len(df_final)})")
        except Exception as e:
            logging.warning(f"Error al leer CSV existente: {e}")
            df_final = df_nuevo
    else:
        df_final = df_nuevo
        logging.info(f"✨ Nuevo archivo CSV creado con {len(df_final)} registros")

    df_final.to_csv(archivo, index=False)

if __name__ == "__main__":
    logging.info(f"🚀 Iniciando descarga de partidos históricos")
    logging.info(f"📁 Archivo destino: {ARCHIVO_PARTIDOS}")
    
    # Configuración de checkpoints
    if CHECKPOINT_POR_PARTIDOS:
        logging.info(f"⚙️ Checkpoint activado: cada {CHECKPOINT_POR_PARTIDOS} partidos")
    if CHECKPOINT_POR_DIA:
        logging.info(f"⚙️ Checkpoint activado: al finalizar cada día")
    
    # Cargar progreso anterior si existe
    checkpoint = cargar_checkpoint()
    fecha_inicio = datetime(2026, 1, 1).date()
    
    # Si hay checkpoint, retomar desde donde se quedó
    if checkpoint.get("ultima_fecha"):
        try:
            ultima_fecha_proc = datetime.strptime(checkpoint["ultima_fecha"], "%Y-%m-%d").date()
            fecha_inicio = max(fecha_inicio, ultima_fecha_proc + timedelta(days=1))
            logging.info(f"🔄 Reanudando desde {fecha_inicio} (última fecha procesada: {checkpoint['ultima_fecha']})")
        except:
            pass
    
    hoy = datetime.now().date()
    
    fechas = []
    actual = fecha_inicio
    while actual <= hoy:
        fechas.append(actual.strftime("%Y-%m-%d"))
        actual += timedelta(days=1)

    logging.info(f"📅 Fechas a procesar: {len(fechas)} días ({fechas[0]} a {fechas[-1]})")

    total_partidos_acum = checkpoint.get("total_partidos_acumulados", 0)
    
    for idx, fecha in enumerate(fechas):
        logging.info(f"\n{'='*60}")
        logging.info(f"📅 Procesando {fecha} ({idx+1}/{len(fechas)})...")
        logging.info(f"{'='*60}")
        
        try:
            total_partidos_acum = procesar_dia(fecha, total_partidos_acum)
            
            # Guardar checkpoint después de cada día completo
            if CHECKPOINT_POR_DIA:
                guardar_checkpoint(fecha, idx, total_partidos_acum)
                
        except Exception as e:
            logging.error(f"❌ Error crítico procesando {fecha}: {e}")
            logging.info(f"💾 Progreso guardado hasta {fecha}. Puedes reanudar ejecutando nuevamente.")
            guardar_checkpoint(fecha, idx, total_partidos_acum)
            break
        
        time.sleep(1)

    logging.info(f"\n{'='*60}")
    logging.info(f"✅ PROCESO COMPLETADO!")
    logging.info(f"📊 Total partidos procesados: {total_partidos_acum}")
    logging.info(f"📁 Archivo final: {ARCHIVO_PARTIDOS}")
    logging.info(f"{'='*60}")






