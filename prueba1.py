import os
import json
import csv
import time
import sys
import hashlib
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# =====================================================================
# CONFIGURACIÓN DE RUTA DINÁMICA (CARPETA DATOS)
# =====================================================================
csv_filename = os.path.join("datos", "futbol_historico.csv")
os.makedirs("datos", exist_ok=True)
# =====================================================================

# Diccionario original completo con sus IDs oficiales para recuperar los IDs de torneo
TORNEOS_IDS = {
    17: {"nombre": "Premier League", "pais": "England"},
    18: {"nombre": "Championship", "pais": "England"},
    24: {"nombre": "League One", "pais": "England"},
    25: {"nombre": "League Two", "pais": "England"},
    19: {"nombre": "FA Cup", "pais": "England"},
    841: {"nombre": "Algerian Ligue 1", "pais": "Algeria"},
    155: {"nombre": "Liga Profesional de Fútbol", "pais": "Argentina"},
    703: {"nombre": "Primera Nacional", "pais": "Argentina"},
    1347: {"nombre": "Primera B Metropolitana", "pais": "Argentina"},
    136: {"nombre": "A-League Men", "pais": "Australia"},
    1894: {"nombre": "A-League Women", "pais": "Australia"},
    1260: {"nombre": "NPL Capital Football", "pais": "Australia"},
    1268: {"nombre": "NPL Queensland", "pais": "Australia"},
    709: {"nombre": "Misli Premier League", "pais": "Azerbaijan"},
    846: {"nombre": "Bahraini Premier League", "pais": "Bahrain"},
    13331: {"nombre": "Bangladesh Football League", "pais": "Bangladesh"},
    16736: {"nombre": "División Profesional", "pais": "Bolivia"},
    325: {"nombre": "Brasileirão Betano", "pais": "Brazil"},
    390: {"nombre": "Brasileirão Série B", "pais": "Brazil"},
    1281: {"nombre": "Brasileirão Série C", "pais": "Brazil"},
    22106: {"nombre": "Première Division de N'Djaména", "pais": "Chad"},
    11653: {"nombre": "Liga de Primera", "pais": "Chile"},
    649: {"nombre": "Chinese Super League", "pais": "China"},
    782: {"nombre": "Chinese League 1", "pais": "China"},
    11539: {"nombre": "Primera A, Apertura", "pais": "Colombia"},
    11536: {"nombre": "Primera A, Finalización", "pais": "Colombia"},
    1238: {"nombre": "Categoría Primera B", "pais": "Colombia"},
    240: {"nombre": "LigaPro Serie A", "pais": "Ecuador"},
    808: {"nombre": "Egyptian Premier League", "pais": "Egypt"},
    309: {"nombre": "World Cup Qual. OFC", "pais": "Oceania"},
    1222: {"nombre": "OFC Champions League", "pais": "Oceania"},
    704: {"nombre": "Erovnuli Liga", "pais": "Georgia"},
    1054: {"nombre": "CAF Champions League", "pais": "Africa"},
    463: {"nombre": "AFC Champions League Elite", "pais": "Asia"},
    7: {"nombre": "UEFA Champions League", "pais": "Europe"},
    679: {"nombre": "UEFA Europa League", "pais": "Europe"},
    17015: {"nombre": "UEFA Conference League", "pais": "Europe"},
    696: {"nombre": "UEFA Women's Champions League", "pais": "Europe"},
    140: {"nombre": "CONCACAF Gold Cup", "pais": "North & Central America"},
    11454: {"nombre": "Campeones Cup", "pais": "North & Central America"},
    498: {"nombre": "CONCACAF Champions Cup", "pais": "North & Central America"},
    13783: {"nombre": "Leagues Cup", "pais": "North & Central America"},
    384: {"nombre": "CONMEBOL Libertadores", "pais": "South America"},
    480: {"nombre": "CONMEBOL Sudamericana", "pais": "South America"},
    133: {"nombre": "Copa América", "pais": "South America"},
    10602: {"nombre": "Copa Libertadores Femenina", "pais": "South America"},
    1015: {"nombre": "Indonesia Super League", "pais": "Indonesia"},
    20708: {"nombre": "UEFA-CONMEBOL Club Challenge", "pais": "World"},
    16: {"nombre": "FIFA World Cup", "pais": "World"},
    23674: {"nombre": "FIFA Intercontinental Cup", "pais": "World"},
    851: {"nombre": "International Friendly Games", "pais": "World"},
    290: {"nombre": "FIFA Women's World Cup", "pais": "World"},
    915: {"nombre": "Persian Gulf Pro League", "pais": "Iran"},
    206: {"nombre": "Israeli Premier League", "pais": "Israel"},
    196: {"nombre": "J1 League", "pais": "Japan"},
    402: {"nombre": "J2 League", "pais": "Japan"},
    682: {"nombre": "Kazakhstan Premier League", "pais": "Kazakhstan"},
    1002: {"nombre": "Zain Premier League", "pais": "Kuwait"},
    594: {"nombre": "New Zealand National League", "pais": "New Zealand"},
    200: {"nombre": "NIFL Premiership", "pais": "Northern Ireland"},
    11540: {"nombre": "Primera División, Apertura", "pais": "Paraguay"},
    11541: {"nombre": "Primera División, Clausura", "pais": "Paraguay"},
    406: {"nombre": "Liga 1", "pais": "Peru"},
    825: {"nombre": "Stars League", "pais": "Qatar"},
    955: {"nombre": "Saudi Pro League", "pais": "Saudi Arabia"},
    36: {"nombre": "Scottish Premiership", "pais": "Scotland"},
    358: {"nombre": "South African Premier Division", "pais": "South Africa"},
    52: {"nombre": "Trendyol Süper Lig", "pais": "Turkey"},
    971: {"nombre": "UAE Pro League", "pais": "United Arab Emirates"},
    278: {"nombre": "Liga AUF Uruguaya", "pais": "Uruguay"},
    13470: {"nombre": "Canadian Premier League", "pais": "Canada"},
    11621: {"nombre": "Liga MX, Apertura", "pais": "Mexico"},
    11620: {"nombre": "Liga MX, Clausura", "pais": "Mexico"},
    11611: {"nombre": "Liga de Expansión MX, Apertura", "pais": "Mexico"},
    11612: {"nombre": "Liga de Expansión MX, Clausura", "pais": "Mexico"},
    242: {"nombre": "MLS", "pais": "USA"},
    13363: {"nombre": "USL Championship", "pais": "USA"},
    18641: {"nombre": "MLS Next Pro", "pais": "USA"},
    1690: {"nombre": "NWSL", "pais": "USA"},
    197: {"nombre": "Virsliga", "pais": "Latvia"},
    198: {"nombre": "TOPLYGA", "pais": "Lithuania"},
    211: {"nombre": "Niké Liga", "pais": "Slovakia"},
    8: {"nombre": "LaLiga", "pais": "Spain"},
    54: {"nombre": "LaLiga 2", "pais": "Spain"},
    20: {"nombre": "Eliteserien", "pais": "Norway"},
    22: {"nombre": "Norwegian 1st Division", "pais": "Norway"},
    202: {"nombre": "Ekstraklasa", "pais": "Poland"},
    238: {"nombre": "Liga Portugal Betclic", "pais": "Portugal"},
    152: {"nombre": "SuperLiga României", "pais": "Romania"},
    40: {"nombre": "Allsvenskan", "pais": "Sweden"},
    46: {"nombre": "Superettan", "pais": "Sweden"},
    67: {"nombre": "Ettan, Norra", "pais": "Sweden"},
    68: {"nombre": "Ettan, Södra", "pais": "Sweden"},
    214: {"nombre": "Damallsvenskan", "pais": "Sweden"},
    218: {"nombre": "Ukrainian Premier League", "pais": "Ukraine"},
    37: {"nombre": "VriendenLoterij Eredivisie", "pais": "Netherlands"},
    131: {"nombre": "Eerste Divisiee", "pais": "Netherlands"},
    215: {"nombre": "Swiss Super League", "pais": "Switzerland"},
    185: {"nombre": "Stoiximan Super League", "pais": "Greece"},
    38: {"nombre": "Pro League", "pais": "Belgium"},
    9: {"nombre": "Challenger Pro League", "pais": "Belgium"},
    178: {"nombre": "Premium Liiga", "pais": "Estonia"},
    678: {"nombre": "Esiliiga", "pais": "Estonia"},
    41: {"nombre": "Veikkausliiga", "pais": "Finland"},
    55: {"nombre": "Ykkösliiga", "pais": "Finland"},
    34: {"nombre": "Ligue 1", "pais": "France"},
    182: {"nombre": "Ligue 2", "pais": "France"},
    35: {"nombre": "Bundesliga", "pais": "Germany"},
    44: {"nombre": "2. Bundesliga", "pais": "Germany"},
    192: {"nombre": "Premier Division", "pais": "Ireland"},
    23: {"nombre": "Serie A", "pais": "Italy"},
    53: {"nombre": "Serie B", "pais": "Italy"},
    45: {"nombre": "Austrian Bundesliga", "pais": "Austria"},
    247: {"nombre": "Parva Liga", "pais": "Bulgaria"},
    1135: {"nombre": "Vtora Liga", "pais": "Bulgaria"},
    205: {"nombre": "FNL", "pais": "Czech Republic"},
    39: {"nombre": "Danish Superliga", "pais": "Denmark"},
    170: {"nombre": "HNL", "pais": "Croatia"}
}

NOMBRES_LIGAS = [info["nombre"] for info in TORNEOS_IDS.values()]

partidos_existentes = set()
partidos_incompletos_por_fecha = {}  # { 'YYYY-MM-DD': [ (liga, local, visita, fila_index), ... ] }
ultima_fecha_registrada = None
filas_completas_csv = []
headers = []

# Función para generar un event_id consistente e idéntico a partir del partido
def generar_event_id(fecha, local, visita):
    clave = f"{fecha}_{local}_{visita}".encode('utf-8')
    # Genera un hash numérico consistente de 8 dígitos para emular los IDs de Sofascore
    return int(hashlib.md5(clave).hexdigest()[:8], 16) % 100000000

# Función para formatear la posesión de balón igual que el resto del histórico (ej. "48%")
def formatear_posesion(valor, default=50):
    try:
        return f"{int(round(float(valor)))}%"
    except (ValueError, TypeError):
        return f"{default}%"

# 1. AUDITORÍA INTERNA DEL CSV EXISTENTE
if os.path.exists(csv_filename):
    print(f"Iniciando auditoría interna de '{csv_filename}'...", flush=True)
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        filas_completas_csv = [headers] if headers else []
        
        if headers:
            try:
                idx_fecha = headers.index("tourney_date")
                idx_liga = headers.index("liga")
                idx_local = headers.index("home_team_name")
                idx_visita = headers.index("away_team_name")
                idx_shots = headers.index("ALL_total_shots_home")
                idx_poss = headers.index("ALL_ball_possession_home")
                
                for row_idx, row in enumerate(reader, start=1):
                    if len(row) > max(idx_fecha, idx_liga, idx_local, idx_visita, idx_shots, idx_poss):
                        liga = row[idx_liga].strip()
                        fecha_str = row[idx_fecha].strip()
                        local = row[idx_local].strip()
                        visita = row[idx_visita].strip()
                        
                        llave = f"{fecha_str}_{local}_{visita}".strip().lower()
                        partidos_existentes.add(llave)
                        filas_completas_csv.append(row)
                        
                        # Guardar la fecha más reciente para la continuación
                        try:
                            f_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                            if ultima_fecha_registrada is None or f_obj > ultima_fecha_registrada:
                                ultima_fecha_registrada = f_obj
                        except ValueError:
                            pass
                        
                        # Verificar si es una de nuestras ligas y si le faltan datos reales
                        if liga in NOMBRES_LIGAS:
                            try:
                                tiros = int(row[idx_shots])
                                posesion_raw = str(row[idx_poss]).replace("%", "").strip()
                                posesion = float(posesion_raw) if posesion_raw else 0.0
                                if tiros == 0 or (posesion == 50.0 and tiros == 0) or posesion == 0:
                                    if fecha_str not in partidos_incompletos_por_fecha:
                                        partidos_incompletos_por_fecha[fecha_str] = []
                                    partidos_incompletos_por_fecha[fecha_str].append((liga, local, visita, len(filas_completas_csv) - 1))
                            except ValueError:
                                pass
            except ValueError:
                print("Error: El formato de los encabezados del CSV no es válido.", flush=True)

# Acotar la reparación SOLO a la última fecha registrada en el CSV
if ultima_fecha_registrada and partidos_incompletos_por_fecha:
    ultima_fecha_str = ultima_fecha_registrada.strftime('%Y-%m-%d')
    partidos_incompletos_por_fecha = {
        k: v for k, v in partidos_incompletos_por_fecha.items()
        if k == ultima_fecha_str
    }

# 2. PROCESO DE CONTROL DE LLAMADAS A LA API DE GEMINI
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")
client = genai.Client(api_key=api_key)
fecha_hoy_str = datetime.now().strftime('%Y-%m-%d')

# =====================================================================
# MODELO A USAR
# (gemini-2.5-flash-lite tiene un cupo diario propio, separado del de
#  gemini-2.5-flash, así que si uno se agota puedes alternar aquí)
# =====================================================================
MODEL_NAME = "gemini-2.5-flash-lite"

# =====================================================================
# CONTROL DE LLAMADAS POR CORRIDA
# (para repartir la cuota diaria de Gemini entre varias ejecuciones del cron
#  y no agotarla toda de un solo golpe)
# =====================================================================
MAX_LLAMADAS_POR_CORRIDA = 10  # Ajusta este número según la frecuencia de tu cron
llamadas_realizadas = 0

def limite_alcanzado():
    """Devuelve True si ya se llegó al tope de llamadas para esta corrida."""
    if llamadas_realizadas >= MAX_LLAMADAS_POR_CORRIDA:
        print(f"\n   ⏸️  Límite de {MAX_LLAMADAS_POR_CORRIDA} llamadas por corrida alcanzado. "
              f"Pausando aquí para repartir la cuota diaria entre varias ejecuciones del cron.", flush=True)
        return True
    return False

# =====================================================================
# HELPER: Llamada robusta a Gemini con búsqueda web y parseo JSON
# =====================================================================
def llamar_gemini_json(prompt):
    """
    Llama a Gemini con la herramienta de búsqueda de Google, desactiva el
    'thinking' (para que no consuma todo el max_output_tokens sin dejar
    texto de respuesta) y devuelve el JSON ya parseado.
    Lanza una excepción con un mensaje descriptivo si algo falla.
    """
    global llamadas_realizadas
    llamadas_realizadas += 1

    config_llamada = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.1,
        max_output_tokens=8192,
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
    response = client.models.generate_content(
        model=MODEL_NAME, contents=prompt, config=config_llamada
    )

    texto_limpio = (response.text or "").strip()

    if not texto_limpio:
        # Diagnóstico: por qué vino vacía la respuesta
        finish_reason = "desconocido"
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            pass
        raise ValueError(f"Respuesta vacía de Gemini (finish_reason={finish_reason})")

    if texto_limpio.startswith("```json"):
        texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
    elif texto_limpio.startswith("```"):
        texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()

    if not texto_limpio:
        # El modelo devolvió un bloque ```json``` vacío (típico cuando no hay
        # partidos para reportar). Lo tratamos como "sin datos" en vez de error.
        return {}

    return json.loads(texto_limpio)

# =====================================================================
# FASE A: REESCRITURA Y REPARACIÓN DE PARTIDOS SIN DATOS (SOLO ÚLTIMA FECHA)
# =====================================================================
reparacion_abortada = False
if partidos_incompletos_por_fecha:
    total_huecos = sum(len(v) for v in partidos_incompletos_por_fecha.values())
    print(f"\n[AUDITORÍA] Se encontraron {total_huecos} partidos sin estadísticas o incompletos en la última fecha registrada.", flush=True)
    print("-> Iniciando fase de reparación prioritaria...", flush=True)
    
    for fecha_inc, partidos_lista in list(partidos_incompletos_por_fecha.items()):
        print(f"\n REPARANDO FECHA: {fecha_inc}", flush=True)
        ligas_en_fecha = set(p[0] for p in partidos_lista)
        
        for liga_obj in ligas_en_fecha:
            if limite_alcanzado():
                reparacion_abortada = True
                break

            partidos_especificos = [p for p in partidos_lista if p[0] == liga_obj]
            nombres_cruzar = ", ".join([f"{p[1]} vs {p[2]}" for p in partidos_especificos])
            
            print(f"   -> Buscando estadísticas reales para {liga_obj} ({nombres_cruzar})...", flush=True)
            
            prompt_reparar = f"""
            Busca en la web las estadísticas completas del día {fecha_inc} para la liga '{liga_obj}' para los siguientes encuentros: {nombres_cruzar}.
            
            Devuelve los datos estrictamente en este formato JSON plano sin bloques markdown:
            {{
              "partidos": [
                {{
                  "home_team_name": "Nombre local exacto",
                  "away_team_name": "Nombre visitante exacto",
                  "ALL_ball_possession_home": 50.0, "ALL_ball_possession_away": 50.0,
                  "ALL_expected_goals_home": 1.0, "ALL_expected_goals_away": 1.0,
                  "ALL_big_chances_home": 0, "ALL_big_chances_away": 0,
                  "ALL_total_shots_home": 0, "ALL_total_shots_away": 0,
                  "ALL_goalkeeper_saves_home": 0, "ALL_goalkeeper_saves_away": 0,
                  "ALL_corner_kicks_home": 0, "ALL_corner_kicks_away": 0,
                  "ALL_fouls_home": 0, "ALL_fouls_away": 0,
                  "ALL_passes_home": 0, "ALL_passes_away": 0,
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
                data = llamar_gemini_json(prompt_reparar)
                partidos_nuevos = data.get("partidos", [])
                
                for pn in partidos_nuevos:
                    loc_n = str(pn.get("home_team_name", "")).strip().lower()
                    
                    for p_inc in partidos_especificos:
                        if p_inc[1].lower() in loc_n or loc_n in p_inc[1].lower():
                            pos_fila = p_inc[3]
                            row_mod = filas_completas_csv[pos_fila]
                            
                            row_mod[headers.index("ALL_ball_possession_home")] = formatear_posesion(pn.get("ALL_ball_possession_home", 50))
                            row_mod[headers.index("ALL_ball_possession_away")] = formatear_posesion(pn.get("ALL_ball_possession_away", 50))
                            row_mod[headers.index("ALL_expected_goals_home")] = pn.get("ALL_expected_goals_home", 0.0)
                            row_mod[headers.index("ALL_expected_goals_away")] = pn.get("ALL_expected_goals_away", 0.0)
                            row_mod[headers.index("ALL_big_chances_home")] = pn.get("ALL_big_chances_home", 0)
                            row_mod[headers.index("ALL_big_chances_away")] = pn.get("ALL_big_chances_away", 0)
                            row_mod[headers.index("ALL_total_shots_home")] = pn.get("ALL_total_shots_home", 0)
                            row_mod[headers.index("ALL_total_shots_away")] = pn.get("ALL_total_shots_away", 0)
                            row_mod[headers.index("ALL_goalkeeper_saves_home")] = pn.get("ALL_goalkeeper_saves_home", 0)
                            row_mod[headers.index("ALL_goalkeeper_saves_away")] = pn.get("ALL_goalkeeper_saves_away", 0)
                            row_mod[headers.index("ALL_corner_kicks_home")] = pn.get("ALL_corner_kicks_home", 0)
                            row_mod[headers.index("ALL_corner_kicks_away")] = pn.get("ALL_corner_kicks_away", 0)
                            row_mod[headers.index("ALL_fouls_home")] = pn.get("ALL_fouls_home", 0)
                            row_mod[headers.index("ALL_fouls_away")] = pn.get("ALL_fouls_away", 0)
                            row_mod[headers.index("ALL_passes_home")] = pn.get("ALL_passes_home", 0)
                            row_mod[headers.index("ALL_passes_away")] = pn.get("ALL_passes_away", 0)
                            row_mod[headers.index("ALL_yellow_cards_home")] = pn.get("ALL_yellow_cards_home", 0)
                            row_mod[headers.index("ALL_yellow_cards_away")] = pn.get("ALL_yellow_cards_away", 0)
                            row_mod[headers.index("ALL_shots_on_target_home")] = pn.get("ALL_shots_on_target_home", 0)
                            row_mod[headers.index("ALL_shots_on_target_away")] = pn.get("ALL_shots_on_target_away", 0)
                            row_mod[headers.index("ALL_offsides_home")] = pn.get("ALL_offsides_home", 0)
                            row_mod[headers.index("ALL_offsides_away")] = pn.get("ALL_offsides_away", 0)
                            row_mod[headers.index("ALL_accurate_passes_home")] = pn.get("ALL_accurate_passes_home", 0)
                            row_mod[headers.index("ALL_accurate_passes_away")] = pn.get("ALL_accurate_passes_away", 0)
                            row_mod[headers.index("ALL_red_cards_home")] = pn.get("ALL_red_cards_home", 0)
                            row_mod[headers.index("ALL_red_cards_away")] = pn.get("ALL_red_cards_away", 0)
                            
                            filas_completas_csv[pos_fila] = row_mod
                            print(f"      + Éxito: Estadísticas restauradas para {p_inc[1]} vs {p_inc[2]}", flush=True)
                
                with open(csv_filename, "w", newline="", encoding="utf-8") as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(filas_completas_csv)
                    
            except Exception as e:
                mensaje = str(e)
                if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
                    print("\n   ⚠️ Cuota agotada durante fase de reparación. No se pudo actualizar este bloque, abortando reparación y pasando a la descarga de nuevos partidos...", flush=True)
                    print(f"      Detalle: {mensaje}", flush=True)
                    reparacion_abortada = True
                    break
                print(f"   x No se pudo parchar el bloque ({e}). Continuando con el siguiente...", flush=True)
            
            time.sleep(8)
        
        if reparacion_abortada:
            break
else:
    print("[AUDITORÍA] ¡Excelente! No se encontraron partidos con datos vacíos en la última fecha registrada.", flush=True)

# =====================================================================
# FASE B: CONTINUACIÓN DE EXTRACCIÓN AVANZANDO HACIA EL FUTURO
# =====================================================================
fecha_hoy_obj = datetime.now()
if ultima_fecha_registrada:
    start_date = ultima_fecha_registrada + timedelta(days=1)
    print(f"\n-> Fase de continuación: El script avanzará desde el {start_date.strftime('%Y-%m-%d')} hasta hoy.", flush=True)
else:
    start_date = datetime.strptime('2026-01-01', '%Y-%m-%d')

end_date = fecha_hoy_obj
if start_date > end_date:
    print("¡El archivo histórico ya se encuentra 100% al día con la fecha actual!", flush=True)
    print(f"\nLlamadas a Gemini realizadas en esta corrida: {llamadas_realizadas}/{MAX_LLAMADAS_POR_CORRIDA}", flush=True)
    sys.exit(0)

# Inicializar headers si el archivo es nuevo
if not os.path.exists(csv_filename) or len(filas_completas_csv) == 0:
    headers = [
        "event_id", "pais", "liga", "tourney_id", "tourney_name", "tourney_season", "tourney_date",
        "round", "round_number", "home_team_id", "home_team_name", "away_team_id", "away_team_name",
        "home_goals", "away_goals", "home_ht_goals", "away_ht_goals", "home_et_goals", "away_et_goals",
        "home_pen_goals", "away_pen_goals", "result", "scrape_date",
        "ALL_ball_possession_home", "ALL_ball_possession_away", "ALL_expected_goals_home", "ALL_expected_goals_away",
        "ALL_big_chances_home", "ALL_big_chances_away", "ALL_total_shots_home", "ALL_total_shots_away",
        "ALL_goalkeeper_saves_home", "ALL_goalkeeper_saves_away", "ALL_corner_kicks_home", "ALL_corner_kicks_away",
        "ALL_fouls_home", "ALL_fouls_away", "ALL_passes_home", "ALL_passes_away",
        "ALL_yellow_cards_home", "ALL_yellow_cards_away", "ALL_shots_on_target_home", "ALL_shots_on_target_away",
        "ALL_offsides_home", "ALL_offsides_away", "ALL_accurate_passes_home", "ALL_accurate_passes_away",
        "ALL_red_cards_home", "ALL_red_cards_away"
    ]
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(headers)

# SOLO ACTIVAMOS LAS LIGAS PRINCIPALES PARA NO COPAR LA CUOTA DIARIA DE INMEDIATO
LIGAS_ACTUALIZAR = {
    17: {"nombre": "Premier League", "pais": "England"},
    11539: {"nombre": "Primera A, Apertura", "pais": "Colombia"},
    8: {"nombre": "LaLiga", "pais": "Spain"},
    23: {"nombre": "Serie A", "pais": "Italy"}
}

cuota_agotada_b = False
fecha_actual = start_date
while fecha_actual <= end_date:
    fecha_fin_semana = fecha_actual + timedelta(days=6)
    if fecha_fin_semana > end_date: 
        fecha_fin_semana = end_date
        
    str_inicio_sem = fecha_actual.strftime('%Y-%m-%d')
    str_fin_sem    = fecha_fin_semana.strftime('%Y-%m-%d')
    
    print(f"\n==================================================", flush=True)
    print(f" PROCESANDO NUEVA SEMANA: Del {str_inicio_sem} al {str_fin_sem}", flush=True)
    print(f"==================================================", flush=True)
    
    for tor_id, info in LIGAS_ACTUALIZAR.items():
        if limite_alcanzado():
            cuota_agotada_b = True
            break

        liga_nombre = info["nombre"]
        pais_nombre = info["pais"]
        
        if pais_nombre == "Colombia" and fecha_actual.month == 1 and fecha_actual.day < 15:
            continue
            
        print(f"-> Descargando bloque nuevo para: {liga_nombre}...", flush=True)
        
        prompt = f"""
        Busca en la web todos los partidos oficiales de fútbol de la liga '{liga_nombre}' ({pais_nombre}) completados entre el {str_inicio_sem} y el {str_fin_sem}.
        Devuelve JSON plano sin markdown. Campo "tourney_date" obligatorio (YYYY-MM-DD).
        
        Establece en el campo "tourney_season" el nombre oficial de la temporada (ej: "Premier League 25/26" o "LaLiga 25/26" o "Primera A 2026").
        
        JSON Estructura:
        {{
          "partidos": [
            {{
              "tourney_date": "YYYY-MM-DD", 
              "tourney_season": "Nombre exacto de la temporada",
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
            data = llamar_gemini_json(prompt)
            partidos = data.get("partidos", [])
            
            if partidos:
                partidos_nuevos_guardados = 0
                with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    for p in partidos:
                        f_partido = p.get("tourney_date", str_inicio_sem)
                        local = str(p.get("home_team_name", "")).strip()
                        visita = str(p.get("away_team_name", "")).strip()
                        
                        if not local or not visita: 
                            continue
                        llave_partido = f"{f_partido}_{local}_{visita}".strip().lower()
                        
                        if llave_partido in partidos_existentes: 
                            continue
                        
                        partidos_existentes.add(llave_partido)
                        partidos_nuevos_guardados += 1
                        
                        # Generación dinámica del ID del partido consistente con Sofascore
                        id_evento_calculado = generar_event_id(f_partido, local, visita)
                        season_detectada = p.get("tourney_season", f"{liga_nombre} {f_partido[:4]}")
                        
                        row = [
                            id_evento_calculado,               # event_id (Generado de forma única para tu MariaDB)
                            pais_nombre,                       # pais
                            liga_nombre,                       # liga
                            tor_id,                            # tourney_id (¡Ahora con tu ID de Sofascore oficial!)
                            liga_nombre,                       # tourney_name
                            season_detectada,                  # tourney_season (Mapeada en tiempo real)
                            f_partido,                         # tourney_date
                            p.get("round", ""),                # round
                            p.get("round_number", ""),         # round_number
                            "",                                # home_team_id
                            local,                             # home_team_name
                            "",                                # away_team_id
                            visita,                            # away_team_name
                            p.get("home_goals", 0), p.get("away_goals", 0),
                            p.get("home_ht_goals", 0), p.get("away_ht_goals", 0),
                            p.get("home_et_goals", 0), p.get("away_et_goals", 0),
                            p.get("home_pen_goals", 0), p.get("away_pen_goals", 0),
                            p.get("result", ""), fecha_hoy_str,
                            formatear_posesion(p.get("ALL_ball_possession_home", 50)), formatear_posesion(p.get("ALL_ball_possession_away", 50)),
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
                print(f"   + Agregados {partidos_nuevos_guardados} partidos nuevos.", flush=True)
            else:
                print("   o No hay partidos nuevos.", flush=True)
                
        except Exception as e:
            mensaje = str(e)
            if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
                print("\n   ⚠️ [CUOTA LIMITADA] Deteniendo la descarga para proteger el flujo. Se continuará desde aquí en la próxima ejecución.", flush=True)
                print(f"      Detalle: {mensaje}", flush=True)
                cuota_agotada_b = True
                break
            print(f"   x Error en bloque ({e}): Avanzando.", flush=True)
                
        time.sleep(8)
    
    if cuota_agotada_b:
        break
            
    fecha_actual += timedelta(days=7)

print(f"\nLlamadas a Gemini realizadas en esta corrida: {llamadas_realizadas}/{MAX_LLAMADAS_POR_CORRIDA}", flush=True)
print(f"\n¡Auditoría y actualización completadas de manera exitosa!", flush=True)
