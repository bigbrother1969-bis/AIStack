#!/usr/bin/env bash
#
# AIStack — the maintenance page, served while Docker is stopped.
#
# The weekly full backup (ReaR) stops Docker: the reverse proxy goes with
# it, and a visitor sees an error. This script puts a page in its place
# — deploy/maintenance/ (an nginx of its own, outside Docker, answering
# 503 and the page on port 80) — and gives the backup a wrapper that does
# the whole dance, whatever happens to the command it runs.
#
#   maintenance_page.sh install [--tls CERT KEY]   install the page, the nginx
#                                                  configuration and the unit
#   maintenance_page.sh uninstall                  remove them again
#   maintenance_page.sh on | off | status          show / hide / look at the page
#   maintenance_page.sh run -- COMMAND [ARGS...]   stop Docker, show the page,
#                                                  run COMMAND, then hide the
#                                                  page and start Docker — even
#                                                  if COMMAND fails
#
# Options: --dry-run (say what would be done, change nothing), --yes
# (do not ask before `install`/`uninstall`).
#
# Run as root. Every file it replaces is first copied beside itself as
# <file>.avant-<date>-<time>; `uninstall` removes only what `install`
# created and puts nothing back unasked.
#
# `install` never enables the unit: the page is shown on demand only,
# because the reverse proxy and the page both want port 80.
#
# Behind a tunnel whose origin is https://…:443 (not http://…:80), give
# the certificate and key the reverse proxy uses: --tls CERT KEY.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKOUT="$(cd "$HERE/.." && pwd)"
# A prefix for every path written, so the tests can run without root.
PREFIX="${AISTACK_MAINTENANCE_ROOT:-}"
PAGE_DIR="$PREFIX/usr/share/aistack-maintenance"
CONF_DIR="$PREFIX/etc/aistack-maintenance"
UNIT="$PREFIX/etc/systemd/system/aistack-maintenance.service"
WAIT_PORT_SECONDS="${AISTACK_MAINTENANCE_WAIT:-120}"
# systemd reports the unit started before nginx listens: how long `on` waits for the 503.
WAIT_PAGE_SECONDS="${AISTACK_MAINTENANCE_PAGE_WAIT:-15}"
DOCKER_BIN="${AISTACK_DOCKER:-docker}"
STAMP="$(date +%Y%m%d-%H%M%S)"

DRY_RUN=0
ASSUME_YES=0
TLS_CERT=""
TLS_KEY=""

say() { printf '%s\n' "$*"; }
fail() { printf '%s\n' "$*" >&2; exit 1; }

usage() { sed -n '3,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

need_root() {
    [ "$DRY_RUN" -eq 1 ] && return 0
    [ -n "$PREFIX" ] || [ "$(id -u)" -eq 0 ] || fail "Lance-moi avec sudo."
}

# do_it "what it does" command args... : says it, runs it unless --dry-run.
do_it() {
    local what="$1"; shift
    if [ "$DRY_RUN" -eq 1 ]; then
        say "  [simulation] $what"
    else
        say "  $what"
        "$@"
    fi
}

confirm() {
    [ "$ASSUME_YES" -eq 1 ] || [ "$DRY_RUN" -eq 1 ] && return 0
    local answer
    read -r -p "$1 [o/N] " answer </dev/tty || return 1
    [ "$answer" = o ] || [ "$answer" = O ]
}

# Copies $1 beside itself as $1.avant-<stamp>, when it exists.
keep_copy() {
    [ -e "$1" ] || return 0
    do_it "copie de $1 → $1.avant-$STAMP" cp -a "$1" "$1.avant-$STAMP"
}

port_busy() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq '[:.]80$'; }

# Installs the nginx package without letting it start: the package starts
# its own nginx when it is configured, and with the reverse proxy on port
# 80 that start fails — which leaves dpkg with a half-configured package.
# A policy-rc.d that refuses every start (exit 101) is in place for the
# duration, and only if there was none.
install_nginx() {
    local policy="$PREFIX/usr/sbin/policy-rc.d"
    if [ "$DRY_RUN" -eq 1 ]; then
        say "  [simulation] apt-get install nginx (démarrage du service interdit pendant l'installation)"
        return 0
    fi
    local made=0
    if [ ! -e "$policy" ]; then
        install -d "$(dirname "$policy")"
        printf '#!/bin/sh\nexit 101\n' > "$policy"
        chmod 755 "$policy"
        made=1
    fi
    local rc=0
    say "  apt-get install nginx (démarrage du service interdit pendant l'installation)"
    apt-get install -y nginx || rc=$?
    [ "$made" -eq 0 ] || rm -f "$policy"
    [ "$rc" -eq 0 ] || fail "apt-get install nginx a échoué (code $rc)."
}

cmd_install() {
    need_root
    say "== Installation de la page de maintenance"
    [ -f "$CHECKOUT/deploy/maintenance/maintenance.html" ] || fail "Fichiers introuvables sous $CHECKOUT/deploy/maintenance."

    if ! command -v nginx >/dev/null 2>&1; then
        say "  nginx n'est pas installé."
        confirm "Installer le paquet nginx (apt) ?" || fail "Abandon."
        install_nginx
        # The package starts and enables its own nginx: not wanted, the
        # reverse proxy has port 80 and this nginx is ours.
        do_it "arrêt et désactivation du service nginx du paquet" systemctl disable --now nginx
    fi

    keep_copy "$PAGE_DIR/maintenance.html"
    do_it "page → $PAGE_DIR/maintenance.html" bash -c \
        "install -d -m 755 '$PAGE_DIR' && install -m 644 '$CHECKOUT/deploy/maintenance/maintenance.html' '$PAGE_DIR/maintenance.html'"

    keep_copy "$CONF_DIR/nginx.conf"
    write_conf
    keep_copy "$UNIT"
    do_it "unité → $UNIT" bash -c \
        "install -d -m 755 '$(dirname "$UNIT")' && install -m 644 '$CHECKOUT/deploy/systemd/aistack-maintenance.service' '$UNIT'"
    do_it "systemctl daemon-reload" systemctl daemon-reload

    if [ "$DRY_RUN" -eq 0 ] && [ -z "$PREFIX" ]; then
        nginx -t -c "$CONF_DIR/nginx.conf" || fail "La configuration nginx est refusée : rien n'est démarré."
    fi
    say
    say "Installée, non démarrée. Essai : sudo $0 on, puis sudo $0 off"
    say "(le port 80 doit être libre : l'essai n'a de sens que Docker arrêté, ou hors du proxy)."
}

write_conf() {
    local src="$CHECKOUT/deploy/maintenance/nginx.conf"
    # nginx refuses to start on a host without IPv6 when the file listens
    # on [::]: those lines go when the kernel has none.
    local v6='cat'
    [ -e "${AISTACK_MAINTENANCE_IF_INET6:-/proc/net/if_inet6}" ] || v6="grep -v '\\[::\\]'"
    if [ -n "$TLS_CERT" ]; then
        [ -r "$TLS_CERT" ] && [ -r "$TLS_KEY" ] || [ "$DRY_RUN" -eq 1 ] || fail "Certificat ou clé illisible."
        do_it "configuration nginx (avec TLS, port 443) → $CONF_DIR/nginx.conf" bash -c \
            "install -d -m 755 '$CONF_DIR' && sed -e 's|^#TLS#||' -e 's|@TLS_CERT@|$TLS_CERT|' -e 's|@TLS_KEY@|$TLS_KEY|' '$src' | $v6 > '$CONF_DIR/nginx.conf'"
    else
        do_it "configuration nginx (port 80) → $CONF_DIR/nginx.conf" bash -c \
            "install -d -m 755 '$CONF_DIR' && grep -v '^#TLS#' '$src' | $v6 > '$CONF_DIR/nginx.conf'"
    fi
}

cmd_uninstall() {
    need_root
    say "== Retrait de la page de maintenance"
    confirm "Retirer la page, la configuration et l'unité ?" || fail "Abandon."
    do_it "arrêt de l'unité" systemctl stop aistack-maintenance.service
    do_it "retrait de $UNIT" rm -f "$UNIT"
    do_it "retrait de $CONF_DIR" rm -rf "$CONF_DIR"
    do_it "retrait de $PAGE_DIR" rm -rf "$PAGE_DIR"
    do_it "systemctl daemon-reload" systemctl daemon-reload
    say "Retiré. Les copies .avant-* éventuelles ne sont pas touchées."
}

cmd_on() {
    need_root
    local waited=0
    while [ "$DRY_RUN" -eq 0 ] && port_busy; do
        [ "$waited" -lt "$WAIT_PORT_SECONDS" ] || fail "Le port 80 est toujours pris après ${WAIT_PORT_SECONDS} s : la page n'est pas affichée (Docker est-il arrêté ?)."
        [ "$waited" -gt 0 ] || say "  Le port 80 est pris, j'attends qu'il soit libre…"
        sleep 2; waited=$((waited + 2))
    done
    do_it "systemctl start aistack-maintenance" systemctl start aistack-maintenance.service
    [ "$DRY_RUN" -eq 1 ] && return 0
    # `Type=simple`: systemd says "started" before nginx has opened the port,
    # so the first answer can be nothing at all. Ask again until the page
    # answers, for up to WAIT_PAGE_SECONDS.
    local code page_waited=0
    while :; do
        code="$(curl -s -m 3 -o /dev/null -w '%{http_code}' http://127.0.0.1/ || true)"
        [ "$code" = 503 ] && break
        [ "$page_waited" -lt "$WAIT_PAGE_SECONDS" ] || break
        sleep 1
        page_waited=$((page_waited + 1))
    done
    [ "$code" = 503 ] || fail "La page ne répond pas 503 (reçu : ${code:-rien}) : journalctl -u aistack-maintenance -n 40"
    say "  La page de maintenance répond (503)."
}

cmd_off() {
    need_root
    do_it "systemctl stop aistack-maintenance" systemctl stop aistack-maintenance.service
}

cmd_status() {
    if systemctl is-active --quiet aistack-maintenance.service; then
        say "La page de maintenance est affichée."
    else
        say "La page de maintenance n'est pas affichée."
    fi
    if [ -f "$PAGE_DIR/maintenance.html" ]; then
        say "Installée : $PAGE_DIR"
    else
        say "Pas installée (sudo $0 install)."
    fi
}

# The containers running before Docker is stopped. A restart policy does
# not bring back every one of them (a container killed while the daemon
# stops, `on-failure`, `no`): after Docker is back, those that were
# running and are not any more are started again.
RUNNING_BEFORE=""
note_running_containers() {
    command -v "$DOCKER_BIN" >/dev/null 2>&1 || return 0
    RUNNING_BEFORE="$("$DOCKER_BIN" ps -q --no-trunc 2>/dev/null || true)"
}

restart_stopped_containers() {
    [ -n "$RUNNING_BEFORE" ] || return 0
    local waited=0 id name
    until "$DOCKER_BIN" info >/dev/null 2>&1; do
        waited=$((waited + 1))
        if [ "$waited" -gt "$WAIT_PORT_SECONDS" ]; then
            say "ATTENTION : Docker ne répond pas, les conteneurs d'avant ne sont pas relancés."
            return 0
        fi
        sleep 1
    done
    # Let the restart policies act first.
    sleep 30
    for id in $RUNNING_BEFORE; do
        if [ "$("$DOCKER_BIN" inspect -f '{{.State.Running}}' "$id" 2>/dev/null || echo true)" != true ]; then
            name="$("$DOCKER_BIN" inspect -f '{{.Name}}' "$id" 2>/dev/null || echo "$id")"
            say "  Relance de ${name#/} (tournait avant l'arrêt de Docker)"
            "$DOCKER_BIN" start "$id" >/dev/null 2>&1 || say "ATTENTION : ${name#/} ne démarre pas."
        fi
    done
}

cmd_run() {
    need_root
    [ $# -gt 0 ] || fail "Usage : $0 run -- COMMANDE [ARGUMENTS...]"
    if [ "$DRY_RUN" -eq 0 ]; then
        [ -f "$PAGE_DIR/maintenance.html" ] && [ -f "$UNIT" ] || fail "La page n'est pas installée : sudo $0 install"
    fi
    say "== $* , avec la page de maintenance"
    if [ "$DRY_RUN" -eq 1 ]; then
        say "  [simulation] arrêt de Docker (docker.service et docker.socket)"
        say "  [simulation] page de maintenance affichée"
        say "  [simulation] $*"
        say "  [simulation] page retirée, Docker redémarré, conteneurs d'avant relancés (même si la commande échoue)"
        return 0
    fi
    # Whatever happens from here on, the page comes down and Docker comes
    # back: the trap is set before anything is stopped.
    note_running_containers
    trap 'cmd_off || true; systemctl start docker.service || say "ATTENTION : Docker ne redémarre pas, à relancer à la main."; restart_stopped_containers || true' EXIT
    systemctl stop docker.service docker.socket
    cmd_on
    local rc=0
    "$@" || rc=$?
    say "== La commande a rendu le code $rc ; retour à la normale."
    exit "$rc"
}

# --- arguments --------------------------------------------------------
[ $# -gt 0 ] || { usage; exit 2; }
ACTION=""
RUN_ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        install|uninstall|on|off|status|run) ACTION="$1"; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        --yes) ASSUME_YES=1; shift ;;
        --tls) [ $# -ge 3 ] || fail "--tls demande CERT et KEY."; TLS_CERT="$2"; TLS_KEY="$3"; shift 3 ;;
        --) shift; RUN_ARGS=("$@"); break ;;
        -h|--help) usage; exit 0 ;;
        *) fail "Option inconnue : $1" ;;
    esac
done
[ -n "$ACTION" ] || { usage >&2; exit 2; }

case "$ACTION" in
    install) cmd_install ;;
    uninstall) cmd_uninstall ;;
    on) cmd_on ;;
    off) cmd_off ;;
    status) cmd_status ;;
    run) cmd_run "${RUN_ARGS[@]}" ;;
esac
