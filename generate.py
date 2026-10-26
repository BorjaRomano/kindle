"""Genera el panel e-ink (site/panel.png) para el Kindle Paperwhite.

Rellena template.html con el tiempo (Open-Meteo) y los datos de config.json,
lo renderiza con Chrome/Edge en modo headless y lo convierte a PNG en grises.
"""
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from string import Template
from zoneinfo import ZoneInfo

from PIL import Image

RAIZ = Path(__file__).parent
SALIDA = RAIZ / "site"
ANCHO, ALTO = 1072, 1448

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Códigos WMO de Open-Meteo -> (icono, descripción)
TIEMPO = {
    0: ("sol", "Despejado"), 1: ("solnube", "Mayormente despejado"),
    2: ("solnube", "Parcialmente nublado"), 3: ("nube", "Nublado"),
    45: ("niebla", "Niebla"), 48: ("niebla", "Niebla"),
    51: ("lluvia", "Llovizna"), 53: ("lluvia", "Llovizna"), 55: ("lluvia", "Llovizna"),
    56: ("lluvia", "Llovizna helada"), 57: ("lluvia", "Llovizna helada"),
    61: ("lluvia", "Lluvia débil"), 63: ("lluvia", "Lluvia"), 65: ("lluvia", "Lluvia fuerte"),
    66: ("lluvia", "Lluvia helada"), 67: ("lluvia", "Lluvia helada"),
    71: ("nieve", "Nieve débil"), 73: ("nieve", "Nieve"), 75: ("nieve", "Nieve fuerte"),
    77: ("nieve", "Granizo fino"), 80: ("lluvia", "Chubascos"), 81: ("lluvia", "Chubascos"),
    82: ("lluvia", "Chubascos fuertes"), 85: ("nieve", "Chubascos de nieve"),
    86: ("nieve", "Chubascos de nieve"), 95: ("tormenta", "Tormenta"),
    96: ("tormenta", "Tormenta con granizo"), 99: ("tormenta", "Tormenta con granizo"),
}


def obtener_tiempo(cfg):
    params = {
        "latitude": cfg["latitud"], "longitude": cfg["longitud"], "timezone": cfg["zona_horaria"],
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 5,
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def bloque_prevision(diario):
    partes = []
    for i in range(1, 5):
        fecha = datetime.fromisoformat(diario["time"][i])
        icono, _ = TIEMPO.get(diario["weather_code"][i], ("nube", ""))
        partes.append(
            f'<div><span class="d">{DIAS[fecha.weekday()][:3]}</span>'
            f'<svg viewBox="0 0 100 100"><use href="#{icono}"/></svg>'
            f'<span class="t">{round(diario["temperature_2m_max"][i])}° / '
            f'{round(diario["temperature_2m_min"][i])}°</span></div>')
    return "".join(partes)


def bloque_eventos(eventos, ahora):
    hhmm = ahora.strftime("%H:%M")
    # El primer evento que aún no ha pasado se resalta
    siguiente = next((i for i, e in enumerate(eventos) if e["hora"] >= hhmm), None)
    partes = []
    for i, e in enumerate(eventos):
        clase = "evento ahora" if i == siguiente else ("evento pasado" if e["hora"] < hhmm else "evento")
        partes.append(
            f'<div class="{clase}"><span class="h">{html.escape(e["hora"])}</span>'
            f'<span>{html.escape(e["titulo"])}<span class="l">{html.escape(e["lugar"]) or "—"}</span></span></div>')
    return "".join(partes)


def bloque_tareas(tareas):
    return "".join(
        f'<div class="tarea{" hecha" if t["hecha"] else ""}"><span class="caja"></span>{html.escape(t["texto"])}</div>'
        for t in tareas)


def buscar_navegador():
    candidatos = [os.environ.get("CHROME"), shutil.which("google-chrome"), shutil.which("chromium"),
                  shutil.which("chromium-browser"),
                  r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    sys.exit("No se encontró Chrome/Edge (define la variable CHROME)")


def renderizar(html_path, png_path):
    with tempfile.TemporaryDirectory() as perfil:
        subprocess.run([
            buscar_navegador(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
            f"--user-data-dir={perfil}", "--force-device-scale-factor=1",
            f"--window-size={ANCHO},{ALTO}", f"--screenshot={png_path}", html_path.as_uri(),
        ], check=True, capture_output=True, timeout=60)
    # El Kindle dibuja PNG de 8 bits en grises; la pantalla tiene 16 niveles
    img = Image.open(png_path).convert("L").crop((0, 0, ANCHO, ALTO))
    img = img.point(lambda v: round(v / 17) * 17)
    img.save(png_path, optimize=True)


def main():
    cfg = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
    ahora = datetime.now(ZoneInfo(cfg["zona_horaria"]))
    t = obtener_tiempo(cfg)
    actual, diario = t["current"], t["daily"]
    icono, descripcion = TIEMPO.get(actual["weather_code"], ("nube", "—"))
    frase, autor = cfg["frases"][ahora.timetuple().tm_yday % len(cfg["frases"])]

    datos = {
        "hora": ahora.strftime("%H:%M"),
        "dia": DIAS[ahora.weekday()],
        "fecha": f"{ahora.day} de {MESES[ahora.month - 1]}",
        "icono": icono, "descripcion": descripcion, "ciudad": html.escape(cfg["ciudad"]),
        "temp": round(actual["temperature_2m"]),
        "max": round(diario["temperature_2m_max"][0]), "min": round(diario["temperature_2m_min"][0]),
        "lluvia": diario["precipitation_probability_max"][0] or 0,
        "viento": round(actual["wind_speed_10m"]), "humedad": actual["relative_humidity_2m"],
        "prevision": bloque_prevision(diario),
        "eventos": bloque_eventos(cfg["eventos_ejemplo"], ahora),
        "tareas": bloque_tareas(cfg["tareas_ejemplo"]),
        "frase": html.escape(frase), "autor": html.escape(autor),
        "aviso": "Calendario y tareas de ejemplo",
    }

    SALIDA.mkdir(exist_ok=True)
    plantilla = Template((RAIZ / "template.html").read_text(encoding="utf-8"))
    # panel.png deja el hueco de la hora vacío: la pinta el propio Kindle cada minuto.
    # preview.png la incluye, para la vista previa web.
    for nombre, visible in (("panel", "hidden"), ("preview", "visible")):
        pagina = SALIDA / f"{nombre}.html"
        pagina.write_text(plantilla.substitute(datos, hora_visible=visible), encoding="utf-8")
        renderizar(pagina.resolve(), SALIDA / f"{nombre}.png")
    (SALIDA / "index.html").write_text(
        (RAIZ / "index.html").read_text(encoding="utf-8").replace("$hora", datos["hora"]), encoding="utf-8")
    print(f"Panel generado: {SALIDA / 'panel.png'} ({datos['hora']}, {datos['temp']}° {descripcion})")


if __name__ == "__main__":
    main()
