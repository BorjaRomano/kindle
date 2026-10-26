# Panel e-ink para Kindle

Genera cada 30 minutos una imagen de 1072×1448 en escala de grises (Kindle Paperwhite 10) con la hora, el tiempo, la agenda, las tareas y una frase, y la publica en GitHub Pages para que el Kindle la descargue.

- `config.json`: ciudad, coordenadas, eventos y tareas de ejemplo, frases.
- `template.html`: diseño del panel.
- `generate.py`: obtiene el tiempo de [Open-Meteo](https://open-meteo.com), rellena la plantilla y la renderiza con Chrome headless a `site/panel.png`.
- `.github/workflows/panel.yml`: lo ejecuta cada 30 minutos y lo publica en Pages.

## En local

```sh
python -m venv .venv
.venv/Scripts/python -m pip install pillow tzdata
.venv/Scripts/python generate.py
```

## Activar Pages

*Settings → Pages → Source: GitHub Actions*. La imagen queda en `https://<usuario>.github.io/<repo>/panel.png`.
