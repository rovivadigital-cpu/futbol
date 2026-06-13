import os
import json
import requests
from datetime import datetime

def obtener_equipos_liga_betplay():
    # ID oficial de la Liga BetPlay (Primera A de Colombia) en Sofascore
    id_liga = 972
    
    # URL de la API interna de Sofascore para ver los equipos del torneo actual
    url = f"https://api.sofascore.com/api/v1/unique-tournament/{id_liga}/seasons"
    
    # Encabezados obligatorios para evitar que Sofascore bloquee la petición (403 Forbidden)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Origin': 'https://www.sofascore.com',
        'Referer': 'https://www.sofascore.com/'
    }

    print("Conectando con la API de Sofascore...")
    
    try:
        # 1. Primero obtenemos el ID de la temporada más reciente (actual)
        res_seasons = requests.get(url, headers=headers)
        res_seasons.raise_for_status()
        id_temporada = res_seasons.json()['data']['seasons'][0]['id']
        
        # 2. Con el ID de la temporada, consultamos los equipos y sus posiciones/datos
        url_equipos = f"https://api.sofascore.com/api/v1/unique-tournament/{id_liga}/season/{id_temporada}/standings/total"
        res_equipos = requests.get(url_equipos, headers=headers)
        res_equipos.raise_for_status()
        
        datos_tabla = res_equipos.json()['data']['standings'][0]['rows']
        
        # 3. Procesamos y limpiamos la lista de equipos
        lista_equipos = []
        for fila in datos_tabla:
            equipo = fila['team']
            lista_equipos.append({
                "id_sofascore": equipo['id'],
                "nombre": equipo['name'],
                "nombre_corto": equipo.get('shortName', ''),
                "codigo": equipo.get('slug', '')
            })
        
        # Ordenamos alfabéticamente por nombre de equipo
        lista_equipos = sorted(lista_equipos, key=lambda k: k['nombre'])
        
        # Estructura final del JSON
        resultado_final = {
            "competicion": "Liga BetPlay Dimayor - Colombia",
            "id_liga_sofascore": id_liga,
            "id_temporada_actual": id_temporada,
            "total_equipos": len(lista_equipos),
            "equipos": lista_equipos
        }
        
        # 4. Guardar en un archivo JSON fijo para que sea tu diccionario de referencia
        filename = "equipos_liga_betplay.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, indent=4, ensure_ascii=False)
            
        print(f"¡Éxito! Se han descargado {len(lista_equipos)} equipos en '{filename}'.")
        
    except Exception as e:
        print(f"Error al extraer datos de Sofascore: {e}")
        # Si falla por bloqueo, dejamos constancia del error
        with open("error_log.txt", "w") as f:
            f.write(f"Error en la ejecución de la fecha {datetime.now()}: {str(e)}")

if __name__ == "__main__":
    obtener_equipos_liga_betplay()
