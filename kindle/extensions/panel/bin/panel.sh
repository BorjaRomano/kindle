#!/bin/sh
# Panel e-ink: cada INTERVALO segundos descarga la imagen y la pinta a pantalla
# completa; cada minuto repinta solo la hora en el hueco que deja la imagen.

URL="https://borjaromano.github.io/kindle/panel.png"
INTERVALO=1800
# Hora peninsular española (cambio de hora incluido)
export TZ="CET-1CEST,M3.5.0,M10.5.0/3"

DIR=/mnt/us/extensions/panel
IMG=$DIR/panel.png
LOG=$DIR/panel.log
PIDFILE=/var/tmp/panel.pid
FBINK=/mnt/us/koreader/fbink
FUENTE=/mnt/us/koreader/fonts/noto/NotoSans-Bold.ttf

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

wifi_on() {
    lipc-set-prop com.lab126.cmd wirelessEnable 1
    n=0
    until lipc-get-prop com.lab126.wifid cmState 2>/dev/null | grep -q CONNECTED; do
        n=$((n + 1))
        [ $n -gt 45 ] && { log "sin WiFi"; return 1; }
        sleep 2
    done
}

wifi_off() { lipc-set-prop com.lab126.cmd wirelessEnable 0; }

# Pone en hora el reloj con la cabecera Date de la respuesta HTTP (el Kindle sin
# registrar no sincroniza la hora por su cuenta)
poner_en_hora() {
    fecha=$(curl -skI -m 30 "$URL" | grep -i '^date:' | tr -d '\r')
    [ -n "$fecha" ] || return
    utc=$(echo "$fecha" | awk '{
        split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", m, " ")
        for (i = 1; i <= 12; i++) if (m[i] == $4) mes = i
        printf "%s-%02d-%02d %s", $5, mes, $3, $6 }')
    TZ=UTC date -s "$utc" >/dev/null 2>&1 && log "reloj: $utc UTC"
}

descargar() {
    wifi_on || return 1
    poner_en_hora
    if curl -fsk -m 60 -o "$IMG.tmp" "$URL"; then
        mv "$IMG.tmp" "$IMG"
        log "imagen descargada"
    else
        log "fallo al descargar"
    fi
    wifi_off
}

# El FBInk de KOReader no trae soporte de imágenes; eips (de serie) sí
pintar_imagen() { [ -f "$IMG" ] && eips -f -g "$IMG" >/dev/null 2>&1; }

# Coordenadas del hueco de la hora en la plantilla (1072x1448). El fondo del
# texto puede tapar la raya de la cabecera, así que se vuelve a dibujar.
pintar_hora() {
    "$FBINK" -q -t regular="$FUENTE",px=190,top=0,left=58,right=420,padding=HORIZONTAL "$(date +%H:%M)"
    "$FBINK" -q -k top=233,left=64,width=944,height=5 -B BLACK
}

terminar() {
    lipc-set-prop com.lab126.powerd preventScreenSaver 0
    rm -f "$PIDFILE"
    log "detenido"
    exit 0
}

echo $$ > "$PIDFILE"
trap terminar TERM INT
lipc-set-prop com.lab126.powerd preventScreenSaver 1
log "iniciado"
sleep 3   # deja que se cierre KUAL

ultima=0
while :; do
    ahora=$(date +%s)
    if [ $((ahora - ultima)) -ge $INTERVALO ] || [ ! -f "$IMG" ]; then
        descargar
        ultima=$(date +%s)
        pintar_imagen
    fi
    pintar_hora
    # Espera hasta el siguiente cambio de minuto
    sleep $((60 - $(date +%S | sed 's/^0//')))
done
