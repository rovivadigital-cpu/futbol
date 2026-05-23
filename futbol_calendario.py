import pandas as pd
from datetime import datetime, timedelta
import os
import logging
from curl_cffi import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")

SUPERFICIE_MAP = {
    "artificial turf": "Césped Artificial",
    "natural grass":   "Césped Natural",
    "grass":           "Césped Natural",
    "turf":            "Césped Artificial",
    "indoor":          "Indoor",
}

def _session():
    s = requests.Session(impersonate="chrome120")
    s.headers.update({
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer":         "https://www.sofascore.com/football",
        "Origin":          "https://www.sofascore.com",
    })
    return s

SESSION   = _session()
_cache_liga = {}

def api_get(url):
    try:
        response = SESSION.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.warning(f"Error al llamar {url}: {e}")
    return {}

def normalizar_superficie(valor):
    if not valor:
        return None
    return SUPERFICIE_MAP.get(str(valor).lower(), str(valor).capitalize())

def obtener_info_liga(unique_id):
    """Obtiene nombre completo y país de la liga desde uniqueTournament."""
    if not unique_id:
        return {}, "Desconocida"
    if unique_id in _cache_liga:
        return _cache_liga[unique_id]

    url  = f"https://api.sofascore.com/api/v1/unique-tournament/{unique_id}"
    data = api_get(url)
    ut   = data.get("uniqueTournament", {})

    pais = (
        ut.get("category", {}).get("country", {}).get("name")
        or ut.get("category", {}).get("name", "Desconocido")
    )
    nombre_liga = ut.get("name", "Desconocida")

    resultado = {"nombre_liga": nombre_liga, "pais": pais}
    _cache_liga[unique_id] = resultado
    return resultado

def estado_partido(status_code):
    """Convierte el código de estado en texto legible."""
    ESTADOS = {
        "notstarted":  "Por jugar",
        "inprogress":  "En curso",
        "finished":    "Finalizado",
        "postponed":   "Postponido",
        "canceled":    "Cancelado",
        "interrupted": "Interrumpido",
    }
    return ESTADOS.get(str(status_code).lower(), str(status_code).capitalize())

def obtener_partidos_fecha(fecha_str):
    """Descarga todos los partidos de fútbol de una fecha dada (YYYY-MM-DD)."""
    logging.info(f"\nObteniendo partidos para: {fecha_str} ...")
    url    = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha_str}"
    data   = api_get(url)
    eventos = data.get("events", [])
    logging.info(f"  Eventos encontrados: {len(eventos)}")

    partidos = []
    for e in eventos:
        try:
            torneo_data = e.get("tournament", {})
            torneo      = torneo_data.get("name", "Desconocido")
            torneo_id   = torneo_data.get("id", "")
            categoria   = torneo_data.get("category", {}).get("name", "")
            pais        = torneo_data.get("category", {}).get("country", {}).get("name", categoria)

            unique_obj  = (
                torneo_data.get("uniqueTournament")
                or e.get("uniqueTournament")
                or {}
            )
            unique_id   = unique_obj.get("id", "")
            nombre_liga = unique_obj.get("name") or torneo

            # ── Equipos ──────────────────────────────────────────────
            home        = e.get("homeTeam", {}).get("name", "Unknown")
            home_id     = e.get("homeTeam", {}).get("id", "")
            home_pais   = e.get("homeTeam", {}).get("country", {}).get("name", "")
            away        = e.get("awayTeam", {}).get("name", "Unknown")
            away_id     = e.get("awayTeam", {}).get("id", "")
            away_pais   = e.get("awayTeam", {}).get("country", {}).get("name", "")

            # ── Fecha / hora ──────────────────────────────────────────
            timestamp  = e.get("startTimestamp")
            hora_local = "Sin hora"
            fecha      = fecha_str
            if timestamp:
                dt         = datetime.fromtimestamp(timestamp)
                hora_local = dt.strftime("%H:%M")
                fecha      = dt.strftime("%Y-%m-%d")

            # ── Marcador (si el partido ya empezó / terminó) ──────────
            score_home = e.get("homeScore", {}).get("current", "")
            score_away = e.get("awayScore", {}).get("current", "")
            marcador   = (
                f"{score_home}-{score_away}"
                if score_home != "" and score_away != ""
                else "-"
            )

            # ── Estado del partido ────────────────────────────────────
            status = e.get("status", {}).get("type", "")
            estado = estado_partido(status)

            # ── Ronda / jornada ───────────────────────────────────────
            ronda_info = e.get("roundInfo", {})
            ronda      = ronda_info.get("name") or (
                f"Jornada {ronda_info['round']}" if ronda_info.get("round") else ""
            )

            partidos.append({
                "Fecha":                         fecha,
                "Hora_Local":                    hora_local,
                "Pais":                          pais,
                "Competicion":                   nombre_liga,
                "Competicion_ID_Sofascore":      unique_id,
                "Torneo":                        torneo,
                "Torneo_ID_Sofascore":           torneo_id,
                "Ronda":                         ronda,
                "Equipo_Local":                  home,
                "Equipo_Local_ID_Sofascore":     home_id,
                "Pais_Local":                    home_pais,
                "Equipo_Visitante":              away,
                "Equipo_Visitante_ID_Sofascore": away_id,
                "Pais_Visitante":                away_pais,
                "Marcador":                      marcador,
                "Estado":                        estado,
            })
        except Exception as ex:
            logging.debug(f"  Error procesando evento: {ex}")

    return partidos

def obtener_calendario_futbol():
    hoy      = datetime.now()
    manana   = hoy + timedelta(days=1)
    hoy_str  = hoy.strftime("%Y-%m-%d")
    man_str  = manana.strftime("%Y-%m-%d")

    partidos_hoy    = obtener_partidos_fecha(hoy_str)
    partidos_manana = obtener_partidos_fecha(man_str)
    todos           = partidos_hoy + partidos_manana

    columnas = [
        "Fecha", "Hora_Local", "Pais", "Competicion", "Competicion_ID_Sofascore",
        "Torneo", "Torneo_ID_Sofascore", "Ronda",
        "Equipo_Local", "Equipo_Local_ID_Sofascore", "Pais_Local",
        "Equipo_Visitante", "Equipo_Visitante_ID_Sofascore", "Pais_Visitante",
        "Marcador", "Estado",
    ]

    os.makedirs("datos", exist_ok=True)
    archivo = os.path.join("datos", "calendar_futbol.csv")

    if todos:
        df = pd.DataFrame(todos, columns=columnas)
        df = df.sort_values(by=["Fecha", "Hora_Local"])
        df.to_csv(archivo, index=False, encoding="utf-8-sig")

        logging.info(f"\n¡Éxito! {len(todos)} partidos guardados en '{archivo}'.")
        logging.info(f"  → Hoy    ({hoy_str}):   {len(partidos_hoy)} partidos")
        logging.info(f"  → Mañana ({man_str}): {len(partidos_manana)} partidos")

        # ── Muestra por consola ──────────────────────────────────────
        print("\n--- Próximos 20 partidos (Hoy + Mañana) ---")
        muestra = df.assign(VS="vs")[
            ["Fecha", "Hora_Local", "Pais", "Competicion",
             "Equipo_Local", "VS", "Equipo_Visitante", "Estado"]
        ].head(20)
        print(muestra.to_string(index=False))

        print("\n--- Partidos por país ---")
        print(df["Pais"].value_counts().head(20).to_string())

        print("\n--- Partidos por competición (Top 15) ---")
        print(df["Competicion"].value_counts().head(15).to_string())
    else:
        df_vacio = pd.DataFrame(columns=columnas)
        df_vacio.to_csv(archivo, index=False, encoding="utf-8-sig")
        logging.info("No se encontraron partidos. El archivo ha sido limpiado.")

if __name__ == "__main__":
    obtener_calendario_futbol()
