# test_scraper.py - Script minimalista para probar
import json
import time
import random
from curl_cffi import requests
from datetime import datetime

def test_scraper():
    # Probar una fecha con partidos conocidos (por ejemplo, Champions League)
    fecha = "2026-05-15"  # Cambia esta fecha
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.sofascore.com/",
    }
    
    session = requests.Session(impersonate="chrome131")
    session.headers.update(headers)
    
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{fecha}"
    
    print(f"🔍 Consultando: {url}")
    time.sleep(2)
    
    try:
        response = session.get(url, timeout=30)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            eventos = data.get("events", [])
            print(f"📊 Eventos totales: {len(eventos)}")
            
            if eventos:
                # Mostrar primeros 5 eventos
                for e in eventos[:5]:
                    home = e.get("homeTeam", {}).get("name", "?")
                    away = e.get("awayTeam", {}).get("name", "?")
                    status = e.get("status", {}).get("description", "?")
                    tourney = e.get("tournament", {}).get("name", "?")
                    print(f"  ⚽ {home} vs {away} | {status} | {tourney}")
            else:
                print("❌ No hay eventos en esta fecha")
                
        elif response.status_code == 403:
            print("❌ Bloqueado por Cloudflare (403)")
            print("Necesitas rotar más los headers o usar proxies")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_scraper()
