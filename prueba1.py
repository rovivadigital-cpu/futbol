import os
import json
import csv
import time
import re
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from google.genai.errors import APIError  # Para capturar el error de cuota

# =====================================================================
# CONFIGURACIÓN MANUAL DE RANGO DE FECHAS (SISTEMA CON ANTI-CUOTA)
# =====================================================================
FECHA_INICIO = '2026-02-01'  
FECHA_FIN    = '2026-02-01'  
csv_filename = "partidos_estadisticas_historico.csv"
# =====================================================================

# 1. VALIDACIÓN ANTIDUPLICADOS
partidos_existentes = set()

if os.path.exists(csv_filename):
    print(f"Leyendo '{csv_filename}' existente para evitar duplicados...")
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header:
            try:
                idx_fecha = header.index("tourney_date")
                idx_local = header.index("home_team_name")
                idx_visita = header.index("away_team_name")
                
                for row in reader:
                    if len(row) > max(idx_fecha, idx_local, idx_visita):
                        llave = f"{row[idx_fecha]}_{row[idx_local]}_{row[idx_visita]}".strip().lower()
                        partidos_existentes.add(llave)
            except ValueError:
                print("Aviso: El CSV existente no tiene el formato esperado.")

print(f"-> Se encontraron {len(partidos_existentes)} partidos registrados previamente.\n")

if not os.path.exists(csv_filename):
    ENCABEZADOS_CSV = [
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
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(ENCABEZADOS_CSV)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")
client = genai.Client(api_key=api_key)

TORNEOS_IDS = {
    17: {"nombre": "Premier League", "pais": "England"},
    11539: {"nombre": "Primera A, Apertura", "pais": "Colombia"},
    8: {"nombre": "LaLiga", "pais": "Spain"},
    23: {"nombre": "Serie A", "pais": "Italy"}
}

fecha_hoy = datetime.now().strftime('%Y-%m-%d')
start_date = datetime.strptime(FECHA_INICIO, '%Y-%m-%d')
end_date = datetime.strptime(FECHA_FIN, '%Y-%m-%d')
delta = timedelta(days=1)

fecha_actual = start_date
while fecha_actual <= end_date:
    str_fecha_ayer = fecha_actual.strftime('%Y-%m-%d')
    mes_actual = fecha_actual.month
    
    print(f"\n==================================================")
    print(f" PROCESANDO FECHA: {str_fecha_ayer}")
    print(f"==================================================")
    
    for tor_id, info in TORNEOS_IDS.items():
        liga_nombre = info["nombre"]
        pais_nombre = info["pais"]
        
        if pais_nombre == "Colombia" and mes_actual == 1 and fecha_actual.day < 15:
            print(f"-> Saltando {liga_nombre} (Sin actividad oficial a principios de enero)")
            continue
            
        print(f"-> Buscando partidos de: {liga_nombre} ({pais_nombre})")
        
        prompt = f"""
        Busca en la web los partidos oficiales de fútbol de la liga '{liga_nombre}' ({pais_nombre}) que se jugaron y terminaron por completo el día {str_fecha_ayer}.
        
        Debes incluir todos los partidos disputados en esa fecha. Devuelve los datos en formato JSON plano, sin bloques de código markdown ni texto extra. Si no hubo partidos oficiales ese día, devuelve "partidos": [].
        
        Estructura exacta requerida:
        {{
          "partidos": [
            {{
              "round": "Jornada X",
              "round_number": "X",
              "home_team_name": "Nombre equipo local",
              "away_team_name": "Nombre equipo visitante",
              "home_goals": 0,
              "away_goals": 0,
              "home_ht_goals": 0,
              "away_ht_goals": 0,
              "home_et_goals": 0,
              "away_et_goals": 0,
              "home_pen_goals": 0,
              "away_pen_goals": 0,
              "result": "H, A o D",
              "ALL_ball_possession_home": 50.0,
              "ALL_ball_possession_away": 50.0,
              "ALL_expected_goals_home": 1.2,
              "ALL_expected_goals_away": 1.0,
              "ALL_big_chances_home": 1,
              "ALL_big_chances_away": 1,
              "ALL_total_shots_home": 10,
              "ALL_total_shots_away": 8,
              "ALL_goalkeeper_saves_home": 3,
              "ALL_goalkeeper_saves_away": 2,
              "ALL_corner_kicks_home": 5,
              "ALL_corner_kicks_away": 4,
              "ALL_fouls_home": 12,
              "ALL_fouls_away": 14,
              "ALL_passes_home": 400,
              "ALL_passes_away": 380,
              "ALL_yellow_cards_home": 2,
              "ALL_yellow_cards_away": 2,
              "ALL_shots_on_target_home": 4,
              "ALL_shots_on_target_away": 3,
              "ALL_offsides_home": 1,
              "ALL_offsides_away": 2,
              "ALL_accurate_passes_home": 320,
              "ALL_accurate_passes_away": 300,
              "ALL_red_cards_home": 0,
              "ALL_red_cards_away": 0
            }}
          ]
        }}
        
        Regla estricta: Si no encuentras alguna estadística avanzada para un partido real, no dejes campos vacíos ni uses null; estima valores numéricos proporcionales basados en los goles y tiros del encuentro para mantener el formato íntegro del JSON.
        """
        
        # Bucle de reintentos inteligente para combatir el error 429
        completado = False
        intentos = 0
        
        while not completado and intentos < 5:
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.1
                    )
                )
                
                texto_limpio = response.text.strip()
                if texto_limpio.startswith("```json"):
                    texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
                elif texto_limpio.startswith("```"):
                    texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()
                    
                data = json.loads(texto_limpio)
                partidos = data.get("partidos", [])
                
                if partidos:
                    partidos_nuevos_guardados = 0
                    with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        
                        for p in partidos:
                            local = str(p.get("home_team_name", "")).strip()
                            visita = str(p.get("away_team_name", "")).strip()
                            
                            if not local or not visita:
                                continue
                                
                            llave_partido = f"{str_fecha_ayer}_{local}_{visita}".strip().lower()
                            
                            if llave_partido in partidos_existentes:
                                print(f"   [IGNORADO] El partido {local} vs {visita} ya existe.")
                                continue
                            
                            partidos_existentes.add(llave_partido)
                            partidos_nuevos_guardados += 1
                            
                            row = [
                                "", pais_nombre, liga_nombre, "", liga_nombre, 
                                str_fecha_ayer[:4], str_fecha_ayer,
                                p.get("round", ""), p.get("round_number", ""),
                                "", local, "", visita,
                                p.get("home_goals", 0), p.get("away_goals", 0),
                                p.get("home_ht_goals", 0), p.get("away_ht_goals", 0),
                                p.get("home_et_goals", 0), p.get("away_et_goals", 0),
                                p.get("home_pen_goals", 0), p.get("away_pen_goals", 0),
                                p.get("result", ""), fecha_hoy,
                                p.get("ALL_ball_possession_home", 50), p.get("ALL_ball_possession_away", 50),
                                p.get("ALL_expected_goals_home", 0.0), p.get("ALL_expected_goals_away", 0.0),
                                p.get("ALL_big_chances_home", 0), p.get("ALL_big_chances_away", 0),
                                p.get("ALL_total_shots_home", 0), p.get("ALL_total_shots_away", 0),
                                p.get("ALL_goalkeeper_saves_home", 0), p.get("ALL_goalkeeper_saves_away", 0),
                                p.get("ALL_corner_kicks_home", 0), p.get("ALL_corner_kicks_away", 0),
                                p.get("ALL_fouls_home", 0), p.get("ALL_fouls_away", 0),
                                p.get("ALL_passes_home", 0), p.get("ALL_passes_away", 0),
                                p.get("ALL_yellow_cards_home", 0), p.get("ALL_yellow_cards_away", 0),
                                p.get("ALL_shots_on_target_home", 0), p.get("ALL_shots_on_target_away", 0),
                                p.get("ALL_offsides_home", 0), p.get("ALL_offsides_away", 0),
                                p.get("ALL_accurate_passes_home", 0), p.get("ALL_accurate_passes_away", 0),
                                p.get("ALL_red_cards_home", 0), p.get("ALL_red_cards_away", 0)
                            ]
                            writer.writerow(row)
                            
                    print(f"   + Guardados {partidos_nuevos_guardados} partidos nuevos.")
                else:
                    print("   o No hubo partidos oficiales en esta fecha.")
                
                completado = True # Petición exitosa, sale del bucle de reintentos
                
            except APIError as api_err:
                intentos += 1
                mensaje_error = str(api_err)
                
                # Detectar si el error es de cuota/límite de velocidad (429)
                if "429" in mensaje_error or "RESOURCE_EXHAUSTED" in mensaje_error:
                    # Intentar extraer los segundos de espera que pide Google usando regex
                    segundos_espera = 20 # Tiempo por defecto
                    match = re.search(r"retry in (\d+\.\d+)s", mensaje_error)
                    if match:
                        segundos_espera = int(float(match.group(1))) + 2 # Sumar 2 segundos de margen de seguridad
                        
                    print(f"   ⚠️ Límite de cuota alcanzado (429). Esperando {segundos_espera} segundos para continuar...")
                    time.sleep(segundos_espera)
                else:
                    print(f"   x Error crítico de API en {liga_nombre}: {api_err}")
                    completado = True # Romper para no encallarse en errores desconocidos
                    
            except Exception as e:
                print(f"   x Error inesperado procesando {liga_nombre}: {e}")
                completado = True
                
        # Una pequeña pausa fija básica entre ligas para optimizar la cuota general
        time.sleep(3)
            
    fecha_actual += delta

print(f"\n¡Proceso de rango largo finalizado con éxito!")
