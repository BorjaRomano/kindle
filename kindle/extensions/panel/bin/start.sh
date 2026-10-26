#!/bin/sh
PIDFILE=/var/tmp/panel.pid
[ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null && exit 0
nohup sh /mnt/us/extensions/panel/bin/panel.sh >/dev/null 2>&1 &
