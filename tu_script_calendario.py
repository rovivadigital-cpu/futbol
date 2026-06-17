import os
import json
import csv
import time
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# =====================================================================
# CONFIGURACIÓN DE RUTA DINÁMICA (CARPETA DATOS)
# =====================================================================
csv_filename = os.path.join("datos", "calendar_futbol.csv")
os.makedirs("datos", exist_ok=True)
# =====================================================================

def limpiar_calendario_vencido(csv_filename):
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    if not os.path.exists(csv_filename): return
    try:
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        if not reader: return
        encabezados = reader[0]
        partidos_futuros = [row for row in reader[1:] if row[0] >= fecha_hoy]
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(encabezados)
            writer.writerows(partidos_futuros)
    except Exception as e:
        print(f"Error limpiando calendario: {e}")

limpiar_calendario_vencido(csv_filename)

# =====================================================================
# CARGAR TABLA DE IDs DE EQUIPOS (lookup local, sin tocar Sofascore)
# Se construye desde partidos_futbol.csv via build_equipos_ids.py
# =====================================================================
equipos_ids_file = os.path.join("datos", "equipos_ids.csv")
EQUIPOS_IDS = {}  # {nombre_normalizado: id_sofascore}

if os.path.exists(equipos_ids_file):
    try:
        with open(equipos_ids_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre = row.get("nombre_equipo", "").strip().lower()
                eid    = row.get("id_sofascore", "").strip()
                if nombre and eid:
                    EQUIPOS_IDS[nombre] = eid
        print(f"   Tabla equipos cargada: {len(EQUIPOS_IDS)} equipos.", flush=True)
    except Exception as e:
        print(f"   ! No se pudo cargar equipos_ids.csv: {e}", flush=True)
else:
    print(f"   ! equipos_ids.csv no encontrado en datos/. Los IDs de equipos quedarán vacíos.", flush=True)
    print(f"     Ejecuta build_equipos_ids.py para generarlo desde partidos_futbol.csv.", flush=True)
# =====================================================================

# =====================================================================
# LISTA DE TORNEOS
# Cada torneo tiene:
#   - nombre: nombre oficial legible (el que Gemini debería reconocer)
#   - pais:   país/región (sirve como desambiguador clave)
#   - aliases: variantes que Gemini puede devolver (en minúsculas)
# =====================================================================
TORNEOS_DATA = {
    17:    {"nombre": "Premier League",                  "pais": "England",                  "aliases": ["english premier league", "epl", "barclays premier league"]},
    18:    {"nombre": "Championship",                    "pais": "England",                  "aliases": ["english championship", "efl championship"]},
    24:    {"nombre": "League One",                      "pais": "England",                  "aliases": ["efl league one", "english league one"]},
    25:    {"nombre": "League Two",                      "pais": "England",                  "aliases": ["efl league two", "english league two"]},
    19:    {"nombre": "FA Cup",                          "pais": "England",                  "aliases": ["the fa cup"]},
    841:   {"nombre": "Algerian Ligue 1",                "pais": "Algeria",                  "aliases": ["ligue professionnelle 1", "algerie ligue 1"]},
    155:   {"nombre": "Liga Profesional de Fútbol",      "pais": "Argentina",                "aliases": ["liga profesional argentina", "lpf argentina", "primera division argentina"]},
    703:   {"nombre": "Primera Nacional",                "pais": "Argentina",                "aliases": ["nacional b argentina"]},
    1347:  {"nombre": "Primera B Metropolitana",         "pais": "Argentina",                "aliases": ["primera b metro"]},
    136:   {"nombre": "A-League Men",                   "pais": "Australia",                "aliases": ["a-league", "australian a-league", "a league men"]},
    1894:  {"nombre": "A-League Women",                 "pais": "Australia",                "aliases": ["a-league women", "australian women"]},
    1260:  {"nombre": "NPL Capital Football",            "pais": "Australia",                "aliases": []},
    1268:  {"nombre": "NPL Queensland",                  "pais": "Australia",                "aliases": []},
    709:   {"nombre": "Misli Premier League",            "pais": "Azerbaijan",               "aliases": ["azerbaijan premier league"]},
    846:   {"nombre": "Bahraini Premier League",         "pais": "Bahrain",                  "aliases": ["bahrain premier league"]},
    13331: {"nombre": "Bangladesh Football League",      "pais": "Bangladesh",               "aliases": ["bpl bangladesh"]},
    16736: {"nombre": "División Profesional",            "pais": "Bolivia",                  "aliases": ["liga boliviana", "division profesional bolivia"]},
    325:   {"nombre": "Brasileirão Série A",             "pais": "Brazil",                   "aliases": ["brasileirao betano", "brasileirao serie a", "campeonato brasileiro serie a", "serie a brasil", "serie a brazil", "brasileiro serie a"]},
    390:   {"nombre": "Brasileirão Série B",             "pais": "Brazil",                   "aliases": ["brasileirao serie b", "campeonato brasileiro serie b", "serie b brasil", "serie b brazil", "brasileiro serie b"]},
    1281:  {"nombre": "Brasileirão Série C",             "pais": "Brazil",                   "aliases": ["brasileirao serie c", "campeonato brasileiro serie c", "serie c brasil", "serie c brazil"]},
    22106: {"nombre": "Première Division de N'Djaména",  "pais": "Chad",                     "aliases": ["chad premiere division"]},
    11653: {"nombre": "Liga de Primera",                 "pais": "Chile",                    "aliases": ["primera division chile", "campeonato nacional chile"]},
    649:   {"nombre": "Chinese Super League",            "pais": "China",                    "aliases": ["csl china", "super league china"]},
    782:   {"nombre": "Chinese League 1",                "pais": "China",                    "aliases": ["china league one", "liga 1 china"]},
    11539: {"nombre": "Primera A, Apertura",             "pais": "Colombia",                 "aliases": ["liga betplay apertura", "primera a apertura colombia", "primera a colombia apertura"]},
    11536: {"nombre": "Primera A, Finalización",         "pais": "Colombia",                 "aliases": ["liga betplay finalizacion", "primera a finalizacion colombia", "primera a colombia finalizacion"]},
    1238:  {"nombre": "Categoría Primera B",             "pais": "Colombia",                 "aliases": ["primera b colombia", "categoria primera b colombia"]},
    240:   {"nombre": "LigaPro Serie A",                 "pais": "Ecuador",                  "aliases": ["liga pro ecuador", "ligapro ecuador", "primera categoria ecuador"]},
    808:   {"nombre": "Egyptian Premier League",         "pais": "Egypt",                    "aliases": ["egypt premier league", "egyptian premier league"]},
    309:   {"nombre": "World Cup Qual. OFC",             "pais": "Oceania",                  "aliases": ["ofc world cup qualifiers"]},
    1222:  {"nombre": "OFC Champions League",            "pais": "Oceania",                  "aliases": []},
    704:   {"nombre": "Erovnuli Liga",                   "pais": "Georgia",                  "aliases": ["georgian premier league", "umaglesi liga"]},
    1054:  {"nombre": "CAF Champions League",            "pais": "Africa",                   "aliases": ["caf champions league"]},
    463:   {"nombre": "AFC Champions League Elite",      "pais": "Asia",                     "aliases": ["afc champions league", "acl elite"]},
    7:     {"nombre": "UEFA Champions League",           "pais": "Europe",                   "aliases": ["champions league", "ucl"]},
    679:   {"nombre": "UEFA Europa League",              "pais": "Europe",                   "aliases": ["europa league", "uel"]},
    17015: {"nombre": "UEFA Conference League",          "pais": "Europe",                   "aliases": ["conference league", "uecl"]},
    696:   {"nombre": "UEFA Women's Champions League",   "pais": "Europe",                   "aliases": ["womens champions league"]},
    140:   {"nombre": "CONCACAF Gold Cup",               "pais": "North & Central America",  "aliases": ["gold cup"]},
    11454: {"nombre": "Campeones Cup",                   "pais": "North & Central America",  "aliases": []},
    498:   {"nombre": "CONCACAF Champions Cup",          "pais": "North & Central America",  "aliases": ["concacaf champions league", "ccl"]},
    13783: {"nombre": "Leagues Cup",                     "pais": "North & Central America",  "aliases": []},
    384:   {"nombre": "CONMEBOL Libertadores",           "pais": "South America",            "aliases": ["copa libertadores", "libertadores"]},
    480:   {"nombre": "CONMEBOL Sudamericana",           "pais": "South America",            "aliases": ["copa sudamericana", "sudamericana"]},
    133:   {"nombre": "Copa América",                    "pais": "South America",            "aliases": ["copa america"]},
    10602: {"nombre": "Copa Libertadores Femenina",      "pais": "South America",            "aliases": ["conmebol libertadores femenina"]},
    1015:  {"nombre": "Indonesia Super League",          "pais": "Indonesia",                "aliases": ["liga 1 indonesia", "bri liga 1"]},
    20708: {"nombre": "UEFA-CONMEBOL Club Challenge",    "pais": "World",                    "aliases": []},
    16:    {"nombre": "FIFA World Cup",                  "pais": "World",                    "aliases": ["world cup", "mundial"]},
    23674: {"nombre": "FIFA Intercontinental Cup",       "pais": "World",                    "aliases": ["intercontinental cup"]},
    851:   {"nombre": "International Friendly Games",    "pais": "World",                    "aliases": ["friendlies", "international friendlies"]},
    290:   {"nombre": "FIFA Women's World Cup",          "pais": "World",                    "aliases": ["women's world cup", "wwc"]},
    915:   {"nombre": "Persian Gulf Pro League",         "pais": "Iran",                     "aliases": ["iran pro league", "ipgl"]},
    206:   {"nombre": "Israeli Premier League",          "pais": "Israel",                   "aliases": ["ligat ha'al"]},
    196:   {"nombre": "J1 League",                       "pais": "Japan",                    "aliases": ["j.league", "j1 league japan"]},
    402:   {"nombre": "J2 League",                       "pais": "Japan",                    "aliases": ["j2 league japan"]},
    682:   {"nombre": "Kazakhstan Premier League",       "pais": "Kazakhstan",               "aliases": ["kpl kazakhstan"]},
    1002:  {"nombre": "Zain Premier League",             "pais": "Kuwait",                   "aliases": ["kuwait premier league"]},
    594:   {"nombre": "New Zealand National League",     "pais": "New Zealand",              "aliases": ["nznl"]},
    200:   {"nombre": "NIFL Premiership",                "pais": "Northern Ireland",         "aliases": ["northern ireland premiership"]},
    11540: {"nombre": "Primera División, Apertura",      "pais": "Paraguay",                 "aliases": ["primera division apertura paraguay", "paraguay apertura"]},
    11541: {"nombre": "Primera División, Clausura",      "pais": "Paraguay",                 "aliases": ["primera division clausura paraguay", "paraguay clausura"]},
    406:   {"nombre": "Liga 1",                          "pais": "Peru",                     "aliases": ["liga 1 peru", "liga 1 betsson"]},
    825:   {"nombre": "Stars League",                    "pais": "Qatar",                    "aliases": ["qatar stars league", "qsl"]},
    955:   {"nombre": "Saudi Pro League",                "pais": "Saudi Arabia",             "aliases": ["saudi professional league", "roshn saudi league"]},
    36:    {"nombre": "Scottish Premiership",            "pais": "Scotland",                 "aliases": ["spfl premiership", "scottish premier league"]},
    358:   {"nombre": "South African Premier Division",  "pais": "South Africa",             "aliases": ["psl south africa", "dstv premiership"]},
    52:    {"nombre": "Trendyol Süper Lig",              "pais": "Turkey",                   "aliases": ["super lig turkey", "turkish super lig", "super lig"]},
    971:   {"nombre": "UAE Pro League",                  "pais": "United Arab Emirates",     "aliases": ["arabian gulf league", "adnoc pro league"]},
    278:   {"nombre": "Liga AUF Uruguaya",               "pais": "Uruguay",                  "aliases": ["primera division uruguay", "campeonato uruguayo"]},
    13470: {"nombre": "Canadian Premier League",         "pais": "Canada",                   "aliases": ["cpl canada"]},
    11621: {"nombre": "Liga MX, Apertura",               "pais": "Mexico",                   "aliases": ["liga mx apertura", "liga mx apertura mexico"]},
    11620: {"nombre": "Liga MX, Clausura",               "pais": "Mexico",                   "aliases": ["liga mx clausura", "liga mx clausura mexico"]},
    11611: {"nombre": "Liga de Expansión MX, Apertura",  "pais": "Mexico",                   "aliases": ["expansion mx apertura", "liga expansion apertura"]},
    11612: {"nombre": "Liga de Expansión MX, Clausura",  "pais": "Mexico",                   "aliases": ["expansion mx clausura", "liga expansion clausura"]},
    242:   {"nombre": "MLS",                             "pais": "USA",                      "aliases": ["major league soccer", "mls usa"]},
    13363: {"nombre": "USL Championship",                "pais": "USA",                      "aliases": ["usl usa"]},
    18641: {"nombre": "MLS Next Pro",                    "pais": "USA",                      "aliases": ["mls next pro usa"]},
    1690:  {"nombre": "NWSL",                            "pais": "USA",                      "aliases": ["national women's soccer league", "nwsl usa"]},
    197:   {"nombre": "Virsliga",                        "pais": "Latvia",                   "aliases": ["latvian higher league"]},
    198:   {"nombre": "TOPLYGA",                         "pais": "Lithuania",                "aliases": ["a lyga lithuania", "lithuanian a lyga"]},
    211:   {"nombre": "Niké Liga",                       "pais": "Slovakia",                 "aliases": ["fortuna liga slovakia", "slovak super liga"]},
    8:     {"nombre": "LaLiga",                          "pais": "Spain",                    "aliases": ["la liga", "la liga santander", "spanish la liga", "primera division spain"]},
    54:    {"nombre": "LaLiga 2",                        "pais": "Spain",                    "aliases": ["la liga 2", "segunda division", "laliga smartbank"]},
    20:    {"nombre": "Eliteserien",                     "pais": "Norway",                   "aliases": ["norwegian eliteserien", "tippeligaen"]},
    22:    {"nombre": "Norwegian 1st Division",          "pais": "Norway",                   "aliases": ["1. divisjon norway"]},
    202:   {"nombre": "Ekstraklasa",                     "pais": "Poland",                   "aliases": ["polish ekstraklasa", "pko ekstraklasa"]},
    238:   {"nombre": "Liga Portugal Betclic",           "pais": "Portugal",                 "aliases": ["primeira liga", "liga nos", "portuguese primeira liga"]},
    152:   {"nombre": "SuperLiga României",              "pais": "Romania",                  "aliases": ["romanian superliga", "liga 1 romania"]},
    40:    {"nombre": "Allsvenskan",                     "pais": "Sweden",                   "aliases": ["swedish allsvenskan"]},
    46:    {"nombre": "Superettan",                      "pais": "Sweden",                   "aliases": ["swedish superettan"]},
    67:    {"nombre": "Ettan, Norra",                    "pais": "Sweden",                   "aliases": ["division 1 norra sweden"]},
    68:    {"nombre": "Ettan, Södra",                    "pais": "Sweden",                   "aliases": ["division 1 sodra sweden"]},
    214:   {"nombre": "Damallsvenskan",                  "pais": "Sweden",                   "aliases": ["swedish women league"]},
    218:   {"nombre": "Ukrainian Premier League",        "pais": "Ukraine",                  "aliases": ["upl ukraine"]},
    37:    {"nombre": "VriendenLoterij Eredivisie",      "pais": "Netherlands",              "aliases": ["eredivisie", "dutch eredivisie"]},
    131:   {"nombre": "Eerste Divisie",                  "pais": "Netherlands",              "aliases": ["eerste divisiee", "dutch eerste divisie"]},
    215:   {"nombre": "Swiss Super League",              "pais": "Switzerland",              "aliases": ["super league switzerland", "credit suisse super league"]},
    185:   {"nombre": "Stoiximan Super League",          "pais": "Greece",                   "aliases": ["super league greece", "greek super league"]},
    38:    {"nombre": "Pro League",                      "pais": "Belgium",                  "aliases": ["jupiler pro league", "belgian pro league"]},
    9:     {"nombre": "Challenger Pro League",           "pais": "Belgium",                  "aliases": ["belgian challenger pro league"]},
    178:   {"nombre": "Premium Liiga",                   "pais": "Estonia",                  "aliases": ["estonian premium liiga", "meistriliiga"]},
    678:   {"nombre": "Esiliiga",                        "pais": "Estonia",                  "aliases": ["estonian esiliiga"]},
    41:    {"nombre": "Veikkausliiga",                   "pais": "Finland",                  "aliases": ["finnish veikkausliiga"]},
    55:    {"nombre": "Ykkösliiga",                      "pais": "Finland",                  "aliases": ["ykkosliiga finland"]},
    34:    {"nombre": "Ligue 1",                         "pais": "France",                   "aliases": ["ligue 1 uber eats", "french ligue 1", "ligue 1 mcdonald"]},
    182:   {"nombre": "Ligue 2",                         "pais": "France",                   "aliases": ["french ligue 2", "ligue 2 bkt"]},
    35:    {"nombre": "Bundesliga",                      "pais": "Germany",                  "aliases": ["german bundesliga", "1. bundesliga", "dfl bundesliga"]},
    44:    {"nombre": "2. Bundesliga",                   "pais": "Germany",                  "aliases": ["2 bundesliga", "german 2 bundesliga", "zweite bundesliga"]},
    192:   {"nombre": "Premier Division",                "pais": "Ireland",                  "aliases": ["league of ireland premier division", "loi premier division"]},
    23:    {"nombre": "Serie A",                         "pais": "Italy",                    "aliases": ["italian serie a", "serie a tim", "calcio serie a"]},
    53:    {"nombre": "Serie B",                         "pais": "Italy",                    "aliases": ["italian serie b", "calcio serie b", "serie b bkt"]},
    45:    {"nombre": "Austrian Bundesliga",             "pais": "Austria",                  "aliases": ["admiral bundesliga", "oefb bundesliga"]},
    247:   {"nombre": "Parva Liga",                      "pais": "Bulgaria",                 "aliases": ["bulgarian first league", "efbet liga"]},
    1135:  {"nombre": "Vtora Liga",                      "pais": "Bulgaria",                 "aliases": ["bulgarian second league"]},
    205:   {"nombre": "FNL",                             "pais": "Czech Republic",           "aliases": ["czech fnl", "fortuna narodni liga"]},
    39:    {"nombre": "Danish Superliga",                "pais": "Denmark",                  "aliases": ["superliga denmark", "3f superliga"]},
    170:   {"nombre": "HNL",                             "pais": "Croatia",                  "aliases": ["hrvatska nogometna liga", "croatian football league", "supersport hnl"]},
}

# =====================================================================
# CONSTRUCCIÓN DEL MAPPING CON CLAVE COMPUESTA nombre|país
# Incluye aliases para mayor tolerancia a variaciones de Gemini
# =====================================================================
MAPPING_LIGAS = {}
for tid, info in TORNEOS_DATA.items():
    # Clave principal: nombre oficial + país
    clave_principal = f"{info['nombre'].lower()}|{info['pais'].lower()}"
    MAPPING_LIGAS[clave_principal] = {"id": tid, **info}

    # Claves alias: cada alias + país
    for alias in info.get("aliases", []):
        clave_alias = f"{alias.lower()}|{info['pais'].lower()}"
        if clave_alias not in MAPPING_LIGAS:
            MAPPING_LIGAS[clave_alias] = {"id": tid, **info}

    # Fallback solo-nombre (menor prioridad, puede haber colisiones)
    # Solo se registra si no existe aún para no pisar claves ya definidas
    clave_solo_nombre = info['nombre'].lower()
    if clave_solo_nombre not in MAPPING_LIGAS:
        MAPPING_LIGAS[clave_solo_nombre] = {"id": tid, **info}

# =====================================================================

partidos_existentes = set()

headers = [
    "Fecha", "Hora_Local", "Pais", "Competicion", "Competicion_ID_Sofascore",
    "Torneo", "Torneo_ID_Sofascore", "Ronda", "Equipo_Local",
    "Equipo_Local_ID_Sofascore", "Pais_Local", "Equipo_Visitante",
    "Equipo_Visitante_ID_Sofascore", "Pais_Visitante", "Marcador", "Estado"
]

if not os.path.exists(csv_filename):
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
print(f" INICIANDO CALENDARIO CON IDS DE SOFASCORE ", flush=True)
print(f"==================================================", flush=True)

# =====================================================================
# Construir el prompt con nombre + país para que Gemini no confunda
# torneos homónimos (Serie B Italy vs Serie B Brazil, Ligue 1 France
# vs Algerian Ligue 1, etc.)
# =====================================================================
lista_ligas_prompt = "\n".join([
    f'  - "{info["nombre"]}" | País: {info["pais"]}'
    for info in TORNEOS_DATA.values()
])

for fecha_obj, etiqueta in dias_a_revisar:
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    print(f"\n-> Buscando partidos para {etiqueta} ({fecha_str})...", flush=True)

    prompt = f"""
Busca el calendario de partidos de fútbol para la fecha {fecha_str}.
Solo incluye partidos de EXACTAMENTE estas ligas (nombre y país):

{lista_ligas_prompt}

REGLAS IMPORTANTES:
- El campo "liga_nombre_oficial" debe ser EXACTAMENTE el nombre que aparece en la lista anterior (respeta tildes, mayúsculas y formato).
- El campo "liga_pais" debe ser EXACTAMENTE el país que aparece junto al nombre en la lista.
- Si un torneo tiene un nombre similar en otro país (ej: "Serie B" existe en Italia y Brasil), usa el país para distinguirlos.
- No incluyas partidos de ligas que no estén en la lista.
- Si no hay partidos para una liga ese día, simplemente no la incluyas.

Devuelve ÚNICAMENTE un objeto JSON con este formato, sin texto adicional:
{{
  "partidos": [
    {{
      "liga_nombre_oficial": "...",
      "liga_pais": "...",
      "tourney_season": "...",
      "round": "...",
      "hora": "HH:MM",
      "home_team_name": "...",
      "home_team_country": "...",
      "away_team_name": "...",
      "away_team_country": "..."
    }}
  ]
}}

Si no hay ningún partido ese día, devuelve {{"partidos": []}}.
"""

    try:
        config_llamada = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=config_llamada)
        texto = (response.text or "").strip()

        # Limpieza robusta de JSON
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio == -1 or fin == -1:
            print(f"   x Error: La respuesta no contiene un JSON válido.")
            continue

        texto_limpio = texto[inicio:fin+1]
        data = json.loads(texto_limpio)
        partidos = data.get("partidos", [])

        if partidos:
            partidos_guardados = 0
            partidos_descartados = 0
            with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for p in partidos:
                    liga_raw  = str(p.get("liga_nombre_oficial", "")).strip().lower()
                    pais_raw  = str(p.get("liga_pais", "")).strip().lower()
                    local     = str(p.get("home_team_name", "")).strip()
                    visita    = str(p.get("away_team_name", "")).strip()

                    if not local or not visita:
                        continue

                    # -------------------------------------------------------
                    # Lookup con clave compuesta nombre|país (más seguro)
                    # Si no encuentra, intenta solo por nombre (fallback)
                    # -------------------------------------------------------
                    clave_compuesta = f"{liga_raw}|{pais_raw}"
                    liga_info = MAPPING_LIGAS.get(clave_compuesta) or MAPPING_LIGAS.get(liga_raw)

                    if not liga_info:
                        partidos_descartados += 1
                        print(f"   ! Descartado (liga no reconocida): '{liga_raw}' | '{pais_raw}'", flush=True)
                        continue

                    llave_partido = f"{fecha_str}_{local}_{visita}".strip().lower()
                    if llave_partido in partidos_existentes:
                        continue

                    partidos_existentes.add(llave_partido)
                    partidos_guardados += 1

                    id_sofascore = liga_info["id"]

                    local_id  = EQUIPOS_IDS.get(local.strip().lower(), "")
                    visita_id = EQUIPOS_IDS.get(visita.strip().lower(), "")

                    row = [
                        fecha_str,
                        p.get("hora", "00:00"),
                        liga_info["pais"],
                        liga_info["nombre"],
                        id_sofascore,
                        liga_info["nombre"],
                        "",
                        p.get("round", ""),
                        local,
                        local_id,
                        p.get("home_team_country", ""),
                        visita,
                        visita_id,
                        p.get("away_team_country", ""),
                        "",
                        "Programado"
                    ]
                    writer.writerow(row)

            print(f"   + Guardados: {partidos_guardados} | Descartados: {partidos_descartados}", flush=True)
        else:
            print("   o No se encontraron partidos.", flush=True)

    except json.JSONDecodeError:
        print(f"   x Error: El JSON devuelto por la IA estaba mal formado o incompleto.")
    except Exception as e:
        print(f"   x Error inesperado: {e}", flush=True)

    time.sleep(6)

print(f"\n Proceso finalizado. Archivo: '{csv_filename}'.", flush=True)


