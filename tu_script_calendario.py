import os
import json
import csv
import time
import hashlib
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# =====================================================================
# CONFIGURACIÓN DE RUTA DINÁMICA (CARPETA DATOS)
# =====================================================================
csv_filename = os.path.join("datos", "futbol_calendario.csv")
os.makedirs("datos", exist_ok=True)
# =====================================================================

# Diccionario oficial de torneos para mapear IDs y Nombres
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
    44: {"nombre": "2. Bundesliga", "sanity": "Germany"},
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

# Invertir el diccionario para buscar IDs oficiales usando "Nombre de Liga"
MAPPING_LIGAS = {info["nombre"].lower(): {"id": tid, "pais": info["pais"]} for tid, info in TORNEOS_IDS.items()}

partidos_existentes = set()

def generar_event_id(fecha, local, visita):
    clave = f"{fecha.strip()}_{local.strip().lower()}_{visita.strip().lower()}".encode('utf-8')
    return int(hashlib.md5(clave).hexdigest()[:8], 16) % 100000000

# Inicializar archivo de calendario con los mismos encabezados estructurales
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

# Si el archivo no existe, lo creamos con cabeceras. Si existe, leemos lo que hay para no duplicar en la misma corrida
if os.path.exists(csv_filename):
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None) # saltar headers
        for row in reader:
            if len(row) > 12:
                # llave única: fecha_local_visita
                partidos_existentes.add(f"{row[6]}_{row[10]}_{row[12]}".strip().lower())
else:
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(headers)

# Configurar Cliente de API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")
client = genai.Client(api_key=api_key)

# Generar rango de días: Hoy, Mañana y Pasado Mañana
fecha_base = datetime.now()
dias_a_revisar = [
    (fecha_base, "HOY"),
    (fecha_base + timedelta(days=1), "MAÑANA"),
    (fecha_base + timedelta(days=2), "PASADO MAÑANA")
]

MODEL_NAME = "gemini-2.5-flash-lite"
scrape_date_str = fecha_base.strftime('%Y-%m-%d')

print(f"==================================================", flush=True)
print(f" INICIANDO EXTRACCIÓN DE CALENDARIO DE PARTIDOS  ", flush=True)
print(f"==================================================", flush=True)

for fecha_obj, etiqueta in dias_a_revisar:
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    print(f"\n-> Buscando partidos programados para {etiqueta} ({fecha_str})...", flush=True)

    # Creamos una lista limpia en texto de las ligas que nos interesan para pasárselas al Prompt
    lista_ligas_prompt = ", ".join([info["nombre"] for info in TORNEOS_IDS.values()])

    prompt = f"""
    Busca en la web el calendario de partidos oficiales programados para el día {fecha_str} exclusivamente para las siguientes ligas de fútbol:
    [{lista_ligas_prompt}]

    Devuelve los datos estrictamente en este formato JSON plano, sin bloques markdown ni texto explicativo:
    {{
      "partidos": [
        {{
          "liga_nombre_oficial": "Nombre de la liga tal cual viene en la lista de arriba",
          "tourney_season": "Nombre oficial de la temporada (ej: Premier League 25/26 o Primera A 2026)",
          "round": "Jornada X o Fase",
          "round_number": "X",
          "home_team_name": "Nombre equipo local",
          "away_team_name": "Nombre equipo visitante"
        }}
      ]
    }}
    If there are no matches scheduled for any of those leagues on that day, return an empty list: {{"partidos": []}}
    """

    try:
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
        if texto_limpio.startswith("```json"):
            texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
        elif texto_limpio.startswith("```"):
            texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()

        if not texto_limpio.startswith("{"):
            inicio = texto_limpio.find("{")
            fin = texto_limpio.rfind("}")
            if inicio != -1 and fin != -1:
                texto_limpio = texto_limpio[inicio:fin+1]
            else:
                texto_limpio = "{}"

        data = json.loads(texto_limpio)
        partidos = data.get("partidos", [])

        if partidos:
            partidos_guardados = 0
            with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for p in partidos:
                    liga_raw = str(p.get("liga_nombre_oficial", "")).strip().lower()
                    local = str(p.get("home_team_name", "")).strip()
                    visita = str(p.get("away_team_name", "")).strip()

                    if not local or not visita or liga_raw not in MAPPING_LIGAS:
                        continue

                    # Verificar duplicados en el archivo actual
                    llave_partido = f"{fecha_str}_{local}_{visita}".strip().lower()
                    if llave_partido in partidos_existentes:
                        continue

                    partidos_existentes.add(llave_partido)
                    partidos_guardados += 1

                    # Recuperar metadatos desde el diccionario base
                    liga_info = MAPPING_LIGAS[liga_raw]
                    tor_id = liga_info["id"]
                    pais_nombre = liga_info["pais"]
                    liga_nombre_correcto = TORNEOS_IDS[tor_id]["nombre"]
                    season = p.get("tourney_season", f"{liga_nombre_correcto} {fecha_str[:4]}")

                    # ID único consistente con el histórico
                    event_id = generar_event_id(fecha_str, local, visita)

                    # Estructura idéntica al histórico original (goles y estadísticas vacías)
                    row = [
                        event_id, pais_nombre, liga_nombre_correcto, tor_id, liga_nombre_correcto, season, fecha_str,
                        p.get("round", ""), p.get("round_number", ""), "", local, "", visita,
                        "", "", "", "", "", "", "", "", "", scrape_date_str,  # Goles y resultados en blanco
                        "50%", "50%", 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  # Stats por defecto
                    ]
                    writer.writerow(row)
            print(f"   + Guardados {partidos_guardados} partidos programados en el CSV.", flush=True)
        else:
            print("   o No se encontraron partidos programados para nuestras ligas en esta fecha.", flush=True)

    except Exception as e:
        print(f"   x Error procesando fecha {fecha_str}: {e}", flush=True)

    # Espera preventiva de cortesía entre llamadas del Cron
    time.sleep(6)

print(f"\n Archivo de programación '{csv_filename}' listo y actualizado.", flush=True)
