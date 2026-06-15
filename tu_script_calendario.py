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
csv_filename = os.path.join("datos", "calendar_futbol.csv")
os.makedirs("datos", exist_ok=True)
# =====================================================================

# =====================================================================
# LIMPIEZA DE DATOS VENCIDOS
# =====================================================================
def limpiar_calendario_vencido(csv_filename):
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    if not os.path.exists(csv_filename): return

    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    
    if not reader: return
    encabezados = reader[0]
    partidos_futuros = [row for row in reader[1:] if row[0] >= fecha_hoy]
    
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(encabezados)
        writer.writerows(partidos_futuros)

limpiar_calendario_vencido(csv_filename)

# =====================================================================
# LISTA DE TORNEOS (Ahora es un DICCIONARIO para soportar los IDs)
# =====================================================================
TORNEOS_DATA = {
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

# Generar un mapeo seguro: { 'premier league': {'id': 17, 'nombre': 'Premier League', 'pais': 'England'}, ... }
MAPPING_LIGAS = {}
for tourney_id, info in TORNEOS_DATA.items():
    MAPPING_LIGAS[info["nombre"].lower()] = {"id": tourney_id, **info}

partidos_existentes = set()

def generar_event_id(fecha, local, visita):
    clave = f"{fecha.strip()}_{local.strip().lower()}_{visita.strip().lower()}".encode('utf-8')
    return int(hashlib.md5(clave).hexdigest()[:8], 16) % 100000000

headers = [
    "Fecha", "Hora_Local", "Pais", "Competicion", "Competicion_ID_Sofascore", 
    "Torneo", "Torneo_ID_Sofascore", "Ronda", "Equipo_Local", 
    "Equipo_Local_ID_Sofascore", "Pais_Local", "Equipo_Visitante", 
    "Equipo_Visitante_ID_Sofascore", "Pais_Visitante", "Marcador", "Estado"
]

archivo_existe = os.path.exists(csv_filename)
if not archivo_existe:
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

api_key = os.environ.get("GEMINI_API_KEY2")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY2 no está configurada.")
client = genai.Client(api_key=api_key)

fecha_base = datetime.now()
dias_a_revisar = [
    (fecha_base, "HOY"),
    (fecha_base + timedelta(days=1), "MAÑANA"),
    (fecha_base + timedelta(days=2), "PASADO MAÑANA")
]

MODEL_NAME = "gemini-2.5-flash-lite"

print(f"==================================================", flush=True)
print(f" INICIANDO CALENDARIO CON IDs DE SOFASCORE ", flush=True)
print(f"==================================================", flush=True)

for fecha_obj, etiqueta in dias_a_revisar:
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    print(f"\n-> Buscando partidos para {etiqueta} ({fecha_str})...", flush=True)

    # Extraemos solo los nombres de las ligas para el prompt
    lista_ligas_prompt = ", ".join([info["nombre"] for info in TORNEOS_DATA.values()])

    prompt = f"""
    Busca el calendario de partidos para los próximos 3 días para las siguientes ligas: [{lista_ligas_prompt}].
    Devuelve un JSON estrictamente con este formato:
    {{
      "partidos": [
        {{
          "liga_nombre_oficial": "...",
          "tourney_season": "...",
          "round": "...",
          "round_number": "...",
          "hora": "HH:MM", 
          "home_team_name": "...",
          "home_team_country": "...",
          "away_team_name": "...",
          "away_team_country": "..."
        }}
      ]
    }}
    Si no hay partidos, devuelve {{"partidos": []}}.
    """

    try:
        config_llamada = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=config_llamada)

        texto_limpio = (response.text or "").strip()
        if "```json" in texto_limpio:
            texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
        elif "```" in texto_limpio:
            texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()

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

                    llave_partido = f"{fecha_str}_{local}_{visita}".strip().lower()
                    if llave_partido in partidos_existentes:
                        continue

                    partidos_existentes.add(llave_partido)
                    partidos_guardados += 1

                    # Recuperar info incluyendo el ID
                    liga_info = MAPPING_LIGAS[liga_raw]
                    id_sofascore = liga_info["id"] # <--- AQUÍ ESTÁ EL NÚMERO
                    
                    row = [
                        fecha_str,                  # Fecha
                        p.get("hora", "00:00"),     # Hora_Local
                        liga_info["pais"],          # Pais
                        liga_info["nombre"],        # Competicion
                        id_sofascore,                # Competicion_ID_Sofascore (EL NÚMERO)
                        liga_info["nombre"],        # Torneo
                        "",                          # Torneo_ID_Sofascore
                        p.get("round", ""),         # Ronda
                        local,                      # Equipo_Local
                        "",                         # Equipo_Local_ID_Sofascore
                        p.get("home_team_country", ""), # Pais_Local
                        visita,                      # Equipo_Visitante
                        "",                         # Equipo_Visitante_ID_Sofascore
                        p.get("away_team_country", ""), # Pais_Visitante
                        "",                         # Marcador
                        "Programado"                # Estado
                    ]
                    writer.writerow(row)
            print(f"   + Guardados {partidos_guardados} partidos.", flush=True)
        else:
            print("   o No hay partidos.", flush=True)

    except Exception as e:
        print(f"   x Error: {e}", flush=True)

    time.sleep(6)

print(f"\n Proceso finalizado. Archivo: '{csv_filename}'.", flush=True)

