import os
import json
import requests
from datetime import datetime

def obtener_equipos_liga_betplay():
    id_liga = 972
    url = f"https://api.sofascore.com/api/v1/unique-tournament/{id_liga}/seasons"
    
    # Cabeceras completas para simular un navegador real al 100%
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Origin': 'https://www.sofascore.com',
        'Referer': 'https://www.sofascore.com/',
        'Sec-Ch-Ua': '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    }

    print("Conectando con la API de Sofascore usando headers avanzados...")
    
    # Usamos una sesión para mantener las cookies que nos asigne el servidor durante las peticiones
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # 1. Intentamos obtener las temporadas
        res_seasons = session.get(url, timeout=15)
        res_seasons.raise_for_status()
        id_temporada = res_seasons.json()['data']['seasons'][0]['id']
        
        # 2. Consultamos los equipos de la temporada actual
        url_equipos = f"https://api.sofascore.com/api/v1/unique-tournament/{id_liga}/season/{id_temporada}/standings/total"
        res_equipos = session.get(url_equipos, timeout=15)
        res_equipos.raise_for_status()
        
        datos_tabla = res_equipos.json()['data']['standings'][0]['rows']
        
        lista_equipos = []
        for fila in datos_tabla:
            equipo = fila['team']
            lista_equipos.append({
                "id_sofascore": equipo['id'],
                "nombre": equipo['name'],
                "nombre_corto": equipo.get('shortName', ''),
                "codigo": equipo.get('slug', '')
            })
        
        lista_equipos = sorted(lista_equipos, key=lambda k: k['nombre'])
        
        resultado_final = {
            "competicion": "Liga BetPlay Dimayor - Colombia",
            "id_liga_sofascore": id_liga,
            "id_temporada_actual": id_temporada,
            "total_equipos": len(lista_equipos),
            "equipos": lista_equipos
        }
        
        filename = "equipos_liga_betplay.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, indent=4, ensure_ascii=False)
            
        print(f"¡Éxito! Se han descargado {len(lista_equipos)} equipos en '{filename}'.")
        
    except Exception as e:
        print(f"Error al extraer datos de Sofascore: {e}")
        with open("error_log.txt", "w") as f:
            f.write(f"Error en la ejecución: {str(e)}")

if __name__ == "__main__":
    obtener_equipos_liga_betplay()
