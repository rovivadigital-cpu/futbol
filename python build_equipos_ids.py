"""
build_equipos_ids.py
--------------------
Extrae todos los nombres e IDs de equipos del CSV histórico
(partidos_futbol.csv) y genera datos/equipos_ids.csv como tabla
de lookup para el calendario.

Ejecutar:
  python build_equipos_ids.py

O agregar como paso previo en el workflow de GitHub Actions
antes de correr el calendario.
"""

import os
import csv

HISTORICO   = os.path.join("datos", "partidos_futbol.csv")
SALIDA      = os.path.join("datos", "equipos_ids.csv")

# Columnas del CSV histórico donde viven los nombres e IDs
COLUMNAS = [
    ("Equipo_Local",     "Equipo_Local_ID_Sofascore"),
    ("Equipo_Visitante", "Equipo_Visitante_ID_Sofascore"),
]

def build_equipos_ids():
    if not os.path.exists(HISTORICO):
        print(f"[!] No se encontró {HISTORICO}. Asegúrate de que el scraper histórico haya corrido al menos una vez.")
        return

    equipos = {}  # nombre_lower → {"nombre_equipo": ..., "id_sofascore": ...}

    with open(HISTORICO, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col_nombre, col_id in COLUMNAS:
                nombre = row.get(col_nombre, "").strip()
                eid    = row.get(col_id, "").strip()
                if nombre and eid:
                    key = nombre.lower()
                    if key not in equipos:
                        equipos[key] = {"nombre_equipo": nombre, "id_sofascore": eid}

    os.makedirs("datos", exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nombre_equipo", "id_sofascore"])
        writer.writeheader()
        writer.writerows(sorted(equipos.values(), key=lambda x: x["nombre_equipo"].lower()))

    print(f"[OK] {len(equipos)} equipos exportados a {SALIDA}")

if __name__ == "__main__":
    build_equipos_ids()
