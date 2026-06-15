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
# Cada entrada incluye "equipos_muestra": palabras clave de equipos típicos de esa liga.
# Se usa para detectar si Gemini devolvió equipos del país/liga equivocados.
TORNEOS_IDS = {
    17:    {"nombre": "Premier League",                 "pais": "England",                 "equipos_muestra": ["arsenal", "chelsea", "liverpool", "manchester", "tottenham", "city", "united", "newcastle", "west ham", "aston villa"]},
    18:    {"nombre": "Championship",                   "pais": "England",                 "equipos_muestra": ["leeds", "sheffield", "burnley", "middlesbrough", "sunderland", "norwich", "bristol", "coventry", "hull", "cardiff"]},
    24:    {"nombre": "League One",                     "pais": "England",                 "equipos_muestra": ["barnsley", "oxford", "bolton", "portsmouth", "derby", "charlton", "exeter", "burton", "stockport", "peterborough"]},
    25:    {"nombre": "League Two",                     "pais": "England",                 "equipos_muestra": ["swindon", "mansfield", "salford", "crewe", "grimsby", "harrogate", "stevenage", "crawley", "colchester", "wrexham"]},
    19:    {"nombre": "FA Cup",                         "pais": "England",                 "equipos_muestra": ["arsenal", "chelsea", "liverpool", "manchester", "tottenham"]},
    841:   {"nombre": "Algerian Ligue 1",               "pais": "Algeria",                 "equipos_muestra": ["mouloudia", "usm alger", "es setif", "cr belouizdad", "js kabylie", "mc oran"]},
    155:   {"nombre": "Liga Profesional de Fútbol",     "pais": "Argentina",               "equipos_muestra": ["boca", "river", "racing", "independiente", "san lorenzo", "velez", "talleres", "estudiantes", "huracan", "lanus"]},
    703:   {"nombre": "Primera Nacional",               "pais": "Argentina",               "equipos_muestra": ["brown", "quilmes", "chaco for ever", "almagro", "san martin", "atletico", "gimnasia"]},
    1347:  {"nombre": "Primera B Metropolitana",        "pais": "Argentina",               "equipos_muestra": ["colegiales", "acassuso", "deportivo riestra", "defensores", "villa san carlos"]},
    136:   {"nombre": "A-League Men",                   "pais": "Australia",               "equipos_muestra": ["sydney", "melbourne", "perth", "brisbane", "adelaide", "wellington", "central coast", "western united"]},
    1894:  {"nombre": "A-League Women",                 "pais": "Australia",               "equipos_muestra": ["sydney", "melbourne", "perth", "brisbane", "adelaide", "canberra", "western united"]},
    1260:  {"nombre": "NPL Capital Football",           "pais": "Australia",               "equipos_muestra": ["canberra", "gungahlin", "tuggeranong", "brindabella", "belconnen"]},
    1268:  {"nombre": "NPL Queensland",                 "pais": "Australia",               "equipos_muestra": ["brisbane", "olympic", "easts", "lions", "rochedale", "north star"]},
    709:   {"nombre": "Misli Premier League",           "pais": "Azerbaijan",              "equipos_muestra": ["qarabag", "neftchi", "sabah", "shamakhi", "zira", "kapaz"]},
    846:   {"nombre": "Bahraini Premier League",        "pais": "Bahrain",                 "equipos_muestra": ["al riffa", "al muharraq", "al hidd", "east riffa", "al ahli"]},
    13331: {"nombre": "Bangladesh Football League",     "pais": "Bangladesh",              "equipos_muestra": ["abahani", "mohammedan", "bashundhara", "sheikh russel"]},
    16736: {"nombre": "División Profesional",           "pais": "Bolivia",                 "equipos_muestra": ["bolivar", "the strongest", "wilstermann", "blooming", "oriente petrolero"]},
    325:   {"nombre": "Brasileirão Série A",            "pais": "Brazil",                  "equipos_muestra": ["flamengo", "palmeiras", "atletico mineiro", "fluminense", "corinthians", "sao paulo", "santos", "gremio", "internacional", "botafogo", "vasco", "cruzeiro", "bahia", "fortaleza"]},
    390:   {"nombre": "Brasileirão Série B",            "pais": "Brazil",                  "equipos_muestra": ["criciuma", "juventude", "sport recife", "athletico paranaense", "america mineiro", "chapecoense", "ituano", "coritiba", "vila nova", "goias"]},
    1281:  {"nombre": "Brasileirão Série C",            "pais": "Brazil",                  "equipos_muestra": ["athletic club", "remo", "tombense", "ferroviaria", "botafogo pb", "abc", "paysandu", "mirassol"]},
    22106: {"nombre": "Première Division de N'Djaména", "pais": "Chad",                    "equipos_muestra": []},
    11653: {"nombre": "Liga de Primera",                "pais": "Chile",                   "equipos_muestra": ["colo colo", "universidad de chile", "universidad catolica", "la serena", "antofagasta", "huachipato", "palestino", "audax italiano"]},
    649:   {"nombre": "Chinese Super League",           "pais": "China",                   "equipos_muestra": ["shandong", "shanghai", "beijing", "guangzhou", "wuhan", "tianjin", "shenzhen", "chengdu"]},
    782:   {"nombre": "Chinese League 1",               "pais": "China",                   "equipos_muestra": ["yanbian", "qingdao", "dalian", "zhejiang", "nanjing", "heilongjiang"]},
    11539: {"nombre": "Primera A, Apertura",            "pais": "Colombia",                "equipos_muestra": ["millonarios", "america", "nacional", "santa fe", "junior", "cali", "medellin", "pereira", "bucaramanga", "pasto"]},
    11536: {"nombre": "Primera A, Finalización",        "pais": "Colombia",                "equipos_muestra": ["millonarios", "america", "nacional", "santa fe", "junior", "cali", "medellin", "pereira", "bucaramanga", "pasto"]},
    1238:  {"nombre": "Categoría Primera B",            "pais": "Colombia",                "equipos_muestra": ["real cartagena", "llaneros", "tigres", "cortuluá", "unión magdalena", "leones"]},
    240:   {"nombre": "LigaPro Serie A",                "pais": "Ecuador",                 "equipos_muestra": ["barcelona sc", "emelec", "liga de quito", "aucas", "independiente", "delfin", "orense", "macara"]},
    808:   {"nombre": "Egyptian Premier League",        "pais": "Egypt",                   "equipos_muestra": ["al ahly", "zamalek", "pyramids", "al masry", "ismaily", "wadi degla"]},
    309:   {"nombre": "World Cup Qual. OFC",            "pais": "Oceania",                 "equipos_muestra": ["new zealand", "tahiti", "solomon islands", "fiji", "vanuatu", "new caledonia"]},
    1222:  {"nombre": "OFC Champions League",           "pais": "Oceania",                 "equipos_muestra": ["auckland city", "hienghene sport", "lautoka", "ba"]},
    704:   {"nombre": "Erovnuli Liga",                  "pais": "Georgia",                 "equipos_muestra": ["dinamo tbilisi", "lokomotivi", "torpedo kutaisi", "saburtalo", "dila gori"]},
    1054:  {"nombre": "CAF Champions League",           "pais": "Africa",                  "equipos_muestra": ["al ahly", "wydad", "mamelodi", "tp mazembe", "esperance", "raja"]},
    463:   {"nombre": "AFC Champions League Elite",     "pais": "Asia",                    "equipos_muestra": ["urawa", "jeonbuk", "al hilal", "al ain", "pohang", "kawasaki"]},
    7:     {"nombre": "UEFA Champions League",          "pais": "Europe",                  "equipos_muestra": ["real madrid", "barcelona", "bayern", "manchester city", "psg", "chelsea", "juventus", "inter", "atletico", "dortmund"]},
    679:   {"nombre": "UEFA Europa League",             "pais": "Europe",                  "equipos_muestra": ["roma", "sevilla", "ajax", "arsenal", "bayer leverkusen", "atalanta", "rangers", "villarreal"]},
    17015: {"nombre": "UEFA Conference League",         "pais": "Europe",                  "equipos_muestra": ["fiorentina", "west ham", "olympiakos", "club brugge", "basel", "gent"]},
    696:   {"nombre": "UEFA Women's Champions League",  "pais": "Europe",                  "equipos_muestra": ["barcelona", "lyon", "chelsea", "wolfsburg", "arsenal", "paris"]},
    140:   {"nombre": "CONCACAF Gold Cup",              "pais": "North & Central America", "equipos_muestra": ["usa", "mexico", "canada", "jamaica", "panama", "costa rica", "honduras"]},
    11454: {"nombre": "Campeones Cup",                  "pais": "North & Central America", "equipos_muestra": ["la galaxy", "leon", "portland", "chivas", "seattle", "club america"]},
    498:   {"nombre": "CONCACAF Champions Cup",         "pais": "North & Central America", "equipos_muestra": ["club america", "tigres", "chivas", "monterrey", "la galaxy", "toronto", "seattle"]},
    13783: {"nombre": "Leagues Cup",                    "pais": "North & Central America", "equipos_muestra": ["la galaxy", "inter miami", "atlas", "tigres", "chivas", "seattle"]},
    384:   {"nombre": "CONMEBOL Libertadores",          "pais": "South America",           "equipos_muestra": ["flamengo", "river", "boca", "palmeiras", "atletico mineiro", "nacional", "olimpia", "independiente"]},
    480:   {"nombre": "CONMEBOL Sudamericana",          "pais": "South America",           "equipos_muestra": ["ldu", "independiente", "fluminense", "defensa y justicia", "peñarol", "america"]},
    133:   {"nombre": "Copa América",                   "pais": "South America",           "equipos_muestra": ["brazil", "argentina", "uruguay", "colombia", "chile", "ecuador", "peru", "venezuela"]},
    10602: {"nombre": "Copa Libertadores Femenina",     "pais": "South America",           "equipos_muestra": ["corinthians", "boca", "nacional", "ferroviaria", "america de cali"]},
    1015:  {"nombre": "Indonesia Super League",         "pais": "Indonesia",               "equipos_muestra": ["persija", "persib", "bali united", "arema", "psm makassar", "madura united"]},
    20708: {"nombre": "UEFA-CONMEBOL Club Challenge",   "pais": "World",                   "equipos_muestra": []},
    16:    {"nombre": "FIFA World Cup",                 "pais": "World",                   "equipos_muestra": ["brazil", "argentina", "france", "germany", "spain", "england"]},
    23674: {"nombre": "FIFA Intercontinental Cup",      "pais": "World",                   "equipos_muestra": []},
    851:   {"nombre": "International Friendly Games",   "pais": "World",                   "equipos_muestra": []},
    290:   {"nombre": "FIFA Women's World Cup",         "pais": "World",                   "equipos_muestra": ["usa", "germany", "france", "japan", "sweden", "england", "australia"]},
    915:   {"nombre": "Persian Gulf Pro League",        "pais": "Iran",                    "equipos_muestra": ["persepolis", "esteghlal", "sepahan", "tractor", "foolad", "zobahan"]},
    206:   {"nombre": "Israeli Premier League",         "pais": "Israel",                  "equipos_muestra": ["maccabi tel aviv", "hapoel", "beitar jerusalem", "bnei yehuda", "maccabi haifa"]},
    196:   {"nombre": "J1 League",                      "pais": "Japan",                   "equipos_muestra": ["kashima", "urawa", "gamba osaka", "yokohama", "vissel kobe", "kawasaki", "cerezo", "nagoya"]},
    402:   {"nombre": "J2 League",                      "pais": "Japan",                   "equipos_muestra": ["vegalta sendai", "kyoto sanga", "tokushima", "renofa yamaguchi", "roasso kumamoto"]},
    682:   {"nombre": "Kazakhstan Premier League",      "pais": "Kazakhstan",              "equipos_muestra": ["shakhtar karagandy", "astana", "kairat", "tobol", "ordabasy"]},
    1002:  {"nombre": "Zain Premier League",            "pais": "Kuwait",                  "equipos_muestra": ["al kuwait", "al qadsia", "al arabi", "al jahra", "kazma"]},
    594:   {"nombre": "New Zealand National League",    "pais": "New Zealand",             "equipos_muestra": ["auckland city", "waitakere", "team wellington", "southern united", "eastern suburbs"]},
    200:   {"nombre": "NIFL Premiership",               "pais": "Northern Ireland",        "equipos_muestra": ["linfield", "glentoran", "cliftonville", "crusaders", "coleraine", "portadown"]},
    11540: {"nombre": "Primera División, Apertura",     "pais": "Paraguay",                "equipos_muestra": ["olimpia", "cerro porteño", "libertad", "guarani", "tacuary", "sol de america"]},
    11541: {"nombre": "Primera División, Clausura",     "pais": "Paraguay",                "equipos_muestra": ["olimpia", "cerro porteño", "libertad", "guarani", "tacuary", "sol de america"]},
    406:   {"nombre": "Liga 1",                         "pais": "Peru",                    "equipos_muestra": ["alianza lima", "universitario", "sporting cristal", "melgar", "cienciano", "san martin"]},
    825:   {"nombre": "Stars League",                   "pais": "Qatar",                   "equipos_muestra": ["al sadd", "al duhail", "al rayyan", "al arabi", "al wakrah", "umm salal"]},
    955:   {"nombre": "Saudi Pro League",               "pais": "Saudi Arabia",            "equipos_muestra": ["al hilal", "al nassr", "al ittihad", "al ahli", "al qadsiah", "al shabab"]},
    36:    {"nombre": "Scottish Premiership",           "pais": "Scotland",                "equipos_muestra": ["celtic", "rangers", "hearts", "hibernian", "aberdeen", "motherwell", "dundee"]},
    358:   {"nombre": "South African Premier Division", "pais": "South Africa",            "equipos_muestra": ["kaizer chiefs", "orlando pirates", "mamelodi sundowns", "cape town city", "supersport united"]},
    52:    {"nombre": "Trendyol Süper Lig",             "pais": "Turkey",                  "equipos_muestra": ["galatasaray", "fenerbahce", "besiktas", "trabzonspor", "basaksehir", "sivasspor", "konyaspor"]},
    971:   {"nombre": "UAE Pro League",                 "pais": "United Arab Emirates",    "equipos_muestra": ["al ain", "al jazira", "al wahda", "al nasr", "sharjah", "dubai"]},
    278:   {"nombre": "Liga AUF Uruguaya",              "pais": "Uruguay",                 "equipos_muestra": ["nacional", "peñarol", "river plate", "defensor sporting", "danubio", "liverpool"]},
    13470: {"nombre": "Canadian Premier League",        "pais": "Canada",                  "equipos_muestra": ["forge", "cavalry", "pacific", "hfx wanderers", "york united", "atletico ottawa"]},
    11621: {"nombre": "Liga MX, Apertura",              "pais": "Mexico",                  "equipos_muestra": ["america", "chivas", "tigres", "monterrey", "cruz azul", "pumas", "toluca", "atlas", "pachuca", "leon"]},
    11620: {"nombre": "Liga MX, Clausura",              "pais": "Mexico",                  "equipos_muestra": ["america", "chivas", "tigres", "monterrey", "cruz azul", "pumas", "toluca", "atlas", "pachuca", "leon"]},
    11611: {"nombre": "Liga de Expansión MX, Apertura", "pais": "Mexico",                  "equipos_muestra": ["atletico morelia", "tapatio", "cancun", "celaya", "tampico madero", "cimarrones"]},
    11612: {"nombre": "Liga de Expansión MX, Clausura", "pais": "Mexico",                  "equipos_muestra": ["atletico morelia", "tapatio", "cancun", "celaya", "tampico madero", "cimarrones"]},
    242:   {"nombre": "MLS",                            "pais": "USA",                     "equipos_muestra": ["la galaxy", "inter miami", "seattle sounders", "portland timbers", "new york", "atlanta united", "chicago fire", "new england", "columbus", "sporting kc"]},
    13363: {"nombre": "USL Championship",               "pais": "USA",                     "equipos_muestra": ["tampa bay", "hartford athletic", "indy eleven", "pittsburgh", "sacramento republic", "orange county"]},
    18641: {"nombre": "MLS Next Pro",                   "pais": "USA",                     "equipos_muestra": ["new york city ii", "la galaxy ii", "portland timbers 2", "seattle sounders 2"]},
    1690:  {"nombre": "NWSL",                           "pais": "USA",                     "equipos_muestra": ["portland thorns", "north carolina", "chicago red stars", "kansas city", "gotham fc", "angel city"]},
    197:   {"nombre": "Virsliga",                       "pais": "Latvia",                  "equipos_muestra": ["riga fc", "riga", "liepaja", "ventspils", "spartaks"]},
    198:   {"nombre": "TOPLYGA",                        "pais": "Lithuania",               "equipos_muestra": ["zalgiris", "suduva", "panevezys", "riteriai", "hegelmann"]},
    211:   {"nombre": "Niké Liga",                      "pais": "Slovakia",                "equipos_muestra": ["slovan bratislava", "spartak trnava", "zilina", "dunajska streda", "trencin"]},
    8:     {"nombre": "LaLiga",                         "pais": "Spain",                   "equipos_muestra": ["real madrid", "barcelona", "atletico", "sevilla", "valencia", "villarreal", "real sociedad", "betis", "athletic", "osasuna"]},
    54:    {"nombre": "LaLiga 2",                       "pais": "Spain",                   "equipos_muestra": ["eibar", "albacete", "huesca", "tenerife", "levante", "zaragoza", "mirandes", "oviedo", "burgos"]},
    20:    {"nombre": "Eliteserien",                    "pais": "Norway",                  "equipos_muestra": ["bodo glimt", "molde", "rosenborg", "viking", "brann", "lillestrom", "ham-kam"]},
    22:    {"nombre": "Norwegian 1st Division",         "pais": "Norway",                  "equipos_muestra": ["fredrikstad", "aalesund", "jerv", "sogndal", "sandnes ulf", "raufoss"]},
    202:   {"nombre": "Ekstraklasa",                    "pais": "Poland",                  "equipos_muestra": ["legia", "lech poznan", "wisla krakow", "rakow", "gornik zabrze", "jagiellonia"]},
    238:   {"nombre": "Liga Portugal Betclic",          "pais": "Portugal",                "equipos_muestra": ["benfica", "porto", "sporting", "braga", "vitoria", "boavista", "famalicao", "estoril"]},
    152:   {"nombre": "SuperLiga României",             "pais": "Romania",                 "equipos_muestra": ["fcsb", "cfr cluj", "rapid", "dinamo", "craiova", "hermannstadt"]},
    40:    {"nombre": "Allsvenskan",                    "pais": "Sweden",                  "equipos_muestra": ["malmo", "djurgarden", "hammarby", "ifk goteborg", "helsingborg", "norrkoping", "aik"]},
    46:    {"nombre": "Superettan",                     "pais": "Sweden",                  "equipos_muestra": ["brage", "degerfors", "brommapojkarna", "vasalunds", "utsikten"]},
    67:    {"nombre": "Ettan, Norra",                   "pais": "Sweden",                  "equipos_muestra": ["ge gefle", "umeå", "friska viljor", "sundsvall", "gif sundsvall"]},
    68:    {"nombre": "Ettan, Södra",                   "pais": "Sweden",                  "equipos_muestra": ["assyriska", "trelleborgs", "landskrona", "halmstads", "ängelholm"]},
    214:   {"nombre": "Damallsvenskan",                 "pais": "Sweden",                  "equipos_muestra": ["rosengard", "linkoping", "goteborg", "djurgarden", "hammarby", "aik"]},
    218:   {"nombre": "Ukrainian Premier League",       "pais": "Ukraine",                 "equipos_muestra": ["shakhtar", "dynamo kyiv", "metalist", "dnipro", "vorskla", "olimpik"]},
    37:    {"nombre": "VriendenLoterij Eredivisie",     "pais": "Netherlands",             "equipos_muestra": ["ajax", "psv", "feyenoord", "az alkmaar", "utrecht", "twente", "vitesse", "groningen"]},
    131:   {"nombre": "Eerste Divisie",                 "pais": "Netherlands",             "equipos_muestra": ["de graafschap", "nac breda", "fc volendam", "almere city", "helmond sport", "dordrecht"]},
    215:   {"nombre": "Swiss Super League",             "pais": "Switzerland",             "equipos_muestra": ["young boys", "basel", "zurich", "servette", "lugano", "st gallen", "sion", "luzern"]},
    185:   {"nombre": "Stoiximan Super League",         "pais": "Greece",                  "equipos_muestra": ["olympiakos", "paok", "panathinaikos", "aek athens", "aris", "asteras tripolis"]},
    38:    {"nombre": "Pro League",                     "pais": "Belgium",                 "equipos_muestra": ["club brugge", "anderlecht", "gent", "standard liege", "antwerp", "genk", "union saint gilloise"]},
    9:     {"nombre": "Challenger Pro League",          "pais": "Belgium",                 "equipos_muestra": ["oh leuven", "rwdm", "dender", "lommel", "beerschot", "lierse"]},
    178:   {"nombre": "Premium Liiga",                  "pais": "Estonia",                 "equipos_muestra": ["flora", "levadia", "paide", "narva trans", "nomme kalju"]},
    678:   {"nombre": "Esiliiga",                       "pais": "Estonia",                 "equipos_muestra": ["tallinn", "parnu", "viljandi", "rakvere", "tartu"]},
    41:    {"nombre": "Veikkausliiga",                  "pais": "Finland",                 "equipos_muestra": ["hjk", "ilves", "kups", "haka", "mariehamn", "inter turku", "seinajoki"]},
    55:    {"nombre": "Ykkösliiga",                     "pais": "Finland",                 "equipos_muestra": ["gnistan", "jazz pori", "klubi 04", "mikkelin palloilijat", "gps turku"]},
    34:    {"nombre": "Ligue 1",                        "pais": "France",                  "equipos_muestra": ["psg", "marseille", "lyon", "monaco", "lille", "rennes", "nice", "strasbourg", "nantes", "lens"]},
    182:   {"nombre": "Ligue 2",                        "pais": "France",                  "equipos_muestra": ["havre", "metz", "caen", "troyes", "amiens", "auxerre", "bordeaux", "laval", "grenoble"]},
    35:    {"nombre": "Bundesliga",                     "pais": "Germany",                 "equipos_muestra": ["bayern", "dortmund", "leverkusen", "leipzig", "frankfurt", "hoffenheim", "wolfsburg", "gladbach", "union berlin"]},
    44:    {"nombre": "2. Bundesliga",                  "pais": "Germany",                 "equipos_muestra": ["hamburger", "schalke", "kaiserslautern", "karlsruhe", "nurnberg", "hannover", "paderborn"]},
    192:   {"nombre": "Premier Division",               "pais": "Ireland",                 "equipos_muestra": ["shamrock rovers", "shelbourne", "bohemian", "dundalk", "derry city", "drogheda"]},
    23:    {"nombre": "Serie A",                        "pais": "Italy",                   "equipos_muestra": ["juventus", "inter", "milan", "roma", "napoli", "lazio", "atalanta", "fiorentina", "torino", "bologna"]},
    53:    {"nombre": "Serie B",                        "pais": "Italy",                   "equipos_muestra": ["parma", "venezia", "palermo", "bari", "catanzaro", "brescia", "reggiana", "modena", "cittadella", "sampdoria"]},
    45:    {"nombre": "Austrian Bundesliga",            "pais": "Austria",                 "equipos_muestra": ["salzburg", "sturm graz", "rapid wien", "austria wien", "wolfsberg", "lask"]},
    247:   {"nombre": "Parva Liga",                     "pais": "Bulgaria",                "equipos_muestra": ["ludogorets", "cska sofia", "levski", "botev plovdiv", "lokomotiv sofia"]},
    1135:  {"nombre": "Vtora Liga",                     "pais": "Bulgaria",                "equipos_muestra": ["hebar", "beroe", "lokomotiv plovdiv", "cherno more", "arda"]},
    205:   {"nombre": "FNL",                            "pais": "Czech Republic",          "equipos_muestra": ["zbrojovka brno", "vlasim", "prostejov", "jihlava", "zlin", "pardubice"]},
    39:    {"nombre": "Danish Superliga",               "pais": "Denmark",                 "equipos_muestra": ["copenhagen", "midtjylland", "brondby", "aab aalborg", "randers", "odense", "silkeborg"]},
    170:   {"nombre": "HNL",                            "pais": "Croatia",                 "equipos_muestra": ["dinamo zagreb", "hajduk split", "rijeka", "osijek", "gorica", "lokomotiva"]},
}

NOMBRES_LIGAS = [info["nombre"] for info in TORNEOS_IDS.values()]

partidos_existentes = set()
partidos_incompletos_por_fecha = {}  # { 'YYYY-MM-DD': [ (liga, local, visita, fila_index), ... ] }
ultima_fecha_registrada = None
ultima_fecha_por_liga = {}  # { 'Nombre Liga': datetime } - progreso independiente por liga
filas_completas_csv = []
headers = []

# =====================================================================
# VALIDACIÓN DE EQUIPOS POR LIGA
# Detecta si Gemini devolvió equipos que no corresponden al país/liga
# solicitada, comparando con palabras clave conocidas de otras ligas
# que podrían confundirse (ej: Serie B Italy vs Brasileirão Série B).
# =====================================================================
def equipo_parece_de_otra_liga(local, visita, liga_id_actual):
    """
    Retorna True si algún equipo parece pertenecer a una liga distinta
    a la solicitada, basándose en los equipos_muestra de otras ligas
    con nombres similares o del mismo país.
    """
    local_l  = local.lower()
    visita_l = visita.lower()
    info_actual = TORNEOS_IDS.get(liga_id_actual, {})
    pais_actual = info_actual.get("pais", "").lower()
    nombre_actual = info_actual.get("nombre", "").lower()

    for tid, info in TORNEOS_IDS.items():
        if tid == liga_id_actual:
            continue
        # Solo revisar ligas de otro país con nombre parecido
        # (las del mismo país son menos peligrosas)
        pais_candidato = info.get("pais", "").lower()
        nombre_candidato = info.get("nombre", "").lower()
        if pais_candidato == pais_actual:
            continue  # Mismo país → no es confusión inter-liga

        # ¿Hay solapamiento de palabras clave en el nombre de la liga?
        palabras_actual    = set(nombre_actual.split())
        palabras_candidato = set(nombre_candidato.split())
        if not palabras_actual & palabras_candidato:
            continue  # Nombres sin palabras en común → no hay riesgo de confusión

        # Revisar si algún equipo recibido aparece en los equipos_muestra del candidato
        muestra = info.get("equipos_muestra", [])
        for kw in muestra:
            kw_l = kw.lower()
            if kw_l in local_l or kw_l in visita_l:
                return True, f"'{local}' o '{visita}' parece de '{info['nombre']}' ({info['pais']}) no de '{info_actual['nombre']}' ({info_actual['pais']})"

    return False, ""

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
                            # Progreso independiente por liga (clave para la rotación)
                            if liga not in ultima_fecha_por_liga or f_obj > ultima_fecha_por_liga[liga]:
                                ultima_fecha_por_liga[liga] = f_obj
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
MAX_LLAMADAS_POR_CORRIDA = 5  # Ajusta este número según la frecuencia de tu cron
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

    if not texto_limpio.startswith("{") and not texto_limpio.startswith("["):
        # El modelo respondió con texto explicativo en lugar de JSON puro
        # (típico cuando dice "no se encontraron partidos..."). Intentamos
        # extraer un objeto JSON embebido; si no hay ninguno, lo tratamos
        # como "sin datos" en vez de error.
        inicio = texto_limpio.find("{")
        fin = texto_limpio.rfind("}")
        if inicio != -1 and fin != -1 and fin > inicio:
            texto_limpio = texto_limpio[inicio:fin + 1]
        else:
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
# FASE B: CONTINUACIÓN DE EXTRACCIÓN AVANZANDO HACIA EL FUTURO (POR LIGA)
# =====================================================================
fecha_hoy_obj = datetime.now()
end_date = fecha_hoy_obj
FECHA_INICIO_DEFAULT = datetime.strptime('2026-01-01', '%Y-%m-%d')

# Cuántos días hacia atrás de la última fecha registrada se vuelven a
# consultar por liga (para capturar partidos que en su momento no tenían
# estadísticas listas aún, o que simplemente no se encontraron).
DIAS_RETROCESO = 2

# Cuántos bloques semanales como máximo se procesan por liga en cada turno.
# Evita que una sola liga con mucho atraso (ej. backlog desde enero) se
# coma todo el cupo de la corrida y deje a las demás ligas del turno sin
# revisar. El resto del atraso se sigue cubriendo en próximos turnos.
MAX_SEMANAS_POR_LIGA = 2

print(f"\n-> Fase de continuación: cada liga avanzará desde {DIAS_RETROCESO} día(s) antes de su último "
      f"partido registrado hasta hoy ({end_date.strftime('%Y-%m-%d')}).", flush=True)

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

# =====================================================================
# ROTACIÓN DE LIGAS
# Tienes ~122 ligas en TORNEOS_IDS pero el cupo diario de Gemini solo
# permite unas pocas llamadas por corrida. En vez de revisar siempre las
# mismas 4 ligas, cada corrida toma el siguiente bloque (circular) y guarda
# un cursor en disco, así con corridas periódicas del cron todas las ligas
# se van cubriendo por turnos.
# =====================================================================
estado_ligas_path = os.path.join("datos", "estado_ligas.json")
cursor_ligas = 0
if os.path.exists(estado_ligas_path):
    try:
        with open(estado_ligas_path, "r", encoding="utf-8") as f:
            cursor_ligas = json.load(f).get("indice_actual", 0)
    except Exception:
        cursor_ligas = 0

todas_las_ligas = list(TORNEOS_IDS.items())
n_ligas = len(todas_las_ligas)
cupo_restante = max(0, MAX_LLAMADAS_POR_CORRIDA - llamadas_realizadas)

LIGAS_ACTUALIZAR = {}
if n_ligas > 0 and cupo_restante > 0:
    cantidad = min(cupo_restante, n_ligas)
    for i in range(cantidad):
        tor_id, info = todas_las_ligas[(cursor_ligas + i) % n_ligas]
        LIGAS_ACTUALIZAR[tor_id] = info

    nuevo_cursor = (cursor_ligas + cantidad) % n_ligas
    try:
        with open(estado_ligas_path, "w", encoding="utf-8") as f:
            json.dump({"indice_actual": nuevo_cursor}, f)
    except Exception as e:
        print(f"   (no se pudo guardar el estado de rotación de ligas: {e})", flush=True)

    print(f"\n-> Este turno cubre {len(LIGAS_ACTUALIZAR)} liga(s) [rotación {cursor_ligas}-{(cursor_ligas + cantidad - 1) % n_ligas} de {n_ligas}]: "
          f"{', '.join(info['nombre'] for info in LIGAS_ACTUALIZAR.values())}", flush=True)
else:
    print("\n-> Sin cupo de llamadas disponible para la fase de descarga; se omite por esta corrida.", flush=True)

cuota_agotada_b = False
for tor_id, info in LIGAS_ACTUALIZAR.items():
    if limite_alcanzado():
        cuota_agotada_b = True
        break

    liga_nombre = info["nombre"]
    pais_nombre = info["pais"]

    ultima_fecha_liga = ultima_fecha_por_liga.get(liga_nombre)
    if ultima_fecha_liga:
        start_date_liga = ultima_fecha_liga - timedelta(days=DIAS_RETROCESO)
        if start_date_liga < FECHA_INICIO_DEFAULT:
            start_date_liga = FECHA_INICIO_DEFAULT
    else:
        start_date_liga = FECHA_INICIO_DEFAULT

    if start_date_liga > end_date:
        print(f"-> {liga_nombre}: ya está al día (último partido registrado: "
              f"{ultima_fecha_liga.strftime('%Y-%m-%d')}).", flush=True)
        continue

    print(f"\n==================================================", flush=True)
    print(f" {liga_nombre} ({pais_nombre}): de {start_date_liga.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}", flush=True)
    print(f"==================================================", flush=True)

    fecha_actual = start_date_liga
    semanas_procesadas = 0
    while fecha_actual <= end_date:
        if semanas_procesadas >= MAX_SEMANAS_POR_LIGA:
            print(f"   ... {liga_nombre} queda con más atraso pendiente; se continuará en un próximo turno.", flush=True)
            break

        fecha_fin_semana = fecha_actual + timedelta(days=6)
        if fecha_fin_semana > end_date:
            fecha_fin_semana = end_date

        str_inicio_sem = fecha_actual.strftime('%Y-%m-%d')
        str_fin_sem    = fecha_fin_semana.strftime('%Y-%m-%d')

        if pais_nombre == "Colombia" and fecha_actual.month == 1 and fecha_actual.day < 15:
            fecha_actual += timedelta(days=7)
            continue

        if limite_alcanzado():
            cuota_agotada_b = True
            break

        print(f"-> Descargando bloque para: {liga_nombre} ({str_inicio_sem} a {str_fin_sem})...", flush=True)
        
        prompt = f"""
Busca en la web todos los partidos oficiales completados entre el {str_inicio_sem} y el {str_fin_sem}
de la liga EXACTA: '{liga_nombre}' del país '{pais_nombre}'.

REGLAS ESTRICTAS:
- NO incluyas partidos de otras ligas aunque tengan un nombre similar (ej: si la liga es 'Serie B' de Italy, NO incluyas partidos de 'Brasileirão Série B' de Brazil, y viceversa).
- NO incluyas partidos de divisiones inferiores, copas ni torneos amistosos a menos que la liga solicitada sea una copa o amistoso.
- Solo partidos del país '{pais_nombre}' para la liga '{liga_nombre}'.
- El campo "tourney_date" es obligatorio (formato YYYY-MM-DD).
- El campo "tourney_season" debe ser el nombre oficial de la temporada (ej: "Premier League 25/26").

Devuelve JSON plano sin bloques markdown con esta estructura:
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

                        # --- VALIDACIÓN: detectar equipos de liga equivocada ---
                        sospechoso, razon = equipo_parece_de_otra_liga(local, visita, tor_id)
                        if sospechoso:
                            print(f"   ! DESCARTADO (posible liga incorrecta): {razon}", flush=True)
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

        semanas_procesadas += 1
        fecha_actual += timedelta(days=7)

    if cuota_agotada_b:
        break

print(f"\nLlamadas a Gemini realizadas en esta corrida: {llamadas_realizadas}/{MAX_LLAMADAS_POR_CORRIDA}", flush=True)
print(f"\n¡Auditoría y actualización completadas de manera exitosa!", flush=True)
