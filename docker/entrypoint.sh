#!/bin/sh
# AIStack's container entrypoint (ADR-0017 § 2): one image, one command
# per process. Every start first fills the configuration directory with
# the declarations it lacks (never overwriting one).
set -eu

python -m aistack.cli.config_init >/dev/null

command="${1:-web}"
[ "$#" -gt 0 ] && shift

case "$command" in
    web)
        # The console is regenerated at every start, as run_web.sh does.
        python -m aistack.cli.console_render || true
        exec python -m aistack.web.server --generated-dir /app/reports/generated "$@"
        ;;
    events)    exec python -m aistack.cli.docker_events_monitor "$@" ;;
    diff)      exec python -m aistack.cli.docker_diff_monitor "$@" ;;
    digest)    exec python -m aistack.cli.docker_digest_monitor "$@" ;;
    packages)  exec python -m aistack.cli.docker_packages_monitor "$@" ;;
    priority)  exec python -m aistack.cli.resource_priority_monitor "$@" ;;
    vigil)     exec python -m aistack.cli.vigil --every "${AISTACK_VIGIL_SECONDS:-900}" "$@" ;;
    validate)  exec python -m aistack.cli.knowledge_integrity "$@" ;;
    *)         exec "$command" "$@" ;;
esac
