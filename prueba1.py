import os
import json
import csv
import time
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# =====================================================================
# CONFIGURACIÓN MANUAL DE RANGO DE FECHAS (VERSIÓN AUTO-FLUSH)
# =====================================================================
FECHA_INICIO = '2026-01-01'  
FECHA_FIN    = '2026-04-19'  
csv_filename = "partidos_estadisticas_historico.csv"
# =====================================================================

# 1. VALIDACIÓN ANTIDUPLICADOS
partidos_existentes = set()

if os.path.exists(csv_filename):
    print(f"Leyendo '{csv_filename}' existente para evitar duplicados...", flush=True)
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
                print("Aviso: El CSV existente no tiene el formato esperado.", flush=True)

print(f"-> Se encontraron {len(partidos_existentes)} partidos registrados previamente.\n", flush=True)

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
    
    print(f"\n==================================================", flush=True)
    print(f" PROCESANDO FECHA: {str_fecha_ayer}", flush=True)
    print(f"==================================================", flush=True)
    
    for tor_id, info in TORNEOS_IDS.items():
        liga_nombre = info["nombre"]
        pais_nombre = info["pais"]
        
        if pais_nombre == "Colombia" and mes_actual == 1 and fecha_actual.day < 15:
            print(f"-> Saltando {liga_nombre} (Sin actividad oficial a principios de enero)", flush=True)
            continue
            
        print(f"-> Buscando partidos de: {liga_nombre} ({pais_nombre})...", flush=True)
        
        prompt = f"""
        Busca en la web los partidos oficiales de fútbol de la liga '{liga_nombre}' ({pais_nombre}) que finalizaron el día {str_fecha_ayer}.
        Devuelve la información estrictamente en formato JSON plano sin bloques markdown. Si no hubo partidos, devuelve "partidos": [].
        
        Estructura:
        {{
          "partidos": [
            {{
              "round": "Jornada X", "round_number": "X",
              "home_team_name": "Nombre local", "away_team_name": "Nombre visitante",
              "home_goals": 0, "away_goals": 0, "home_ht_goals": 0, "away_ht_goals": 0,
              "home_et_goals": 0, "away_et_goals": 0, "home_pen_goals": 0, "away_pen_goals": 0,
              "result": "H, A o D", "ALL_ball_possession_home": 50.0, "ALL_ball_possession_away": 50.0,
              "ALL_expected_goals_home": 1.0, "ALL_expected_goals_away": 1.0,
              "ALL_big_chances_home": 0, "ALL_big_chances_away": 0,
              "ALL_total_shots_home": 0, "ALL_total_shots_away": 0,
              "ALL_goalkeeper_saves_home": 0, "ALL_goalkeeper_saves_away": 0,
              "ALL_corner_kicks_home": 0, "ALL_corner_kicks_away": 0,
              "ALL_fouls_home": 0, "ALL_fouls_away": 0, "ALL_passes_home": 0, "ALL_passes_away": 0,
              "ALL_yellow_cards_home": 0, "ALL_yellow_cards_away": 0,
              "ALL_shots_on_target_home": 0, "ALL_shots_on_target_away": 0,
              "ALL_offsides_home": 0, "ALL_offsides_away": 0,
              "ALL_accurate_passes_home": 0, "ALL_accurate_passes_away": 0,
              "ALL_red_cards_home": 0, "ALL_red_cards_away": 0
            }}
          ]
        }}
        """
        
        try:
            config_llamada = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1
            )
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config_llamada
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
                            print(f"   [IGNORADO] {local} vs {visita} ya existe.", flush=True)
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
                        
                print(f"   + Guardados {partidos_nuevos_guardados} partidos nuevos.", flush=True)
            else:
                print("   o No hubo partidos oficiales en esta fecha.", flush=True)
                
        except Exception as e:
            mensaje = str(e)
            if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
                print("   ⚠️ Alerta de Cuota (429). Esperando 30 segundos obligatorios...", flush=True)
                time.sleep(30)
            else:
                print(f"   x Error/Timeout en {liga_nombre}: Pasando a la siguiente consulta.", flush=True)
                
        time.sleep(4)
            
    fecha_actual += delta

print(f"\n¡Proceso finalizado limpia y rápidamente!", flush=True)
