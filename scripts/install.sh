#!/usr/bin/env bash
# AIStack — installation on a new host (ADR-0023 § 4).
#
#   curl -fsSLO https://raw.githubusercontent.com/bigbrother1969-bis/AIStack/main/scripts/install.sh
#   bash install.sh                 # asks before each change
#   bash install.sh --dry-run       # says what it would do, changes nothing
#
# Lays the base on the host, then hands over to the browser: the page
# /setup guides the rest (the host, the public address, signing in,
# storage, API keys). Run as a user who can use sudo, not as root.
#
#   1. the system: Debian, Ubuntu, Linux Mint, LMDE (the apt family);
#   2. Docker Engine and the Compose plugin, from Docker's repository,
#      when missing — and this user in the docker group;
#   3. the AIStack directory: docker-compose.yml, .env, config/, data/,
#      .env.web (0600);
#   4. on request: Pocket ID, Gotify, Syncthing (each its own Compose
#      project in /srv/<name>), Ollama and its model;
#   5. AIStack started, and the address of /setup.
#
# Never prints a secret: generated ones go to a file readable by this
# user only, and the script says which. A second run changes only what
# is still missing.

set -euo pipefail

VERSION="${AISTACK_VERSION:-1.11.0}"
REPOSITORY="${AISTACK_REPOSITORY:-https://raw.githubusercontent.com/bigbrother1969-bis/AIStack}"
DIR="/srv/aistack"
PREREQ_ROOT="/srv"
OS_RELEASE="${AISTACK_OS_RELEASE:-/etc/os-release}"
MODEL="qwen2.5:3b"
REF=""
DRY_RUN=0
ASSUME_YES=0
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKOUT="$(cd "$HERE/.." && pwd)"

usage() {
    cat <<EOF
Usage: bash install.sh [--dir DIR] [--version VERSION] [--ref REF] [--dry-run] [--yes]

  --dir DIR          where AIStack goes (default: $DIR)
  --version VERSION  the AIStack version to run (default: $VERSION)
  --ref REF          the repository's tag or branch the files come from
                     (default: v<VERSION>; a release candidate: its tag)
  --dry-run          say what would be done, change nothing
  --yes              answer yes to every question (unattended)
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dir) DIR="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --ref) REF="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --yes) ASSUME_YES=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Option inconnue : $1" >&2; usage >&2; exit 2 ;;
    esac
done

say() { printf '\n== %s\n' "$*"; }
note() { printf '   %s\n' "$*"; }

# Every change goes through `run`: printed in a dry run, done otherwise.
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '   [à faire] %s\n' "$*"
    else
        "$@"
    fi
}

ask() {
    # ask "question" → 0 for yes. A dry run answers yes, to show everything.
    if [ "$ASSUME_YES" -eq 1 ] || [ "$DRY_RUN" -eq 1 ]; then
        return 0
    fi
    local answer
    read -r -p "   $1 [o/N] " answer
    case "$answer" in o|O|oui|Oui|y|Y|yes) return 0 ;; *) return 1 ;; esac
}

ask_value() {
    # ask_value "question" default → the answer on stdout.
    if [ "$ASSUME_YES" -eq 1 ] || [ "$DRY_RUN" -eq 1 ]; then
        printf '%s' "$2"
        return
    fi
    local answer
    read -r -p "   $1 [$2] " answer
    printf '%s' "${answer:-$2}"
}

write_file() {
    # write_file path mode < content
    local path="$1" mode="$2" content
    content="$(cat)"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '   [à faire] écrire %s (mode %s)\n' "$path" "$mode"
        return
    fi
    (umask 077; printf '%s\n' "$content" > "$path")
    chmod "$mode" "$path"
}

fetch() {
    # fetch relative-path destination: from this checkout when the script
    # runs from one, from the repository at the version's tag otherwise.
    local relative="$1" destination="$2"
    if [ -f "$CHECKOUT/$relative" ]; then
        run cp "$CHECKOUT/$relative" "$destination"
    else
        run curl -fsSL "$REPOSITORY/${REF:-v$VERSION}/$relative" -o "$destination"
    fi
}

SUDO="sudo"
USER_NAME="$(id -un)"
if [ "$(id -u)" -eq 0 ]; then
    # Root works, but the files then belong to root: an ordinary account
    # that can use sudo is better.
    echo "   Attention : lancé en root ; mieux vaut ton compte habituel (avec sudo)." >&2
    SUDO=""
fi

# ---------------------------------------------------------------- 1. system
say "1. Le système"
if [ ! -r "$OS_RELEASE" ]; then
    echo "   $OS_RELEASE est illisible : système non reconnu." >&2
    exit 1
fi
# shellcheck disable=SC1090
. "$OS_RELEASE"
FAMILY=""
case " ${ID:-} ${ID_LIKE:-} " in
    *" ubuntu "*) FAMILY="ubuntu"; CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" ;;
    *" debian "*) FAMILY="debian"; CODENAME="${DEBIAN_CODENAME:-${VERSION_CODENAME:-}}" ;;
esac
if [ -z "$FAMILY" ] || [ -z "${CODENAME:-}" ]; then
    echo "   ${PRETTY_NAME:-Ce système} n'est pas de la famille Debian/Ubuntu : installe à la main" >&2
    echo "   Docker Engine et le plugin Compose, puis suis le manuel (Mise en route)." >&2
    exit 1
fi
note "${PRETTY_NAME:-$ID} — dépôts $FAMILY ($CODENAME)"

# ---------------------------------------------------------------- 2. Docker
say "2. Docker et Docker Compose"
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    note "déjà installés : $(docker --version)"
else
    note "absents : ils viennent du dépôt officiel de Docker."
    if ask "Installer Docker Engine et le plugin Compose ?"; then
        run $SUDO apt-get update
        run $SUDO apt-get install -y ca-certificates curl gnupg
        run $SUDO install -m 0755 -d /etc/apt/keyrings
        run $SUDO curl -fsSL "https://download.docker.com/linux/$FAMILY/gpg" -o /etc/apt/keyrings/docker.asc
        run $SUDO chmod a+r /etc/apt/keyrings/docker.asc
        line="deb [arch=$(dpkg --print-architecture 2>/dev/null || echo amd64) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/$FAMILY $CODENAME stable"
        if [ "$DRY_RUN" -eq 1 ]; then
            note "[à faire] écrire /etc/apt/sources.list.d/docker.list : $line"
        else
            printf '%s\n' "$line" | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
        fi
        run $SUDO apt-get update
        run $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    else
        echo "   Sans Docker, AIStack ne peut pas tourner : arrêt." >&2
        exit 1
    fi
fi
if [ "$(id -u)" -ne 0 ] && ! id -nG "$USER_NAME" | grep -qw docker; then
    note "$USER_NAME n'est pas dans le groupe docker."
    if ask "L'y ajouter (il faudra te reconnecter pour que ça compte) ?"; then
        run $SUDO usermod -aG docker "$USER_NAME"
    fi
fi
DOCKER="docker"
if [ "$DRY_RUN" -eq 0 ] && ! docker info >/dev/null 2>&1; then
    DOCKER="$SUDO docker"
fi

# ---------------------------------------------------------------- 3. AIStack directory
say "3. Le dossier d'AIStack : $DIR"
if [ ! -d "$DIR" ]; then
    run $SUDO mkdir -p "$DIR"
    run $SUDO chown "$(id -u):$(id -g)" "$DIR"
fi
run mkdir -p "$DIR/config" "$DIR/data"
if [ ! -f "$DIR/docker-compose.yml" ]; then
    fetch docker-compose.yml "$DIR/docker-compose.yml"
else
    note "docker-compose.yml déjà là : gardé."
fi
if [ ! -f "$DIR/.env" ]; then
    docker_gid="$(stat -c %g /var/run/docker.sock 2>/dev/null || getent group docker | cut -d: -f3 || echo 999)"
    write_file "$DIR/.env" 644 <<EOF
# AIStack — docker compose settings (ADR-0017), written by install.sh.
AISTACK_VERSION=$VERSION
AISTACK_UID=$(id -u)
AISTACK_GID=$(id -g)
DOCKER_GID=$docker_gid
EOF
else
    note ".env déjà là : gardé."
fi
if [ ! -f "$DIR/.env.web" ]; then
    write_file "$DIR/.env.web" 600 <<'EOF'
# AIStack's secrets (never shown). The API keys are entered from the
# browser: /setup, then Settings → API keys.
EOF
fi

HOST_ADDRESS="$(hostname -I 2>/dev/null | awk '{print $1}')"
HOST_ADDRESS="${HOST_ADDRESS:-$(hostname)}"

prerequisite() {
    # prerequisite name → copies its compose file to /srv/<name>.
    local name="$1" target="$PREREQ_ROOT/$1"
    if [ -f "$target/compose.yml" ]; then
        note "$target/compose.yml déjà là : gardé."
        return 1
    fi
    run $SUDO mkdir -p "$target"
    run $SUDO chown "$(id -u):$(id -g)" "$target"
    fetch "deploy/prerequisites/$name/compose.yml" "$target/compose.yml"
    return 0
}

# ---------------------------------------------------------------- 4. prerequisites
say "4. Les prérequis (chacun est facultatif)"
WITH_POCKET_ID=no WITH_GOTIFY=no WITH_SYNCTHING=no WITH_OLLAMA=no
domain="" id_name=""

note "Pocket ID : la connexion par passkey. Sans lui, seul l'administrateur local se connecte."
note "Il lui faut un nom de domaine et un reverse proxy en HTTPS (Nginx Proxy Manager, par exemple)."
if ask "Installer Pocket ID ?"; then
    WITH_POCKET_ID=yes
    domain="$(ask_value "Nom de domaine" "example.org")"
    id_name="$(ask_value "Adresse de Pocket ID" "id.$domain")"
    if prerequisite pocket-id; then
        key="$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)"
        write_file "$PREREQ_ROOT/pocket-id/.env" 600 <<EOF
APP_URL=https://$id_name
ENCRYPTION_KEY=$key
EOF
        unset key
        run $DOCKER compose -f "$PREREQ_ROOT/pocket-id/compose.yml" --project-directory "$PREREQ_ROOT/pocket-id" up -d
    fi
    note "Dans le reverse proxy, crée l'hôte https://$id_name → http://$HOST_ADDRESS:1411"
    note "(certificat Let's Encrypt, WebSockets autorisés). /setup vérifiera qu'il répond."
fi

note "Gotify : les notifications de la vigie (santé qui baisse, Dock, hôte silencieux…)."
if ask "Installer Gotify ?"; then
    WITH_GOTIFY=yes
    if prerequisite gotify; then
        password="$(openssl rand -base64 18 2>/dev/null || head -c 18 /dev/urandom | base64)"
        write_file "$PREREQ_ROOT/gotify/.env" 600 <<EOF
GOTIFY_DEFAULTUSER_PASS=$password
EOF
        unset password
        run $DOCKER compose -f "$PREREQ_ROOT/gotify/compose.yml" --project-directory "$PREREQ_ROOT/gotify" up -d
        note "Gotify : http://$HOST_ADDRESS:8070 — compte admin, son mot de passe est dans"
        note "$PREREQ_ROOT/gotify/.env (lisible par toi seul) ; change-le à la première connexion."
    fi
fi

note "Syncthing : la synchronisation vers les téléphones et les ordinateurs."
if ask "Installer Syncthing ?"; then
    WITH_SYNCTHING=yes
    if prerequisite syncthing; then
        write_file "$PREREQ_ROOT/syncthing/.env" 600 <<EOF
PUID=$(id -u)
PGID=$(id -g)
EOF
        run $DOCKER compose -f "$PREREQ_ROOT/syncthing/compose.yml" --project-directory "$PREREQ_ROOT/syncthing" up -d
        note "Syncthing : http://$HOST_ADDRESS:8384 — définis un mot de passe pour son interface."
    fi
fi

note "Ollama : l'IA locale, en secours de Gemini (modèle $MODEL, environ 2 Go)."
if command -v ollama >/dev/null 2>&1; then
    note "Ollama déjà installé."
    WITH_OLLAMA=yes
    if ! ollama list 2>/dev/null | grep -q "^$MODEL"; then
        if ask "Télécharger le modèle $MODEL ?"; then
            run ollama pull "$MODEL"
        fi
    fi
elif ask "Installer Ollama et le modèle $MODEL ?"; then
    WITH_OLLAMA=yes
    if [ "$DRY_RUN" -eq 1 ]; then
        note "[à faire] curl -fsSL https://ollama.com/install.sh | sh"
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    run ollama pull "$MODEL"
fi

# ---------------------------------------------------------------- 5. start
say "5. Démarrer AIStack"
# What the assistant's pages start from (ADR-0023 § 5) — never a
# secret — and the installation token that opens them, kept until the
# assistant is finished.
SETUP_DIR="$DIR/data/setup"
run mkdir -p "$SETUP_DIR"
write_file "$SETUP_DIR/install.env" 600 <<EOF
HOST_NAME=$(hostname)
HOST_ADDRESS=$HOST_ADDRESS
DOMAIN=$domain
ID_NAME=$id_name
POCKET_ID=$WITH_POCKET_ID
GOTIFY=$WITH_GOTIFY
SYNCTHING=$WITH_SYNCTHING
OLLAMA=$WITH_OLLAMA
EOF
token=""
if [ -f "$SETUP_DIR/finished" ]; then
    note "L'assistant d'installation est déjà terminé : il reste fermé."
elif [ -s "$SETUP_DIR/token" ]; then
    token="$(cat "$SETUP_DIR/token")"
elif [ "$DRY_RUN" -eq 1 ]; then
    token="JETON"
    note "[à faire] écrire $SETUP_DIR/token (mode 600)"
else
    token="$(openssl rand -hex 24 2>/dev/null || head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    printf '%s\n' "$token" | write_file "$SETUP_DIR/token" 600
fi
run $DOCKER compose --project-directory "$DIR" -f "$DIR/docker-compose.yml" pull
run $DOCKER compose --project-directory "$DIR" -f "$DIR/docker-compose.yml" up -d
say "C'est prêt pour la suite dans le navigateur"
if [ -n "$token" ]; then
    note "Ouvre cette adresse depuis un poste du réseau local (elle porte le jeton d'installation) :"
    note "http://$HOST_ADDRESS:8186/setup/open?token=$token"
    note "L'hôte, l'adresse publique, la connexion, le stockage et les clés d'API se règlent là."
    note "Adresse perdue ? cd $DIR && docker compose exec web python -m aistack.cli.setup_token"
else
    note "Ouvre http://$HOST_ADDRESS:8186/setup depuis un poste du réseau local."
fi
