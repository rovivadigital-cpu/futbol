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

    # Leemos y filtramos
    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
    
    encabezados = reader[0]
    partidos_futuros = [row for row in reader[1:] if row[0] >= fecha_hoy]
    
    # Reescribimos solo lo necesario
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(encabezados)
        writer.writerows(partidos_futuros)

limpiar_calendario_vencido(csv_filename)

# Lista de torneos oficial (Eliminamos los IDs de Sofascore para evitar bloqueos)
TORNEOS_DATA = [
    {"nombre": "Premier League", "pais": "England"},
    {"nombre": "Championship", "pais": "England"},
    {"nombre": "League One", "pais": "England"},
    {"nombre": "League Two", "pais": "England"},
    {"nombre": "FA Cup", "pais": "England"},
    {"nombre": "Algerian Ligue 1", "pais": "Algeria"},
    {"nombre": "Liga Profesional de Fútbol", "pais": "Argentina"},
    {"nombre": "Primera Nacional", "pais": "Argentina"},
    {"nombre": "Primera B Metropolitana", "pais": "Argentina"},
    {"nombre": "A-League Men", "pais": "Australia"},
    {"nombre": "A-League Women", "pais": "Australia"},
    {"nombre": "NPL Capital Football", "pais": "Australia"},
    {"nombre": "NPL Queensland", "pais": "Australia"},
    {"nombre": "Misli Premier League", "pais": "Azerbaijan"},
    {"nombre": "Bahraini Premier League", "pais": "Bahrain"},
    {"nombre": "Bangladesh Football League", "pais": "Bangladesh"},
    {"nombre": "División Profesional", "pais": "Bolivia"},
    {"nombre": "Brasileirão Betano", "pais": "Brazil"},
    {"nombre": "Brasileirão Série B", "pais": "Brazil"},
    {"nombre": "Brasileirão Série C", "pais": "Brazil"},
    {"nombre": "Première Division de N'Djaména", "pais": "Chad"},
    {"nombre": "Liga de Primera", "pais": "Chile"},
    {"nombre": "Chinese Super League", "pais": "China"},
    {"nombre": "Chinese League 1", "pais": "China"},
    {"nombre": "Primera A, Apertura", "pais": "Colombia"},
    {"nombre": "Primera A, Finalización", "pais": "Colombia"},
    {"nombre": "Categoría Primera B", "pais": "Colombia"},
    {"nombre": "LigaPro Serie A", "pais": "Ecuador"},
    {"nombre": "Egyptian Premier League", "pais": "Egypt"},
    {"nombre": "World Cup Qual. OFC", "pais": "Oceania"},
    {"nombre": "OFC Champions League", "pais": "Oceania"},
    {"nombre": "Erovnuli Liga", "pais": "Georgia"},
    {"nombre": "CAF Champions League", "pais": "Africa"},
    {"nombre": "AFC Champions League Elite", "pais": "Asia"},
    {"nombre": "UEFA Champions League", "pais": "Europe"},
    {"nombre": "UEFA Europa League", "pais": "Europe"},
    {"nombre": "UEFA Conference League", "pais": "Europe"},
    {"nombre": "UEFA Women's Champions League", "pais": "Europe"},
    {"nombre": "CONCACAF Gold Cup", "pais": "North & Central America"},
    {"nombre": "Campeones Cup", "pais": "North & Central America"},
    {"nombre": "CONCACAF Champions Cup", "pais": "North & Central America"},
    {"nombre": "Leagues Cup", "pais": "North & Central America"},
    {"nombre": "CONMEBOL Libertadores", "pais": "South America"},
    {"nombre": "CONMEBOL Sudamericana", "pais": "South America"},
    {"nombre": "Copa América", "pais": "South America"},
    {"nombre": "Copa Libertadores Femenina", "pais": "South America"},
    {"nombre": "Indonesia Super League", "pais": "Indonesia"},
    {"nombre": "UEFA-CONMEBOL Club Challenge", "pais": "World"},
    {"nombre": "FIFA World Cup", "pais": "World"},
    {"nombre": "FIFA Intercontinental Cup", "pais": "World"},
    {"nombre": "International Friendly Games", "pais": "World"},
    {"nombre": "FIFA Women's World Cup", "pais": "World"},
    {"nombre": "Persian Gulf Pro League", "pais": "Iran"},
    {"nombre": "Israeli Premier League", "pais": "Israel"},
    {"nombre": "J1 League", "pais": "Japan"},
    {"nombre": "J2 League", "pais": "Japan"},
    {"nombre": "Kazakhstan Premier League", "pais": "Kazakhstan"},
    {"nombre": "Zain Premier League", "pais": "Kuwait"},
    {"nombre": "New Zealand National League", "pais": "New Zealand"},
    {"nombre": "NIFL Premiership", "pais": "Northern Ireland"},
    {"nombre": "Primera División, Apertura", "pais": "Paraguay"},
    {"nombre": "Primera División, Clausura", "pais": "Paraguay"},
    {"nombre": "Liga 1", "pais": "Peru"},
    {"nombre": "Stars League", "pais": "Qatar"},
    {"nombre": "Saudi Pro League", "pais": "Saudi Arabia"},
    {"nombre": "Scottish Premiership", "pais": "Scotland"},
    {"nombre": "South African Premier Division", "pais": "South Africa"},
    {"nombre": "Trendyol Süper Lig", "pais": "Turkey"},
    {"nombre": "UAE Pro League", "pais": "United Arab Emirates"},
    {"nombre": "Liga AUF Uruguaya", "pais": "Uruguay"},
    {"nombre": "Canadian Premier League", "pais": "Canada"},
    {"nombre": "Liga MX, Apertura", "pais": "Mexico"},
    {"nombre": "Liga MX, Clausura", "pais": "Mexico"},
    {"nombre": "Liga de Expansión MX, Apertura", "pais": "Mexico"},
    {"nombre": "Liga de Expansión MX, Clausura", "pais": "Mexico"},
    {"nombre": "MLS", "pais": "USA"},
    {"nombre": "USL Championship", "pais": "USA"},
    {"nombre": "MLS Next Pro", "pais": "USA"},
    {"nombre": "NWSL", "pais": "USA"},
    {"nombre": "Virsliga", "pais": "Latvia"},
    {"nombre": "TOPLYGA", "pais": "Lithuania"},
    {"nombre": "Niké Liga", "pais": "Slovakia"},
    {"nombre": "LaLiga", "pais": "Spain"},
    {"nombre": "LaLiga 2", "pais": "Spain"},
    {"nombre": "Eliteserien", "pais": "Norway"},
    {"nombre": "Norwegian 1st Division", "pais": "Norway"},
    {"nombre": "Ekstraklasa", "pais": "Poland"},
    {"nombre": "Liga Portugal Betclic", "pais": "Portugal"},
    {"nombre": "SuperLiga României", "pais": "Romania"},
    {"nombre": "Allsvenskan", "pais": "Sweden"},
    {"nombre": "Superettan", "pais": "Sweden"},
    {"nombre": "Ettan, Norra", "pais": "Sweden"},
    {"nombre": "Ettan, Södra", "pais": "Sweden"},
    {"nombre": "Damallsvenskan", "pais": "Sweden"},
    {"nombre": "Ukrainian Premier League", "pais": "Ukraine"},
    {"nombre": "VriendenLoterij Eredivisie", "pais": "Netherlands"},
    {"nombre": "Eerste Divisiee", "pais": "Netherlands"},
    {"nombre": "Swiss Super League", "pais": "Switzerland"},
    {"nombre": "Stoiximan Super League", "pais": "Greece"},
    {"nombre": "Pro League", "pais": "Belgium"},
    {"nombre": "Challenger Pro League", "pais": "Belgium"},
    {"nombre": "Premium Liiga", "pais": "Estonia"},
    {"nombre": "Esiliiga", "pais": "Estonia"},
    {"nombre": "Veikkausliiga", "pais": "Finland"},
    {"nombre": "Ykkösliiga", "pais": "Finland"},
    {"nombre": "Ligue 1", "pais": "France"},
    {"nombre": "Ligue 2", "pais": "France"},
    {"nombre": "Bundesliga", "pais": "Germany"},
    {"nombre": "2. Bundesliga", "pais": "Germany"},  # Corregido el error de dedo previo ("sanity")
    {"nombre": "Premier Division", "pais": "Ireland"},
    {"nombre": "Serie A", "pais": "Italy"},
    {"nombre": "Serie B", "pais": "Italy"},
    {"nombre": "Austrian Bundesliga", "pais": "Austria"},
    {"nombre": "Parva Liga", "pais": "Bulgaria"},
    {"nombre": "Vtora Liga", "pais": "Bulgaria"},
    {"nombre": "FNL", "pais": "Czech Republic"},
    {"nombre": "Danish Superliga", "pais": "Denmark"},
    {"nombre": "HNL", "pais": "Croatia"}
]

# Generar un mapeo seguro indexado por el nombre de la liga en minúsculas
MAPPING_LIGAS = {info["nombre"].lower(): info for info in TORNEOS_DATA}

partidos_existentes = set()

# Función para generar un event_id único y consistente para el partido
def generar_event_id(fecha, local, visita):
    clave = f"{fecha.strip()}_{local.strip().lower()}_{visita.strip().lower()}".encode('utf-8')
    return int(hashlib.md5(clave).hexdigest()[:8], 16) % 100000000

# NUEVA FUNCIÓN: Generar un ID numérico único e independiente para el torneo/liga
def generar_tourney_id(nombre_liga, pais):
    clave = f"{nombre_liga.strip().lower()}_{pais.strip().lower()}".encode('utf-8')
    # Retorna un entero consistente de 5 dígitos para tus llaves foráneas en MariaDB
    return int(hashlib.md5(clave).hexdigest()[:6], 16) % 100000

# Inicializar archivo de calendario con cabeceras estándar
headers = [
    "Fecha", "Hora_Local", "Pais", "Competicion", "Competicion_ID_Sofascore", 
    "Torneo", "Torneo_ID_Sofascore", "Ronda", "Equipo_Local", 
    "Equipo_Local_ID_Sofascore", "Pais_Local", "Equipo_Visitante", 
    "Equipo_Visitante_ID_Sofascore", "Pais_Visitante", "Marcador", "Estado"
]

# =====================================================================
# INICIALIZACIÓN DEL ARCHIVO CSV
# =====================================================================
# Verificamos si el archivo existe antes de abrirlo
archivo_existe = os.path.exists(csv_filename)

# Si el archivo NO existe, lo creamos y escribimos los encabezados
if not archivo_existe:
    with open(csv_filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
    print(f"Archivo creado con encabezados en: {csv_filename}")
else:
    print(f"El archivo ya existe, se añadirán los datos a: {csv_filename}")
# =====================================================================

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
scrape_date_str = fecha_base.strftime('%Y-%m-%d')

print(f"==================================================", flush=True)
print(f" INICIANDO CALENDARIO INDEPENDIENTE (SIN SOFASCORE) ", flush=True)
print(f"==================================================", flush=True)

for fecha_obj, etiqueta in dias_a_revisar:
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    print(f"\n-> Buscando partidos programados para {etiqueta} ({fecha_str})...", flush=True)

    lista_ligas_prompt = ", ".join([info["nombre"] for info in TORNEOS_DATA])

    prompt = f"""
    Busca el calendario de partidos para los próximos 3 días (hoy, mañana y pasado mañana) para las siguientes ligas: [{lista_ligas_prompt}].
    Devuelve un JSON con:
    - liga_nombre_oficial, tourney_season, round, round_number, home_team_name, away_team_name.
    - Opcional: Intenta extraer la hora del partido (formato HH:MM) y el país de los equipos si la información está disponible.
    
    Devuelve estrictamente este JSON:
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

                    llave_partido = f"{fecha_str}_{local}_{visita}".strip().lower()
                    if llave_partido in partidos_existentes:
                        continue

                    partidos_existentes.add(llave_partido)
                    partidos_guardados += 1

                    # Recuperar metadatos locales de nuestro diccionario seguro
                    liga_info = MAPPING_LIGAS[liga_raw]
                    hora = p.get("hora", "00:00")
                    pais_local = p.get("home_team_country", "")
                    pais_visitante = p.get("away_team_country", "")
                    liga_nombre_correcto = liga_info["nombre"]
                    pais_nombre = liga_info["pais"]
                    season = p.get("tourney_season", f"{liga_nombre_correcto} {fecha_str[:4]}")

                    # GENERACIÓN EN CALIENTE DE NUESTROS PROPIOS IDS SEGUROS
                    event_id = generar_event_id(fecha_str, local, visita)
                    custom_tourney_id = generar_tourney_id(liga_nombre_correcto, pais_nombre)

                    row = [
                        fecha_str,                  # Fecha
                        hora,                       # Hora_Local
                        liga_info["pais"],          # Pais
                        liga_nombre_correcto,       # Competicion
                        "",                         # Competicion_ID_Sofascore
                        liga_nombre_correcto,       # Torneo
                        "",                         # Torneo_ID_Sofascore
                        p.get("round", ""),         # Ronda
                        local,                      # Equipo_Local
                        "",                         # Equipo_Local_ID_Sofascore
                        pais_local,                 # Pais_Local
                        visita,                     # Equipo_Visitante
                        "",                         # Equipo_Visitante_ID_Sofascore
                        pais_visitante,             # Pais_Visitante
                        "",                         # Marcador
                        "Programado"                # Estado
                    ]
                    writer.writerow(row)
            print(f"   + Guardados {partidos_guardados} partidos en el archivo temporal.", flush=True)
        else:
            print("   o No hay partidos calendarizados en nuestras ligas para esta fecha.", flush=True)

    except Exception as e:
        print(f"   x Error procesando fecha {fecha_str}: {e}", flush=True)

    time.sleep(6)

print(f"\n Calendario independiente actualizado con éxito en '{csv_filename}'.", flush=True)
