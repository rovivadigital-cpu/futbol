import os
import json
from datetime import datetime
from google import genai
from google.genai import types

# 1. Validar la API Key de Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")

# 2. Inicializar el cliente
client = genai.Client(api_key=api_key)

# 3. Diseñar el prompt con contexto temporal (Año actual: 2026)
prompt = (
    "Utilizando la función de búsqueda web en fuentes deportivas confiables (como Sofascore, AS Colombia o Dimayor), "
    "recopila todos los partidos, marcadores y resultados correspondientes a las últimas 6 jornadas disputadas "
    "en el torneo de la Liga BetPlay Dimayor de Colombia en este año 2026.\n\n"
    "Devuelve la información estrictamente en formato JSON sin introducir texto de introducción ni bloques markdown (```json). "
    "Usa exactamente la siguiente estructura:\n"
    "{\n"
    "  \"competicion\": \"Liga BetPlay Dimayor 2026\",\n"
    "  \"jornadas_analizadas\": 6,\n"
    "  \"historial\": [\n"
    "    {\n"
    "      \"numero_jornada\": \"Número o nombre de la jornada (ej: Jornada 15)\",\n"
    "      \"partidos\": [\n"
    "        {\n"
    "          \"equipo_local\": \"Nombre del equipo\",\n"
    "          \"equipo_visitante\": \"Nombre del equipo\",\n"
    "          \"goles_local\": \"Número de goles o null si aplazado\",\n"
    "          \"goles_visitante\": \"Número de goles o null si aplazado\",\n"
    "          \"estado\": \"Finalizado / Aplazado\"\n"
    "        }\n"
    "      ]\n"
    "    }\n"
    "  ]\n"
    "}"
)

print("Consultando a Gemini para compilar el histórico de las últimas 6 jornadas...")

try:
    # 4. Petición a Gemini con Google Search activado
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.15  # Temperatura baja para mantener consistencia de datos
        )
    )

    texto_limpio = response.text.strip()
    
    # Limpieza de envolturas markdown por si acaso
    if texto_limpio.startswith("```json"):
        texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
    elif texto_limpio.startswith("```"):
        texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()

    # 5. Validar formato y escribir archivo
    datos_json = json.loads(texto_limpio)
    
    filename = "ultimas_6_jornadas.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(datos_json, f, indent=4, ensure_ascii=False)
        
    print(f"¡Éxito! Archivo '{filename}' generado correctamente con el histórico de partidos.")

except Exception as e:
    print(f"Error en el proceso de extracción: {e}")
    with open("error_jornadas_log.txt", "w", encoding="utf-8") as f:
        f.write(f"Error el {datetime.now()}: {str(e)}\n")
