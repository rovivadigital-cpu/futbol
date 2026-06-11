import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def scrape_aiscore():
    url = "https://www.aiscore.com/"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Ejemplo: capturar títulos de partidos destacados
    matches = [m.get_text(strip=True) for m in soup.select("div.match-item")]
    return {"aiscore": matches}

def scrape_footystats():
    url = "https://footystats.org/"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Ejemplo: capturar ligas destacadas
    leagues = [l.get_text(strip=True) for l in soup.select("div.league-name")]
    return {"footystats": leagues}

if __name__ == "__main__":
    data = {}
    data.update(scrape_aiscore())
    data.update(scrape_footystats())
    data["timestamp"] = datetime.utcnow().isoformat()

    with open("resultados.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Scraping completado. Datos guardados en resultados.json")