#!/usr/bin/env bash
#
# Before moving a git + systemd installation of AIStack onto
# `docker-compose.yml` (ADR-0017 § 5): read what the move depends on,
# change nothing. Run from the checkout, as the account the services
# run as.
#
# Every line says OK, À VOIR (to look at before going on) or INFO.

main() {
    local root
    root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    cd "$root" || exit 1

    ok()   { printf '  OK      %s\n' "$*"; }
    look() { printf '  À VOIR  %s\n' "$*"; }
    info() { printf '  INFO    %s\n' "$*"; }

    echo "AIStack — vérification avant le passage au compose ($root)"

    echo "Compte et Docker"
    info "utilisateur $(id -un) : uid $(id -u), gid $(id -g)"
    if docker compose version >/dev/null 2>&1; then
        ok "$(docker compose version | head -1)"
    else
        look "docker compose ne répond pas"
    fi
    if [ -S /var/run/docker.sock ]; then
        info "groupe du socket Docker : $(stat -c %g /var/run/docker.sock)"
    else
        look "pas de socket /var/run/docker.sock"
    fi
    if docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q nvidia; then
        ok "runtime NVIDIA présent : le bloc GPU de l'override peut rester"
    else
        look "pas de runtime NVIDIA : retire le bloc « deploy » de docker-compose.override.yml"
    fi

    echo "Services systemd"
    local unit
    for unit in aistack-web aistack-docker-events-monitor aistack-docker-diff-monitor \
        aistack-docker-digest-monitor aistack-docker-packages-monitor aistack-resource-priority-monitor; do
        info "$unit : $(systemctl is-active "$unit" 2>/dev/null) / $(systemctl is-enabled "$unit" 2>/dev/null)"
    done

    echo "Ports"
    local port
    for port in 8183 8186; do
        if ss -ltn "sport = :$port" 2>/dev/null | grep -q LISTEN; then
            info "$port écouté (par aistack-web jusqu'à la bascule)"
        else
            info "$port libre"
        fi
    done

    echo "Fichiers"
    if [ -f .env.web ]; then
        if [ "$(stat -c %a .env.web)" = "600" ]; then ok ".env.web présent, droits 600"; else look ".env.web : droits $(stat -c %a .env.web), attendu 600"; fi
    else
        look ".env.web absent : personne ne pourra se connecter"
    fi
    [ -f .env.resource-priority ] && info ".env.resource-priority présent" || info ".env.resource-priority absent"
    [ -e .env ] && look ".env existe déjà : il sera remplacé" || ok ".env absent"
    # config/ is also where the checkout keeps its tracked
    # context_bundle_transfer.yml.example (ADR-0007): only declarations
    # already there matter.
    if ls config/*.yml >/dev/null 2>&1; then
        look "config/ contient déjà des déclarations : vérifie-les avant de copier"
    else
        ok "aucune déclaration dans config/"
    fi
    [ -e docker-compose.override.yml ] && look "docker-compose.override.yml existe déjà" || ok "docker-compose.override.yml absent"
    [ -f data_location.yml ] && look "data_location.yml (choix d'emplacement) présent : annule-le dans Paramètres ou supprime-le" || ok "aucun déplacement de données prévu"
    if [ -d examples/selections ]; then
        info "sélections : $(ls examples/selections | tr '\n' ' ')"
    else
        look "examples/selections absent"
    fi
    if [ -L reports/generated ]; then
        info "reports/generated est un lien vers $(readlink -f reports/generated)"
    elif [ -d reports/generated ]; then
        info "reports/generated : $(du -sh reports/generated 2>/dev/null | cut -f1)"
    else
        look "reports/generated absent"
    fi

    echo "Tâches planifiées qui lancent AIStack sur l'hôte"
    local planned
    planned="$(crontab -l 2>/dev/null | grep -i aistack || true)"
    if [ -n "$planned" ]; then
        look "crontab de $(id -un) :"
        printf '          %s\n' "$planned"
    else
        ok "aucune dans la crontab de $(id -un)"
    fi
    local timers
    timers="$(systemctl list-timers --all --no-legend 2>/dev/null | grep -i aistack || true)"
    [ -n "$timers" ] && look "minuteries systemd : $timers" || ok "aucune minuterie systemd AIStack"
}

main "$@"
