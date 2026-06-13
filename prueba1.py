import os
import json
import csv
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# 1. Configuración de Fechas (Ayer)
fecha_ayer = '2026-05-01'
fecha_hoy = datetime.now().strftime('%Y-%m-%d')

# 2. Inicializar Cliente Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")
client = genai.Client(api_key=api_key)

# 3. Extraer Nombres y Países de tu diccionario original (Ignorando los IDs numéricos)
TORNEOS_IDS = {
    17: {"nombre": "Premier League", "pais": "England"},
    18: {"nombre": "Championship", "pais": "England"},
    11539: {"nombre": "Primera A, Apertura", "pais": "Colombia"},
    11536: {"nombre": "Primera A, Finalización", "pais": "Colombia"},
    1238: {"nombre": "Categoría Primera B", "pais": "Colombia"},
    8: {"nombre": "LaLiga", "pais": "Spain"},
    23: {"nombre": "Serie A", "pais": "Italy"},
    35: {"nombre": "Bundesliga", "pais": "Germany"},
    34: {"nombre": "Ligue 1", "pais": "France"},
    242: {"nombre": "MLS", "pais": "USA"}
    # Puedes descomprimir o agregar aquí el resto de ligas de tu lista original
}

# 4. Definición exacta de tus columnas para el CSV
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

csv_filename = "partidos_estadisticas.csv"

# Inicializar el archivo CSV escribiendo la cabecera
with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(ENCABEZADOS_CSV)

print(f"Iniciando raspado con Gemini para la fecha: {fecha_ayer}...")

# 5. Bucle para procesar liga por liga de forma controlada
for tor_id, info in TORNEOS_IDS.items():
    liga_nombre = info["nombre"]
    pais_nombre = info["pais"]
    
    print(f"-> Buscando partidos de: {liga_nombre} ({pais_nombre})")
    
    prompt = f"""
    Realiza una búsqueda web exhaustiva de los partidos de fútbol de la liga '{liga_nombre}' del país '{pais_nombre}' 
    que finalizaron el día {fecha_ayer} (Temporada actual 2026).
    
    Necesito que extraigas el resultado y las estadísticas completas de cada partido.
    Devuelve la información estrictamente en formato JSON plano sin bloques de código markdown (```json).
    Usa exactamente esta estructura:
    
    {{
      "partidos": [
        {{
          "round": "Nombre de la ronda o jornada",
          "round_number": "Número de jornada (solo número)",
          "home_team_name": "Nombre equipo local",
          "away_team_name": "Nombre equipo visitante",
          "home_goals": 0,
          "away_goals": 0,
          "home_ht_goals": "Goles al descanso (int o null)",
          "away_ht_goals": "Goles al descanso (int o null)",
          "home_et_goals": "Goles prórroga (int o 0)",
          "away_et_goals": "Goles prórroga (int o 0)",
          "home_pen_goals": "Goles penaltis (int o 0)",
          "away_pen_goals": "Goles penaltis (int o 0)",
          "result": "H (si ganó local), A (si ganó visitante), D (si fue empate)",
          "ALL_ball_possession_home": 50.0,
          "ALL_ball_possession_away": 50.0,
          "ALL_expected_goals_home": 0.0,
          "ALL_expected_goals_away": 0.0,
          "ALL_big_chances_home": 0,
          "ALL_big_chances_away": 0,
          "ALL_total_shots_home": 0,
          "ALL_total_shots_away": 0,
          "ALL_goalkeeper_saves_home": 0,
          "ALL_goalkeeper_saves_away": 0,
          "ALL_corner_kicks_home": 0,
          "ALL_corner_kicks_away": 0,
          "ALL_fouls_home": 0,
          "ALL_fouls_away": 0,
          "ALL_passes_home": 0,
          "ALL_passes_away": 0,
          "ALL_yellow_cards_home": 0,
          "ALL_yellow_cards_away": 0,
          "ALL_shots_on_target_home": 0,
          "ALL_shots_on_target_away": 0,
          "ALL_offsides_home": 0,
          "ALL_offsides_away": 0,
          "ALL_accurate_passes_home": 0,
          "ALL_accurate_passes_away": 0,
          "ALL_red_cards_home": 0,
          "ALL_red_cards_away": 0
        }}
      ]
    }}
    
    Nota: Si estadísticas avanzadas como xG o Big Chances no se encuentran para algún partido, calcula una aproximación numérica coherente con el resultado y tiros a puerta (no uses null en estadísticas estadísticas). Las posesiones deben ser float sin signo '%'. Si no hubo partidos, devuelve el arreglo "partidos" vacío.
    """
    
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
            # 6. Guardar los partidos encontrados en el CSV de manera inmediata
            with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                
                for p in partidos:
                    # Rellenamos columnas con strings vacíos o valores por defecto para IDs que ya no se manejan
                    row = [
                        "",                                      # event_id (vacío)
                        pais_nombre,                             # pais
                        liga_nombre,                             # liga
                        "",                                      # tourney_id (vacío)
                        liga_nombre,                             # tourney_name
                        "2026",                                  # tourney_season
                        fecha_ayer,                              # tourney_date
                        p.get("round", ""),                      # round
                        p.get("round_number", ""),               # round_number
                        "",                                      # home_team_id (vacío)
                        p.get("home_team_name", ""),             # home_team_name
                        "",                                      # away_team_id (vacío)
                        p.get("away_team_name", ""),             # away_team_name
                        p.get("home_goals", 0),                  # home_goals
                        p.get("away_goals", 0),                  # away_goals
                        p.get("home_ht_goals", ""),              # home_ht_goals
                        p.get("away_ht_goals", ""),              # away_ht_goals
                        p.get("home_et_goals", 0),               # home_et_goals
                        p.get("away_et_goals", 0),               # away_et_goals
                        p.get("home_pen_goals", 0),              # home_pen_goals
                        p.get("away_pen_goals", 0),              # away_pen_goals
                        p.get("result", ""),                     # result
                        fecha_hoy,                               # scrape_date
                        p.get("ALL_ball_possession_home", 50),   # ALL_ball_possession_home
                        p.get("ALL_ball_possession_away", 50),   # ALL_ball_possession_away
                        p.get("ALL_expected_goals_home", 0.0),   # ALL_expected_goals_home
                        p.get("ALL_expected_goals_away", 0.0),   # ALL_expected_goals_away
                        p.get("ALL_big_chances_home", 0),        # ALL_big_chances_home
                        p.get("ALL_big_chances_away", 0),        # ALL_big_chances_away
                        p.get("ALL_total_shots_home", 0),        # ALL_total_shots_home
                        p.get("ALL_total_shots_away", 0),        # ALL_total_shots_away
                        p.get("ALL_goalkeeper_saves_home", 0),   # ALL_goalkeeper_saves_home
                        p.get("ALL_goalkeeper_saves_away", 0),   # ALL_goalkeeper_saves_away
                        p.get("ALL_corner_kicks_home", 0),       # ALL_corner_kicks_home
                        p.get("ALL_corner_kicks_away", 0),       # ALL_corner_kicks_away
                        p.get("ALL_fouls_home", 0),              # ALL_fouls_home
                        p.get("ALL_fouls_away", 0),              # ALL_fouls_away
                        p.get("ALL_passes_home", 0),             # ALL_passes_home
                        p.get("ALL_passes_away", 0),             # ALL_passes_away
                        p.get("ALL_yellow_cards_home", 0),       # ALL_yellow_cards_home
                        p.get("ALL_yellow_cards_away", 0),       # ALL_yellow_cards_away
                        p.get("ALL_shots_on_target_home", 0),    # ALL_shots_on_target_home
                        p.get("ALL_shots_on_target_away", 0),    # ALL_shots_on_target_away
                        p.get("ALL_offsides_home", 0),           # ALL_offsides_home
                        p.get("ALL_offsides_away", 0),           # ALL_offsides_away
                        p.get("ALL_accurate_passes_home", 0),    # ALL_accurate_passes_home
                        p.get("ALL_accurate_passes_away", 0),    # ALL_accurate_passes_away
                        p.get("ALL_red_cards_home", 0),          # ALL_red_cards_home
                        p.get("ALL_red_cards_away", 0)           # ALL_red_cards_away
                    ]
                    writer.writerow(row)
            print(f"   + Guardados {len(partidos)} partidos correctamente.")
        else:
            print("   o No se encontraron partidos disputados ayer.")
            
    except Exception as e:
        print(f"   x Error procesando la liga {liga_nombre}: {e}")

print(f"\n¡Proceso finalizado! Todos los datos recolectados se encuentran en '{csv_filename}'")
