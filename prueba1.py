import os
import json
from datetime import datetime
from google import genai
from google.genai import types

# 1. Validar la API Key de Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada en GitHub.")

# 2. Inicializar el cliente
client = genai.Client(api_key=api_key)

# 3. Diseñar el prompt para evadir el bloqueo usando la búsqueda de Google
prompt = (
    "Busca en la web, utilizando principalmente páginas como Sofascore o el sitio oficial de la Dimayor, "
    "la lista de todos los equipos de fútbol que participan en la primera división de Colombia (Liga BetPlay Dimayor) en la temporada actual de 2026. "
    "Devuelve la información estrictamente en formato JSON con la siguiente estructura, sin textos adicionales ni bloques de código markdown:\n"
    "{\n"
    "  \"competicion\": \"Liga BetPlay Dimayor\",\n"
    "  \"pais\": \"Colombia\",\n"
    "  \"total_equipos\": 20,\n"
    "  \"equipos\": [\n"
    "    { \"nombre\": \"Nombre del Equipo\", \"ciudad\": \"Ciudad origen\" }\n"
    "  ]\n"
    "}"
)

print("Consultando a Gemini (vía Google Search) para extraer los equipos...")

try:
    # 4. Ejecutar la consulta con Grounding (búsqueda web activa)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1 # Temperatura muy baja para evitar invenciones
        )
    )

    texto_limpio = response.text.strip()
    
    # Limpieza de posibles bloques de código generados por el modelo (```json)
    if texto_limpio.startswith("```json"):
        texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
    elif texto_limpio.startswith("```"):
        texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()

    # 5. Validar que la respuesta sea un JSON correcto y guardarla
    datos_json = json.loads(texto_limpio)
    
    filename = "equipos_liga_betplay.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(datos_json, f, indent=4, ensure_ascii=False)
        
    print(f"¡Éxito! Se generó el archivo '{filename}' con la lista de equipos mapeada por Gemini.")

except Exception as e:
    print(f"Error en el proceso: {e}")
    with open("error_log.txt", "w", encoding="utf-8") as f:
        f.write(f"Error el {datetime.now()}: {str(e)}\nRespuesta cruda del modelo:\n{response.text if 'response' in locals() else 'No response'}")
