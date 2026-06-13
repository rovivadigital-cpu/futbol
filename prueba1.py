import os
import json
from datetime import datetime
from google import genai
from google.genai import types

# 1. Validar la API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")

# 2. Inicializar el cliente de Gemini
client = genai.Client(api_key=api_key)

# 3. Definir qué partidos quieres buscar
# Puedes cambiar este prompt o dinamizarlo según lo que necesites mapear
prompt = (
    "Dame un reporte detallado en formato JSON del último partido de la liga colombiana de fútbol "
    "u otro partido relevante reciente. Incluye: resultado, goleadores, porcentaje de posesión, "
    "remates al arco, faltas y las alineaciones titulares. Devuelve SOLO el objeto JSON estructurado."
)

print("Consultando a Gemini con soporte de búsqueda web...")

# 4. Llamar a la API con Google Search Grounding activado
response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2 # Temperatura baja para que se ciña más a los datos reales encontrados
    )
)

# 5. Guardar la información en un archivo local
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"datos_partido_{timestamp}.json"

# Limpieza rápida por si el modelo envuelve el JSON en bloques de código (```json)
texto_limpio = response.text.strip()
if texto_limpio.startswith("```json"):
    texto_limpio = texto_limpio.split("```json")[1].split("```")[0].strip()
elif texto_limpio.startswith("```"):
    texto_limpio = texto_limpio.split("```")[1].split("```")[0].strip()

try:
    # Validamos que sea un JSON correcto antes de guardar
    datos_json = json.loads(texto_limpio)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(datos_json, f, indent=4, ensure_ascii=False)
    print(f"¡Datos guardados exitosamente en {filename}!")
except Exception as e:
    # Si no devolvió JSON puro, lo guardamos como texto para no perder la info
    filename_txt = f"reporte_partido_{timestamp}.txt"
    with open(filename_txt, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"El formato no era JSON puro. Guardado como texto en {filename_txt}. Error: {e}")
