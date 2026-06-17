import os
import json
import csv
import time
import random
from datetime import datetime, timedelta
from google import genai
from google.genai import types
from curl_cffi import requests as cffi_requests

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
# CACHÉ DE IDs DE EQUIPOS (lookup local + búsqueda en Sofascore)
# Se persiste en datos/equipos_ids.csv entre ejecuciones.
# Solo consulta Sofascore para equipos que no están en caché.
# =====================================================================
import re

def normalizar_equipo(nombre: str) -> str:
    """
    Normaliza el nombre de un equipo para deduplicación robusta.
    Elimina prefijos/sufijos comunes (FC, CF, SC, AC, CD, etc.),
    puntuación, y colapsa espacios. Todo en minúsculas.
    Ejemplos:
      'FC Barcelona'  → 'barcelona'
      'Barcelona FC'  → 'barcelona'
      'Atlético de Madrid CF' → 'atletico de madrid'
      'Manchester United FC' → 'manchester united'
    """
    import unicodedata
    # Lowercase
    s = nombre.strip().lower()
    # Quitar acentos
    s = ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )
    # Eliminar sufijos comunes al final: fc, cf, sc, ac, cd, sd, afc, fk, sk, bk, if, ik, ff, ss, as, us, sv
    s = re.sub(
        r'\b(f\.?c\.?|c\.?f\.?|s\.?c\.?|a\.?c\.?|c\.?d\.?|s\.?d\.?|a\.?f\.?c\.?|'
        r'f\.?k\.?|s\.?k\.?|b\.?k\.?|i\.?f\.?|i\.?k\.?|f\.?f\.?|s\.?s\.?|a\.?s\.?|'
        r'u\.?s\.?|s\.?v\.?|r\.?c\.?|r\.?s\.?c\.?|k\.?f\.?c\.?|o\.?f\.?k\.?)\s*$',
        '', s
    ).strip()
    # Eliminar prefijos comunes al inicio
    s = re.sub(
        r'^\s*(f\.?c\.?|c\.?f\.?|s\.?c\.?|a\.?c\.?|c\.?d\.?|s\.?d\.?|a\.?f\.?c\.?|'
        r'f\.?k\.?|s\.?k\.?|b\.?k\.?|r\.?c\.?|r\.?s\.?c\.?|k\.?f\.?c\.?|c\.?a\.?|'
        r'c\.?s\.?d\.?|p\.?f\.?c\.?|h\.?n\.?k\.?|n\.?k\.?|g\.?d\.?)\s+',
        '', s
    ).strip()
    # Eliminar puntuación sobrante y colapsar espacios
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

equipos_ids_file = os.path.join("datos", "equipos_ids.csv")
EQUIPOS_IDS = {}  # {nombre_normalizado: id_sofascore}

def guardar_cache_equipos():
    """Persiste el caché actual en disco."""
    with open(equipos_ids_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nombre_equipo", "id_sofascore"])
        writer.writeheader()
        for nombre_lower, eid in sorted(EQUIPOS_IDS.items()):
            writer.writerow({"nombre_equipo": nombre_lower, "id_sofascore": eid})

# Cargar caché existente
if os.path.exists(equipos_ids_file):
    try:
        with open(equipos_ids_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nombre = row.get("nombre_equipo", "").strip().lower()
                eid    = row.get("id_sofascore", "").strip()
                if nombre and eid:
                    EQUIPOS_IDS[nombre] = eid
        print(f"   Caché equipos cargado: {len(EQUIPOS_IDS)} equipos.", flush=True)
    except Exception as e:
        print(f"   ! Error cargando caché de equipos: {e}", flush=True)

# Headers para impersonar Chrome ante Sofascore
SOFASCORE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Cache-Control": "no-cache",
}

# Marcador para equipos buscados pero no encontrados (evita reintentar)
NO_ENCONTRADO = "__NOT_FOUND__"
_cache_nuevos = 0  # contador de IDs nuevos encontrados en esta ejecución

def buscar_id_equipo_sofascore(nombre_equipo: str) -> str:
    """
    Busca el ID de un equipo en Sofascore por nombre.
    Devuelve el ID como string, o "" si no se encuentra.
    Respeta el caché: no vuelve a buscar equipos ya procesados.
    Si SOFASCORE_IDS_ACTIVO=false (Actions), solo usa caché y no hace requests.
    """
    global _cache_nuevos
    key = nombre_equipo.strip().lower()

    # Ya está en caché (encontrado o marcado como no-encontrado)
    if key in EQUIPOS_IDS:
        val = EQUIPOS_IDS[key]
        return "" if val == NO_ENCONTRADO else val

    # Si las búsquedas están desactivadas (ej: GitHub Actions), no hacer request
    if os.environ.get("SOFASCORE_IDS_ACTIVO", "true").lower() == "false":
        return ""

    # Pausa humana antes de la request
    time.sleep(random.uniform(2.5, 5.0))

    try:
        url = f"https://api.sofascore.com/api/v1/search/all?q={nombre_equipo}"
        resp = cffi_requests.get(
            url,
            headers=SOFASCORE_HEADERS,
            impersonate="chrome124",
            timeout=15,
        )

        if resp.status_code != 200:
            print(f"   ! Sofascore {resp.status_code} para '{nombre_equipo}'", flush=True)
            EQUIPOS_IDS[key] = NO_ENCONTRADO
            return ""

        data = resp.json()
        teams = data.get("teams", [])

        if not teams:
            print(f"   ~ Sin resultados Sofascore para '{nombre_equipo}'", flush=True)
            EQUIPOS_IDS[key] = NO_ENCONTRADO
            return ""

        # Intentar match exacto primero, luego tomar el primero
        eid = ""
        for t in teams:
            if t.get("name", "").strip().lower() == key or \
               t.get("shortName", "").strip().lower() == key:
                eid = str(t.get("id", ""))
                break
        if not eid:
            eid = str(teams[0].get("id", ""))

        if eid:
            EQUIPOS_IDS[key] = eid
            _cache_nuevos += 1
            print(f"   + ID encontrado: '{nombre_equipo}' → {eid}", flush=True)

        return eid

    except Exception as e:
        print(f"   ! Error buscando '{nombre_equipo}': {e}", flush=True)
        EQUIPOS_IDS[key] = NO_ENCONTRADO
        return ""
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

# Precargar partidos ya existentes en el CSV para evitar duplicados
# entre runs múltiples del mismo día
partidos_existentes = set()

headers = [
    "Fecha", "Hora_Local", "Pais", "Competicion", "Competicion_ID_Sofascore",
    "Torneo", "Torneo_ID_Sofascore", "Ronda", "Equipo_Local",
    "Equipo_Local_ID_Sofascore", "Pais_Local", "Equipo_Visitante",
    "Equipo_Visitante_ID_Sofascore", "Pais_Visitante", "Marcador", "Estado"
]

if os.path.exists(csv_filename):
    try:
        with open(csv_filename, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                fecha  = row.get("Fecha", "").strip()
                local  = row.get("Equipo_Local", "").strip()
                visita = row.get("Equipo_Visitante", "").strip()
                if fecha and local and visita:
                    llave = f"{fecha}_{normalizar_equipo(local)}_{normalizar_equipo(visita)}"
                    partidos_existentes.add(llave)
        print(f"   Partidos ya en CSV: {len(partidos_existentes)}", flush=True)
    except Exception as e:
        print(f"   ! Error leyendo CSV existente: {e}", flush=True)
else:
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
# Agrupar torneos en bloques de 10 para reducir alucinaciones de Gemini
# Menos ligas por prompt = más precisión, menos partidos inventados
# =====================================================================
TAMAÑO_GRUPO = 10
torneos_lista = list(TORNEOS_DATA.items())
grupos_torneos = [
    torneos_lista[i:i + TAMAÑO_GRUPO]
    for i in range(0, len(torneos_lista), TAMAÑO_GRUPO)
]

def construir_prompt(fecha_str, grupo):
    lista_ligas = "\n".join([
        f'  - "{info["nombre"]}" | País: {info["pais"]}'
        for _, info in grupo
    ])
    return f"""Busca el calendario de partidos de fútbol para la fecha {fecha_str}.
Solo incluye partidos de EXACTAMENTE estas ligas (nombre y país):

{lista_ligas}

REGLAS IMPORTANTES:
- El campo "liga_nombre_oficial" debe ser EXACTAMENTE el nombre de la lista (respeta tildes, mayúsculas y formato).
- El campo "liga_pais" debe ser EXACTAMENTE el país de la lista.
- NO incluyas partidos de ligas que no estén en esta lista exacta.
- NO inventes partidos. Si no tienes información confirmada de un partido, no lo incluyas.
- Si no hay partidos para ninguna liga ese día, devuelve {{"partidos": []}}.

Devuelve ÚNICAMENTE un objeto JSON sin texto adicional:
{{
  "partidos": [
    {{
      "liga_nombre_oficial": "...",
      "liga_pais": "...",
      "round": "...",
      "hora": "HH:MM",
      "home_team_name": "...",
      "home_team_country": "...",
      "away_team_name": "...",
      "away_team_country": "..."
    }}
  ]
}}"""

config_llamada = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch())],
    temperature=0.1,
    max_output_tokens=4096,
    thinking_config=types.ThinkingConfig(thinking_budget=0)
)

fecha_base = datetime.now()
dias_a_revisar = [
    (fecha_base, "HOY"),
    (fecha_base + timedelta(days=1), "MAÑANA"),
]

for fecha_obj, etiqueta in dias_a_revisar:
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    print(f"\n{'='*54}", flush=True)
    print(f"-> {etiqueta} ({fecha_str}) — {len(grupos_torneos)} grupos de ligas", flush=True)
    print(f"{'='*54}", flush=True)

    total_guardados   = 0
    total_descartados = 0

    for idx, grupo in enumerate(grupos_torneos, 1):
        nombres_grupo = ", ".join(info["nombre"] for _, info in grupo)
        print(f"\n  Grupo {idx}/{len(grupos_torneos)}: {nombres_grupo[:80]}...", flush=True)

        prompt = construir_prompt(fecha_str, grupo)

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config_llamada
            )
            texto = (response.text or "").strip()

            inicio = texto.find("{")
            fin    = texto.rfind("}")
            if inicio == -1 or fin == -1:
                print(f"  x Sin JSON válido en respuesta.", flush=True)
                time.sleep(3)
                continue

            data     = json.loads(texto[inicio:fin+1])
            partidos = data.get("partidos", [])

            if not partidos:
                print(f"  o Sin partidos.", flush=True)
                time.sleep(3)
                continue

            guardados   = 0
            descartados = 0

            with open(csv_filename, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for p in partidos:
                    liga_raw = str(p.get("liga_nombre_oficial", "")).strip().lower()
                    pais_raw = str(p.get("liga_pais", "")).strip().lower()
                    local    = str(p.get("home_team_name", "")).strip()
                    visita   = str(p.get("away_team_name", "")).strip()

                    if not local or not visita:
                        continue

                    # -------------------------------------------------------
                    # Filtro 1: nombres placeholder que Gemini inventa cuando
                    # no sabe los equipos reales (ej: "Ranked 1st", "TBD",
                    # "Winner Group A", "Team A", etc.)
                    # -------------------------------------------------------
                    PLACEHOLDERS = re.compile(
                        r'^(ranked\s+\d|tbd|tbf|tba|winner|loser|team\s+[a-z]|'
                        r'group\s+[a-z]|\d+st|\d+nd|\d+rd|\d+th)',
                        re.IGNORECASE
                    )
                    if PLACEHOLDERS.match(local) or PLACEHOLDERS.match(visita):
                        descartados += 1
                        print(f"  ! Descartado (nombre placeholder): '{local}' vs '{visita}'", flush=True)
                        continue

                    # -------------------------------------------------------
                    # Filtro 2: equipos femeninos en ligas masculinas.
                    # Si el nombre contiene sufijos femeninos comunes, descartar.
                    # -------------------------------------------------------
                    SUFIJOS_FEMENINOS = re.compile(
                        r'\b(women|woman|ladies|femenino|femenina|girls|femmes|dames|'
                        r'mujer|vrouwen|frauen|damlag|kvinder|naiset)\b',
                        re.IGNORECASE
                    )
                    if SUFIJOS_FEMENINOS.search(local) or SUFIJOS_FEMENINOS.search(visita):
                        descartados += 1
                        print(f"  ! Descartado (equipo femenino en liga masculina): '{local}' vs '{visita}'", flush=True)
                        continue


                    # Gemini meta ligas de otros grupos o ligas inventadas)
                    ids_grupo = {tid for tid, _ in grupo}
                    clave_compuesta = f"{liga_raw}|{pais_raw}"
                    liga_info = MAPPING_LIGAS.get(clave_compuesta) or MAPPING_LIGAS.get(liga_raw)

                    if not liga_info or liga_info["id"] not in ids_grupo:
                        descartados += 1
                        print(f"  ! Descartado (fuera de grupo): '{liga_raw}' | '{pais_raw}'", flush=True)
                        continue

                    llave_partido = f"{fecha_str}_{normalizar_equipo(local)}_{normalizar_equipo(visita)}"
                    if llave_partido in partidos_existentes:
                        print(f"  ~ Duplicado ignorado: {local} vs {visita}", flush=True)
                        continue

                    partidos_existentes.add(llave_partido)
                    guardados += 1

                    local_id  = buscar_id_equipo_sofascore(local)
                    visita_id = buscar_id_equipo_sofascore(visita)

                    writer.writerow([
                        fecha_str,
                        p.get("hora", "00:00"),
                        liga_info["pais"],
                        liga_info["nombre"],
                        liga_info["id"],
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
                    ])

            total_guardados   += guardados
            total_descartados += descartados
            print(f"  + Guardados: {guardados} | Descartados: {descartados}", flush=True)

        except json.JSONDecodeError:
            print(f"  x JSON malformado en grupo {idx}.", flush=True)
        except Exception as e:
            print(f"  x Error en grupo {idx}: {e}", flush=True)

        time.sleep(4)

    print(f"\n  TOTAL {etiqueta}: {total_guardados} guardados | {total_descartados} descartados", flush=True)


# =====================================================================
# PERSISTIR CACHÉ DE EQUIPOS
# =====================================================================
if _cache_nuevos > 0:
    try:
        guardar_cache_equipos()
        print(f"\n   Caché actualizado: {_cache_nuevos} IDs nuevos guardados en {equipos_ids_file}", flush=True)
    except Exception as e:
        print(f"\n   ! Error guardando caché de equipos: {e}", flush=True)

# =====================================================================
# ORDENAR CSV POR FECHA → HORA Y MOSTRAR RESUMEN FINAL
# =====================================================================
try:
    if os.path.exists(csv_filename):
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))

        if len(reader) > 1:
            encabezados = reader[0]
            filas = reader[1:]

            # Ordenar por Fecha (col 0) y Hora_Local (col 1)
            filas.sort(key=lambda r: (r[0], r[1]))

            with open(csv_filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(encabezados)
                writer.writerows(filas)

            total = len(filas)

            # --- Resumen por país (col 2) ---
            conteo_pais = {}
            for r in filas:
                pais = r[2] if len(r) > 2 else "Desconocido"
                conteo_pais[pais] = conteo_pais.get(pais, 0) + 1

            # --- Resumen por competición (col 3) ---
            conteo_comp = {}
            for r in filas:
                comp = r[3] if len(r) > 3 else "Desconocida"
                conteo_comp[comp] = conteo_comp.get(comp, 0) + 1

            print(f"\n{'='*54}", flush=True)
            print(f"  RESUMEN FINAL — {total} partidos guardados", flush=True)
            print(f"{'='*54}", flush=True)

            print(f"\n  Partidos por país (Top 15):", flush=True)
            for pais, cnt in sorted(conteo_pais.items(), key=lambda x: -x[1])[:15]:
                print(f"    {pais:<30} {cnt:>4}", flush=True)

            print(f"\n  Partidos por competición (Top 20):", flush=True)
            for comp, cnt in sorted(conteo_comp.items(), key=lambda x: -x[1])[:20]:
                print(f"    {comp:<40} {cnt:>4}", flush=True)

            print(f"\n{'='*54}", flush=True)
        else:
            print("\n  Sin partidos en el archivo.", flush=True)

except Exception as e:
    print(f"\n   ! Error generando resumen: {e}", flush=True)

print(f"\n Proceso finalizado. Archivo: '{csv_filename}'.", flush=True)


