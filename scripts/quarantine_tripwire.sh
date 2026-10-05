# OPS-0012 — the tripwire of a quarantined shell script. Sourced, never
# run: `quarantine_tripwire <path of the script, from the repository root>`
# appends one line to the quarantine's hits file and prints a warning on
# stderr. It never stops the script: finding out who still runs it is
# the point of the quarantine.
#
# The hits file lives with AIStack's data: AISTACK_DATA_DIR when `.env`
# names it (docker compose, ADR-0017), else reports/generated.

quarantine_tripwire() {
    local script="$1"
    local root data hits value parent
    root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    data="$root/reports/generated"
    if [ -f "$root/.env" ]; then
        value="$(sed -n 's/^AISTACK_DATA_DIR=//p' "$root/.env" | tail -1)"
        if [ -n "$value" ]; then
            case "$value" in
                /*) data="$value" ;;
                *) data="$root/${value#./}" ;;
            esac
        fi
    fi
    hits="$data/quarantine/hits.jsonl"
    echo "AVERTISSEMENT : $script est en quarantaine (OPS-0012) et vient d'être lancé — il n'est pas inutilisé : retire-le de src/aistack/quarantine/register.yml" >&2
    {
        mkdir -p "$data/quarantine" &&
        # Who launched it — a crontab shows up here as cron's command.
        parent="$(ps -o args= -p "${PPID:-0}" 2>/dev/null | tr -d '"\\' | cut -c1-200)"
        printf '{"at": "%s", "kind": "script", "target": "%s", "caller": "%s", "program": "%s", "pid": %s}\n' \
            "$(date -Iseconds)" "$script" "$(id -un)@$(hostname)" "$parent" "$$" >> "$hits"
    } 2>/dev/null || true
}
