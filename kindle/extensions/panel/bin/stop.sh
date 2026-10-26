#!/bin/sh
PIDFILE=/var/tmp/panel.pid
[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null
rm -f "$PIDFILE"
lipc-set-prop com.lab126.powerd preventScreenSaver 0
# Vuelve a la pantalla de inicio para que el Kindle se redibuje
lipc-set-prop com.lab126.appmgrd start app://com.lab126.booklet.home
