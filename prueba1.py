import os
import json
import csv
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# =====================================================================
# CONFIGURACIÓN MANUAL DE RANGO DE FECHAS
# =====================================================================
FECHA_INICIO = '2026-01-01'  
FECHA_FIN    = '2026-05-03'  
csv_filename = "partidos_estadisticas_historico.csv"
# =====================================================================

# 1. VALIDACIÓN ANTIDUPLICADOS: Cargar partidos que ya existen en el CSV
partidos_existentes = set()

if os.path.exists(csv_filename):
    print(f"Leyendo '{csv_filename}' existente para evitar duplicados...")
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None) # Saltar cabecera
        if header:
            # Identificar los índices de las columnas que necesitamos
            try:
                idx_fecha = header.index("tourney_date")
                idx_local = header.index("home_team_name")
                idx_visita = header.index("away_team_name")
                
                for row in reader:
                    if len(row) > max(idx_fecha, idx_local, idx_visita):
                        # Creamos la llave única: 'fecha_local_visita'
                        llave = f"{row[idx_fecha]}_{row[idx_local]}_{row[idx_visita]}".strip().lower()
                        partidos_existentes.add(llave)
            except ValueError:
                print("Aviso: El CSV existente no tiene el formato esperado. Se creará uno nuevo.")

print(f"-> Se encontraron {len(partidos_existentes)} partidos registrados previamente.")

# Inicializar o mantener el archivo CSV
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

# Inicializar Cliente Gemini
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

TORNEOS_IDS = {
    17: {"nombre": "Premier League", "pais": "England"},
    11539: {"nombre": "Primera A, Apertura", "pais": "Colombia"}
}

fecha_hoy = datetime.now().strftime('%Y-%m-%d')
start_date = datetime.strptime(FECHA_INICIO, '%Y-%m-%d')
end_date = datetime.strptime(FECHA_FIN, '%Y-%m-%d')
delta = timedelta(days=1)

fecha_actual = start_date
while fecha_actual <= end_date:
    str_fecha_ayer = fecha_actual.strftime('%Y-%m-%d')
    print(f"\n==================================================")
    print(f" PROCESANDO FECHA: {str_fecha_ayer}")
    print(f"==================================================")
    
    for tor_id, info in TORNEOS_IDS.items():
        liga_nombre = info["nombre"]
        pais_nombre = info["pais"]
        
        print(f"-> Buscando partidos de: {liga_nombre} ({pais_nombre})")
        
        # ... [AQUÍ SE MANTIENE EL MISMO PROMPT DE LA RESPUESTA ANTERIOR] ...
        prompt = "..." 
        
        try:
            # Petición a la API (Simulada conceptualmente para el flujo)
            # response = client.models.generate_content(...)
            # data = json.loads(texto_limpio)
            
            # Simulación de lectura de la respuesta estructurada de Gemini
            partidos = data.get("partidos", [])
            
            if partidos:
                partidos_nuevos_guardados = 0
                
                with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    
                    for p in partidos:
                        local = p.get("home_team_name", "").strip()
                        visita = p.get("away_team_name", "").strip()
                        
                        # Generar la llave de validación para este partido específico
                        llave_partido = f"{str_fecha_ayer}_{local}_{visita}".strip().lower()
                        
                        # 2. CONTROL CLAVE: Si ya existe, saltar al siguiente
                        if llave_partido in partidos_existentes:
                            print(f"   [IGNORADO] El partido {local} vs {visita} ya se encuentra registrado.")
                            continue
                        
                        # Si es nuevo, lo procesamos y añadimos al set para evitar que se duplique en este mismo ciclo
                        partidos_existentes.add(llave_partido)
                        partidos_nuevos_guardados += 1
                        
                        row = [
                            "", pais_nombre, liga_nombre, "", liga_nombre, 
                            str_fecha_ayer[:4], str_fecha_ayer,
                            p.get("round", ""), p.get("round_number", ""),
                            "", local, "", visita,
                            p.get("home_goals", 0), p.get("away_goals", 0),
                            p.get("home_ht_goals", ""), p.get("away_ht_goals", ""),
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
                        
                print(f"   + Guardados {partidos_nuevos_guardados} partidos nuevos en esta liga.")
            else:
                print("   o No se encontraron partidos disputados.")
                
        except Exception as e:
            print(f"   x Error procesando {liga_nombre}: {e}")
            
    fecha_actual += delta

print(f"\n¡Proceso de actualización finalizado!")
