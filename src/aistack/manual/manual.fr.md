# Manuel utilisateur d'AIStack

AIStack observe l'infrastructure sur laquelle il est installé, garde ce qu'il
observe avec sa date et son origine, mesure son état de santé, et aide la
personne qui l'administre à comprendre, expliquer et corriger. Ce manuel
décrit chaque écran et la mise en route d'une nouvelle installation.

## Les bases

### Deux adresses

AIStack répond sur deux adresses :

- **l'adresse publique** (par exemple `https://aistack.<nom_de_domaine>`),
  joignable depuis internet : la console, l'aide, les mentions légales, la
  licence, les Paramètres, et — une fois connecté — Architecture et le
  Cockpit Santé ;
- **l'adresse du réseau local** (par exemple `http://serveur:8186`) : tout ce
  qui précède, plus les écrans qui montrent l'historique de l'infrastructure
  ou qui agissent sur elle (Priorité CPU, sélection musicale, découverte
  réseau, assistant de pannes, Time Machine).

Sur la console, la bordure d'une carte dit d'où l'écran est joignable :
bleu-gris pour le réseau local, dorée pour internet.

### Se connecter

Le bouton **Se connecter**, en haut de chaque page, ouvre la page de
connexion du fournisseur d'identité (Pocket ID). Après la connexion, tu
reviens sur la page que tu avais demandée, avec ton nom en haut de la page.
**Se déconnecter** ferme la session sur AIStack et chez le fournisseur.

Sur le réseau local seulement, un **compte de secours** permet d'entrer quand
le fournisseur ou internet est indisponible : le lien **Administrateur de
secours**, à côté de *Se connecter*. Après cinq mots de passe erronés en
quinze minutes, il refuse toute tentative jusqu'à la fin de ces quinze
minutes.

Une session se termine après **8 heures sans activité** ou **7 jours** au
plus.

### Profils

| Profil | Qui | Peut |
|---|---|---|
| **Administrateur** | membre du groupe `aistack_admins` du fournisseur, ou le compte de secours | tout lire et agir |
| **Utilisateur** | tout autre compte du fournisseur | tout lire, ne rien modifier |
| *Non connecté* | — | la console, l'aide, les mentions légales, la licence, la langue |

Une action refusée affiche une page qui dit pourquoi. Le profil est relu à
chaque connexion : retirer quelqu'un du groupe chez le fournisseur prend effet
à sa connexion suivante.

### Langue

Les drapeaux, en haut de chaque page, changent la langue de toutes les pages ;
la page Paramètres permet de la choisir explicitement. Le choix est gardé dans
ce navigateur par un seul cookie.

### Bulles d'aide

Chaque bouton, lien et champ dit ce qu'il fait quand on le survole.

## La console

C'est la page d'accueil. Elle réunit :

- **le cadre de santé** : le score sur 100 du dernier passage du Cockpit
  Santé, la note de dette technique (plus elle est basse, plus il reste de
  domaines avec de la dette à traiter) et une pastille par domaine — verte sans constat, rouge
  avec au moins un constat (un clic ouvre son détail dans le Cockpit), grise
  si le domaine n'est pas mesuré sur cet hôte ;
- **les cartes des écrans**, regroupées par adresse (réseau local ou
  internet), chacune avec une description ;
- **la colonne de gauche** : l'aide (qui mène à ce manuel), les mentions
  légales, la licence et les sources (dépôts du code et image Docker).

La console est régénérée à chaque démarrage du service web et par
`python -m aistack.cli.console_render`.

## Paramètres

Ouverts depuis le bouton **Paramètres** en haut de chaque page.

- **Langue de l'interface** — pour tout le monde.
- **Mon profil** — une fois connecté : nom, e-mail, profil, groupes, quand et
  comment la session a été ouverte, quand elle se termine au plus tard.
- **Sessions ouvertes** — administrateurs : qui est connecté, par quelle
  méthode, sur quelle adresse, depuis quand, dernière activité, et le bouton
  **Fermer** pour terminer la session de quelqu'un d'autre.
- **Journal des connexions** — administrateurs : connexions, refus,
  déconnexions et échecs du compte de secours des 30 derniers jours.
- **Disques et montages** — administrateurs : les disques et points de
  montage que voit le serveur, leur taille, leur espace libre, et ce
  qu'AIStack y stocke déjà.
- **Emplacement des données d'AIStack** — administrateurs : où vivent
  toutes les données d'AIStack (historiques, explications, graphe,
  sessions, pages générées), en un seul bloc. Choisis un autre disque
  dans la liste : n'y figurent que les disques locaux accessibles en
  écriture, avec leur espace libre, hors celui où sont déjà les données
  (pas de partage réseau : la base des sessions n'y est pas en sûreté).
  Les données iront dans `AIStack/data` : un dossier `AIStack` réservé,
  à la racine du disque. AIStack
  refuse un disque sans assez de place, puis enregistre le choix et
  affiche **les commandes à lancer**, dans l'ordre. Il ne déplace jamais rien lui-même. En installation git, les
  services sont arrêtés, les données copiées, `reports/generated` devient
  un lien vers le nouveau dossier et l'ancien est gardé sous
  `reports/generated.avant-deplacement` ; avec Docker, les données sont
  copiées et `AISTACK_DATA_DIR` est déclaré dans `.env`. L'état passe à
  **fait** une fois les services redémarrés.

## Architecture

*Connexion requise.* La carte de l'infrastructure, régénérée par
`python -m aistack.cli.architecture_render` :

- le graphe de topologie des conteneurs et leurs dépendances réelles
  (`depends_on:`) ;
- la topologie réseau externe et le matériel de chaque machine ;
- l'état en direct des machines remonté par Beszel ;
- la **CMDB temps réel** : chaque point d'accès HTTP déclaré, interrogé au
  moment de la génération.

## Cockpit Santé

*Connexion requise.* Régénéré par `python -m aistack.cli.health_render`.

Le score sur 100 combine sept domaines, chacun pondéré selon `OPS-0008` :
stockage, services, sauvegardes et PRA, GPU, tests de restauration, état
persistant (chaque service qui garde des données a-t-il une stratégie de
sauvegarde réelle ?) et écarts d'inventaire (services déclarés contre
conteneurs réellement découverts). Une carte séparée donne la dette
technique : chaque domaine qui porte au moins un constat de dette retire
15 points une seule fois (`OPS-0008`), et ses constats sont listés.
Un service qu'on ne lance qu'à la demande se déclare avec
`on_demand: true` dans `service_categorization.yml` : arrêté, il n'est pas
compté comme un écart d'inventaire.

Un clic sur la pastille d'un score (« à surveiller », « action requise »),
sur la console comme dans le Cockpit, ouvre le **plan d'action** : ce qu'il
faut faire d'abord, domaine par domaine, classé par ce que chaque action
fait gagner au score, avec où agir (le fichier à modifier, la commande à
lancer) et, pour chaque constat, le lien vers l'assistant IA. Rien n'y est
appliqué ; il est recalculé à chaque passage du Cockpit.

Chaque constat indique son sujet, son interprétation, la correction proposée
et sa confiance. Le lien **Diagnostiquer avec l'assistant IA** ouvre ce constat dans l'assistant
de pannes, sur le réseau local.

Après une modification qui change le score, régénère la console et le
Cockpit ensemble, pour qu'ils affichent le même chiffre :

```
python -m aistack.cli.console_render && python -m aistack.cli.health_render
```

## Priorité CPU

*Réseau local, connexion requise, enregistrement réservé aux
administrateurs.* Chaque conteneur reçoit une classe :

- **Ignoré, non touché** — aucune limite ;
- **Au ralenti** — limité à peu de CPU (la valeur par défaut est affichée en
  haut ; un champ permet de la changer pour ce conteneur) ;
- **Prioritaire** — reçoit plus de CPU quand il est actif, avec son
  détecteur d'activité (lecture Jellyfin en cours, ou consommation CPU
  soutenue) et ses limites normale et boostée.

**Enregistrer la classification** écrit `resource_priority.yml`. Le service
`aistack-resource-priority-monitor` applique ensuite les limites : quand une
application prioritaire devient active, les conteneurs au ralenti sont
limités ; quand elle redevient calme, après la fenêtre de grâce, tout revient
à la normale. Chaque décision est enregistrée et visible dans la Time
Machine.

## Synchroniser vers un appareil

*Réseau local, connexion requise, enregistrement réservé aux
administrateurs.* La page **Selection UI** liste, pour chaque appareil
appairé avec le Syncthing du serveur (le téléphone, le portable…), chaque
contenu déclaré dans `./config/sync.yml` : musique, photos, images,
vidéos, films, séries, livres, BD, mangas, comics, documents. Pour un
contenu et un appareil :

- coche des répertoires dans l'arbre (la recherche et *Tout replier* /
  *Tout déplier* aident) ; un sous-répertoire d'un répertoire coché est
  inclus d'office ; les répertoires exclus (`restricted`, `lost+found`…)
  ne sont jamais proposés ;
- la carte **Capacité** compare la sélection au quota de l'appareil,
  partagé entre tous ses contenus (`quota_gb` dans `sync.yml`) ;
- **Enregistrer la sélection** l'enregistre ; l'exécutant sur le serveur
  (`aistack-sync.timer`, toutes les deux minutes) l'applique par liens
  physiques, sur le disque du contenu — aucune place prise en plus —, et
  Syncthing l'envoie à l'appareil ; rien ne revient vers le serveur ;
- si le dossier Syncthing n'existe pas encore, **Créer et partager le
  dossier** l'ajoute à Syncthing (envoi seul) et le partage avec
  l'appareil : accepte-le ensuite sur l'appareil.

Installation, une fois, sur le serveur, depuis une copie du dépôt : un
dossier `.aistack-sync` à la racine de chaque disque de contenu, au compte
qui possède les fichiers, puis l'exécutant ; le conteneur Syncthing doit
voir chaque disque sous `/data` (`/media/Musique` → `/data/Musique`…) :

```
cd <copie du dépôt>
for d in /media/Musique /media/Photos; do      # tes disques de contenu
  sudo install -d -o "$USER" -g "$USER" "$d/.aistack-sync"
done
sudo cp deploy/systemd/aistack-sync.service deploy/systemd/aistack-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now aistack-sync.timer
./run_sync.sh --list
```

La liseuse et les clés USB viendront ensuite (ADR-0022).

## Découverte réseau

*Réseau local, connexion requise, modification réservée aux
administrateurs.* La liste des noms d'utilisateur SSH que le scan réseau
essaie, dans l'ordre, sur chaque machine trouvée, pour y découvrir les
conteneurs Docker. N'ajoute que des comptes réels que tu contrôles : le scan
les essaie sans surveillance.

Le scan lui-même se lance depuis le serveur :
`python -m aistack.cli.network_docker_discover`.

## Assistant de pannes

*Réseau local, connexion requise, actions réservées aux administrateurs.*
La liste des pannes réelles détectées maintenant par le Cockpit Santé et la
surveillance CPU. **Commencer →** ouvre une panne en quatre étapes :

1. **la panne** détectée ;
2. **ce qu'AIStack en sait** : les mesures et les déclarations qu'elle cite,
   lues à l'instant — rien de généré ;
3. **ce que tu fais** : la marche à suivre, le bloc à écrire et le fichier où
   l'écrire, la commande qui montre que c'est réglé. Pour la seule
   correction qu'AIStack sait appliquer d'un clic (déclarer un conteneur
   « au ralenti » dans les priorités CPU), **Appliquer** l'écrit, puis un
   nouveau diagnostic vérifie qu'elle a réellement agi. Pour un test de
   restauration, que tu fais toi-même, **Enregistrer le résultat** le note
   avec les tests planifiés (`pra/scheduled.jsonl`, sans toucher à ton
   `pra_tests.yml`) et vérifie que le constat a disparu ;
4. **l'avis de l'IA**, facultatif : seulement si tu cliques **Demander
   l'avis de l'IA** — un raisonnement, une explication et une suggestion,
   jamais une source de vérité.

La question part, avec les faits de l'étape 2, d'abord à **Google Gemini**
quand une clé est déclarée, sinon — ou si Gemini ne répond pas — au modèle
local d'Ollama. Avec Gemini, la question **sort de ton réseau** : noms
d'hôtes, chemins, services, mécanismes de sauvegarde (jamais de mot de
passe) ; l'étape 4 le dit avant le clic. Pour l'activer, crée une clé dans
Google AI Studio et saisis-la dans **Paramètres → Clés d'API** (voir
ci-dessous), ou ajoute-la dans `.env.web` puis `docker compose up -d` :

```
AISTACK_GEMINI_API_KEY=<ta clé>
```
 Le modèle se choisit dans
`./config/ai_runtime.yml` (bloc `gemini:`) ; retire ce bloc pour que tout
reste sur la machine.

Chaque raisonnement de l'IA est gardé dans l'historique du sujet. Le lien
**Besoin d'aide pour ouvrir un terminal ?** explique comment se connecter au
serveur.

Une réponse de l'IA locale peut prendre plusieurs minutes : inutile
d'attendre sur la page. Dès qu'une réponse est prête, une notification
apparaît en bas à droite de la page où tu te trouves (sur le réseau local,
connecté) ; un clic ouvre la réponse, la croix la ferme.

## Clés d'API

*Administrateurs, depuis les deux adresses.* Dans **Paramètres → Clés d'API** : toutes
les clés et accès que les composants d'AIStack lisent (Gemini, Gotify,
Syncthing, Jellyfin, Beszel…), déclarés dans `api_keys.yml`. Pour chacune :
d'où vient la valeur (saisie ici, `.env.web` ou absente), ses quatre derniers
caractères — jamais la clé entière —, un champ pour la remplacer, **Effacer**
et, quand le service le permet, **Tester**. Une valeur saisie ici est gardée
dans le dossier des données (`secrets/api_keys.json`, lisible par AIStack
seul) et passe avant `.env.web` ; effacée, celle de `.env.web` revient. La
ligne de chaque clé dit quand elle est prise en compte (tout de suite, au
prochain passage de la vigie, au redémarrage d'un conteneur). Chaque clé dit aussi comment l'obtenir (« Comment l'obtenir »). Les secrets
de connexion (Pocket ID, administrateur local) n'y sont pas : ils restent
dans `.env.web`, ou dans ce qu'a gardé l'assistant d'installation.

## Time Machine

*Réseau local, connexion requise.* Ce qu'AIStack a observé, gardé dans un
graphe de provenance (PROV-O). Le graphe se reconstruit en entier, à la
demande, depuis les historiques :

```
python -m aistack.cli.timemachine_rebuild
```

Tant qu'il n'a jamais été construit, chaque page le dit et donne cette
commande. Quatre vues, reliées par le menu en haut de chaque page :

### Flux

Un flux par historique (décisions CPU, observations Docker, événements
Docker, dérive de fichiers, empreintes d'images, inventaires de paquets,
raisonnements de l'IA…). Un flux ouvre la liste de ses instants ; un instant
ouvre tout ce que le graphe sait de lui.

### Arbre

Réseau → Hôte → Stack → Conteneur, lu en direct depuis Docker et Compose,
avec une recherche par nom. **Historique** ouvre le nœud d'un élément dans le
graphe ; **Voir dans le ruban** ouvre sa chronologie.

### Ruban

Tous les instants enregistrés sur un axe du temps, une ligne par flux,
filtrables par flux et par sujet. Un clic ou un glissé ouvre l'instant le
plus proche ; un groupe d'instants trop serrés se déplie en liste. La liste
complète, en dessous, est paginée et groupée par flux.

### Explications

Chaque sujet qui a une explication — le *pourquoi* — avec le statut, la
confiance, l'auteur, le validateur, la date et le nombre de versions de sa
version actuelle. Le filtre **Statut** montre les explications à traiter
(*Proposed*), validées ou écartées ; la recherche filtre par nom. Un sujet
ouvre sa page Pourquoi.

### Un nœud

La page d'un nœud montre trois colonnes : l'arbre du réseau, la chronologie
du sujet (avec **Reconstituer à cet instant** et **Voir le pourquoi**), et
les faits connus du nœud avec son diagramme de provenance.

### Reconstituer

Ce qui était connu d'un sujet à un instant donné, flux par flux : la
dernière observation à cet instant ou avant, ou « rien d'observé encore ».
AIStack ne restaure jamais rien depuis cet écran.

### Pourquoi

Toutes les versions de l'explication d'un sujet, de la plus ancienne à
l'actuelle, avec leur confiance, leur statut, leur auteur, leur validateur et,
pour une version écartée, qui l'a écartée et pourquoi. Les explications
sont écrites par les administrateurs, ou importées à chaque reconstruction du
graphe depuis les réponses de l'IA et les commentaires datés de
`pra_tests.yml`, comme propositions à valider.

Un administrateur dispose de trois actions ; chacune ajoute une version,
aucune n'efface :

- **Rédiger** — un nouveau texte, qui part de la version actuelle ;
  enregistrer deux fois le même texte est refusé ;
- **Valider** — confirmer la version actuelle, en second auteur ;
- **Écarter** — mettre la version actuelle de côté, avec une raison
  obligatoire.

Les règles dépendent de la **phase** de l'instance :

| | Phase de développement | Phase de production |
|---|---|---|
| Un texte rédigé | est validé dès son enregistrement, en ton nom | attend la validation d'une autre personne |
| Valider son propre texte | permis | refusé |
| Effacer les versions d'un sujet | `python -m aistack.cli.explications_admin purge <sujet>` | impossible |

Si quelqu'un a modifié l'explication depuis l'ouverture de ta page, ton
action est refusée et la page le dit : relis la version actuelle, puis
recommence. Le graphe voit chaque action au prochain `timemachine_rebuild`.

## Mise en route d'une nouvelle installation

Une nouvelle installation se fait avec Docker, en deux temps : un script
pose la base sur le serveur, puis l'**assistant d'installation**, dans le
navigateur, demande tout le reste, une étape après l'autre. Aucun
fichier n'est à modifier à la main.

### Avec Docker

**Avant de commencer.**

- Un serveur Linux de la famille Debian : Debian, Ubuntu, Linux Mint ou
  LMDE. Un autre système reçoit la liste de ce qu'il faut installer, et
  le script s'arrête.
- Ton compte habituel, avec `sudo`. Pas `root`.
- Pour se connecter depuis l'extérieur avec Pocket ID (passkeys) : un nom
  de domaine, un reverse proxy en HTTPS (Nginx Proxy Manager, par
  exemple), et la box qui renvoie les ports 80 et 443 vers lui. Sans
  cela, seul l'administrateur de secours se connecte, depuis le réseau
  local.

**1. Le script.** Sur le serveur, la version à installer à la place de
`<version>` :

```
curl -fsSLO https://raw.githubusercontent.com/bigbrother1969-bis/AIStack/v<version>/scripts/install.sh
bash install.sh --dry-run      # dit ce qu'il ferait, sans rien changer
bash install.sh --version <version>
```

Il lit d'abord, puis demande avant chaque changement :

1. **le système** ;
2. **Docker et Docker Compose**, depuis le dépôt de Docker, s'ils
   manquent ; ton compte est ajouté au groupe `docker` ;
3. **le dossier d'AIStack**, `/srv/aistack` (ou celui donné par `--dir`) :
   `docker-compose.yml`, `.env`, `config/`, `data/`, `.env.web` ;
4. **les prérequis**, chacun facultatif, chacun dans son propre dossier
   `/srv/<nom>` : **Pocket ID** (il demande le nom de domaine), **Gotify**
   (les notifications), **Syncthing** (la synchronisation vers les
   appareils) et **Ollama** avec le modèle `qwen2.5:3b` (l'IA locale, en
   secours de Gemini) ;
5. **le démarrage d'AIStack**, puis l'adresse de l'assistant.

Le script n'affiche jamais de secret : ceux qu'il crée vont dans un
fichier lisible par toi seul, et il dit lequel. Relancé, il ne refait que
ce qui manque.

**2. L'assistant d'installation.** Le script finit par une adresse de la
forme `http://<adresse du serveur>:8186/setup/open?token=…` : ouvre-la
depuis un poste du réseau local. Le jeton qu'elle porte ouvre
l'assistant, et lui seul ; il reste valable jusqu'à la fin de
l'assistant. Adresse perdue ? Sur le serveur :

```
cd /srv/aistack
docker compose exec web python -m aistack.cli.setup_token
```

Six étapes, chacune enregistrée depuis sa page :

1. **L'hôte** : le nom du serveur sur le réseau local (son adresse IP
   s'il ne répond pas depuis un autre poste), le port public (8183), le
   port du réseau local (8186) et la phase. Laisse **Mise au point**
   pendant l'installation.
2. **L'adresse publique** : le nom de domaine, le reverse proxy et les
   deux noms, `aistack.<domaine>` et `id.<domaine>`. La page donne
   ensuite les deux hôtes à créer dans le reverse proxy, avec l'adresse
   et le port vers lesquels chacun renvoie, puis vérifie qu'ils
   répondent.
3. **La connexion** : la procédure dans Pocket ID (le premier compte sur
   `https://id.<domaine>/setup`, le groupe `aistack_admins`, le client
   OIDC et ses **quatre adresses**, que la page écrit pour toi), puis
   l'identifiant et le secret du client, et le mot de passe de
   l'**administrateur de secours**. Le secret n'est plus jamais affiché ;
   le mot de passe est haché, jamais gardé en clair.
4. **Le stockage** : `/media`, `/srv` et `/opt` sont toujours lus ; coche
   les autres disques du serveur, ou tape d'autres dossiers (un par
   ligne). AIStack les lit, en lecture seule, au même chemin.
5. **Les clés d'API** : chaque clé avec la façon de l'obtenir (Gemini,
   Gotify, Syncthing…), **Tester** pour la vérifier. Aucune n'est
   indispensable.
6. **La vérification** : chaque prérequis est interrogé une fois (Gotify
   envoie un message de test à ton téléphone) ; ce qui ne répond pas est
   dit, avec ce qu'on perd sans lui. **Terminer l'assistant** efface le
   jeton.

**3. Redémarrer et se connecter.** La dernière page donne la commande :

```
cd /srv/aistack
docker compose up -d --force-recreate
```

Puis connecte-toi avec Pocket ID à l'adresse publique, ou, depuis le
réseau local, avec l'administrateur de secours (`/login/local`). Dans
**Paramètres**, ton profil doit indiquer **Administrateur**. Le reste — la
topologie, les sauvegardes, les liens de la console — se déclare au fil
de l'eau, dans `./config`.

**Ce que l'assistant écrit, et où.** Les déclarations dans `./config`
(`instance_config.yml`, `authentication.yml`, `volumes.yml`, que
`docker compose` lit grâce à la ligne `COMPOSE_FILE` de `.env`) ; les
secrets dans le dossier des données, lisibles par AIStack seul
(`secrets/sign_in.json` pour la connexion, `secrets/api_keys.json` pour
les clés d'API). Ensuite, les déclarations se modifient dans leurs
fichiers, les clés d'API dans **Paramètres → Clés d'API**. Un dossier à
lire en plus : ajoute-le à `./config/volumes.yml`, puis
`docker compose up -d`.

Tant qu'une déclaration indispensable garde les valeurs de l'hôte de
référence, **chaque page affiche « ⚠ À configurer »** en haut : ce lien
ouvre la page **Premier démarrage** (`/setup`), qui dit ce qu'il reste à
déclarer, et, sur le réseau local, mène à l'assistant tant qu'il est
ouvert.

Quand une nouvelle version change une déclaration livrée : une copie que
tu n'as jamais modifiée suit la nouvelle version au démarrage ; un
fichier que tu as modifié, ou déposé toi-même, n'est jamais touché, mais
**Paramètres → Déclarations livrées** montre la différence et la commande
qui prend la version livrée, jusqu'à ce que tu cliques « Vu, je garde mon
fichier ».

**Ce qu'une installation Docker ne fait pas encore tourner.** Quatre
exécutants travaillent sur l'hôte lui-même, lancés par systemd depuis une
copie du dépôt (`deploy/systemd/`) : le Dock (mises à jour gouvernées),
les tests de restauration planifiés, l'exécutant de synchronisation vers
les appareils et la sauvegarde nocturne d'AIStack. `install.sh` ne les
installe pas : sans eux, ces écrans montrent et enregistrent, mais rien
ne s'applique sur l'hôte. Les pages d'Architecture et le graphe de la
Time Machine, eux, sont faits par la vigie à son premier passage.

Le service `web` a un contrôle de santé : `docker ps` le montre
`healthy` quand l'application répond sur le port du réseau local. Un
tableau de bord qui lit Docker (Homepage, par exemple) affiche alors
« healthy » sur sa tuile, à condition qu'elle nomme le conteneur
`aistack-web` (dans Homepage : `server:` et `container: aistack-web`).

### Depuis le dépôt git (développement)

Pour travailler sur AIStack lui-même, sans Docker. Le détail est dans la
section *How to install* du README du dépôt. Dans l'ordre :

1. **Prérequis** : un hôte Linux avec systemd, Python 3.13, git, un
   fournisseur OpenID Connect (Pocket ID) joignable en HTTPS, et un
   reverse proxy avec TLS pour l'adresse publique. En option : Ollama
   (l'IA), Syncthing, Beszel (les métriques).
2. **Le code** : cloner le dépôt dans `/srv/aistack`, créer l'environnement
   Python (`python3.13 -m venv .venv`, puis
   `.venv/bin/python -m pip install -e ".[dev]"`), et vérifier que
   `pytest -q` passe.
3. **Les déclarations** : sous `src/aistack/*/definitions/`, au minimum le
   nom de l'hôte et les deux ports (`instance_config.yml`), l'adresse du
   fournisseur et l'adresse publique (`authentication.yml`), la topologie,
   le réseau à scanner et les liens de la console. Laisse
   `phase: development` pendant la mise au point.
4. **Le fournisseur d'identité** : un groupe nommé exactement
   `aistack_admins` (son *nom*, pas son nom d'affichage), un client
   confidentiel avec PKCE et **quatre adresses** — les deux URL de retour
   (`/auth/callback`) et les deux URL après déconnexion (`/console.html`),
   pour l'adresse publique et pour celle du réseau local, écrites à la
   lettre près.
5. **Les secrets** dans `.env.web`, sans les afficher : l'identifiant et le
   secret du client, puis le mot de passe du compte de secours avec
   `python -m aistack.cli.web_admin_password >> .env.web` ; ensuite
   `chmod 600 .env.web`.
6. **Les services** : adapter l'utilisateur et le chemin des unités de
   `deploy/systemd/`, les copier dans `/etc/systemd/system/`, puis
   `systemctl enable --now` pour `aistack-web` et les collecteurs.
7. **Le reverse proxy** : publier **uniquement** le port public (8183) ;
   jamais le port du réseau local.
8. **Premières pages** : `architecture_render`, `health_render`,
   `console_render`, les imports d'explications, puis
   `timemachine_rebuild`.
9. **Vérifier** : ouvre l'adresse du réseau local, connecte-toi ; dans
   Paramètres, ton profil doit indiquer **Administrateur**.

### Passer en production

Quand d'autres personnes utilisent AIStack : `phase: production` dans
`instance_config.yml`, puis redémarrer AIStack (`docker compose restart`,
ou `sudo systemctl restart aistack-web` sur une installation git). Une
deuxième personne valide alors les Explications, et rien n'est jamais
effacé.

## Sauvegarder et restaurer AIStack

AIStack se sauvegarde lui-même chaque nuit à 03:00, à chaud, sans rien
arrêter : `scripts/backup_aistack.sh`, lancé par le minuteur systemd
`aistack-backup.timer`. L'archive va dans `/media/BACKUP/AIStack/`
(lisible par toi seul, gardée 30 jours) et contient les données (sauf le
graphe de la Time Machine, qui se reconstruit), `./config` et les
fichiers `.env`, secrets compris.

Mise en place, une fois, sur le serveur (en root) :

```
install -d -o <utilisateur> -g <utilisateur> -m 700 /media/BACKUP/AIStack
cp deploy/systemd/aistack-backup.service deploy/systemd/aistack-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now aistack-backup.timer
```

Le domaine Sauvegarde/PRA du Cockpit Santé signale une sauvegarde
absente ou de plus de 2 jours.

**Tester une restauration**, sans toucher à l'installation en service :

```
scripts/restore_aistack.sh /media/BACKUP/AIStack/aistack-<date>.tar.gz /tmp/aistack-restore
```

Le script restaure dans un dossier neuf, vérifie la base des sessions et
les explications, puis affiche la commande qui reconstruit le graphe de la
Time Machine à partir des fichiers restaurés, dans un conteneur jetable
sans réseau. Si elle réussit, note la date et la durée dans
`pra_tests.yml` (service `aistack`). Remettre une copie restaurée en
service reste un geste manuel.

Plus simple : `python -m aistack.cli.sandbox restore aistack` fait tout
cela en bac à sable (section suivante), démarre en plus l'application sur
les données restaurées et mesure le temps de reprise. Les fichiers
d'environnement (secrets) sont restaurés et comptés, jamais donnés au bac
à sable : la connexion n'y est pas disponible, la console est ce qui est
vérifié.

## Tester la restauration d'un service en bac à sable

Pour les services qui ont une recette (WordPress, AIStack lui-même, Nextcloud et Immich), une
commande sur l'hôte restaure la dernière sauvegarde à côté du service en
service, jamais à sa place :

```
cd <dossier d'AIStack>
source scripts/dev-env.sh
python -m aistack.cli.sandbox recipes
python -m aistack.cli.sandbox restore wordpress
```

La commande tourne sur l'hôte, depuis une copie du dépôt (installation
git, `scripts/dev-env.sh`) : elle a besoin de Docker et, pour Immich, de
`duplicity`. Une installation par Docker seul ne l'a pas.

Le bac à sable a son propre réseau Docker interne (ni Internet, ni accès
aux services, aucun port publié), ses propres conteneurs
(`aistack-sandbox-…`) et ses propres mots de passe jetables. Il reprend
les images des conteneurs en service et ne lit rien d'autre chez eux. Les
fichiers restaurés vont sur le disque local (`run_root` dans
`sandbox.yml`) ; la commande vérifie d'abord la place libre et refuse si
elle manque. À la fin, réussite ou échec, tout est effacé sauf le
rapport, écrit dans le dossier des données, sous `sandbox/`.

La commande affiche chaque étape, chaque vérification, le temps de
reprise mesuré et l'entrée qu'elle propose pour `pra_tests.yml`. Elle ne
l'écrit pas : copie-la si tu la valides. Pour Nextcloud et Immich, la
base de données est restaurée entière ; pour Immich, quelques photos de
la bibliothèque externe sont reprises dans la sauvegarde Déjà Dup et
comparées à l'empreinte que la base garde d'elles. Ce qu'aucune
sauvegarde ne contient est dit dans le rapport. Si une exécution a été
interrompue, `python -m aistack.cli.sandbox cleanup` retire ce qu'elle a
laissé.

Pour comparer la sauvegarde restaurée avec le service en marche, ajoute
`--compare` : `python -m aistack.cli.sandbox restore wordpress --compare`.
Le rapport montre, sans verdict, les lignes par table et les fichiers par
dossier côté sauvegarde et côté vivant, les plus gros écarts d'abord. Une
sauvegarde de la nuit a toujours un peu de retard : c'est à toi de juger
l'écart. Le côté vivant est seulement lu (fichiers sur l'hôte, comptages
dans la base du conteneur avec ses propres variables).

### Tests de restauration planifiés

Chaque dimanche matin, après les sauvegardes de la nuit, le minuteur
`aistack-pra.timer` refait ce test pour chaque service qui a une recette
et n'a pas été testé dans les six derniers jours. Le résultat est
**enregistré par AIStack** dans le dossier des données
(`pra/scheduled.jsonl`) et compte dans le domaine Tests PRA du Cockpit
Santé : une réussite rafraîchit la date du service, un échec devient un
constat jusqu'au prochain test réussi. `pra_tests.yml` reste ton fichier :
AIStack ne le réécrit jamais, et garde pour chaque service le résultat le
plus récent des deux. Le test attend que le Dock ait fini, et le Dock
attend le test.

Installation, une fois, sur l'hôte (en root) :

```
cd /srv/aistack/AIStack
cp deploy/systemd/aistack-pra.service deploy/systemd/aistack-pra.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now aistack-pra.timer
```

Pour lancer un test tout de suite et voir les résultats :

```
./run_pra_schedule.sh wordpress
./run_pra_schedule.sh --all
./run_pra_schedule.sh --list
```

## Dock : mettre à jour un service de façon gouvernée

Les services déclarés dans `dock.yml` (WordPress, par exemple) ne
changent d'image que par le dock, depuis la console → *Dock* (réseau
local, connecté). La page montre, pour chaque conteneur, l'image qui
tourne et si une image plus récente est publiée pour le même tag ; elle
ne télécharge rien.

Quand une mise à jour est disponible, un administrateur la propose en
écrivant pourquoi (obligatoire : ce sera l'explication du changement).
Un administrateur la valide — en production, un autre que l'auteur. La
proposition validée est ensuite prise en charge par l'exécuteur du
dock, sur l'hôte : restauration en bac à sable de la dernière
sauvegarde, répétition avec la nouvelle image, puis application avec
retour arrière prêt. Une proposition peut être rejetée tant qu'elle
n'a pas commencé.

Un service gouverné ne doit plus porter le label de Watchtower : la page
signale ceux qui l'ont encore. Retire-le de leur fichier compose.

L'exécuteur du dock tourne sur l'hôte, comme service systemd, et prend
les propositions validées une à une. Installe-le une fois, en root :

```
cp deploy/systemd/aistack-dock.service deploy/systemd/aistack-dock.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now aistack-dock.timer
```

Pour chaque proposition, dans l'ordre : vérifications préalables (le
conteneur tourne toujours l'image d'origine, sans label Watchtower) ;
restauration en bac à sable réussie de moins de 24 h, sinon il en lance
une ; téléchargement de la nouvelle image par son digest ; répétition de
la restauration avec elle ; conservation de l'image précédente
(`aistack-dock/<conteneur>:<proposition>`) ; application avec le projet
compose du service ; vérifications sur le service réel. Un échec avant
l'application arrête tout sans rien toucher ; un échec après remet
l'image précédente et vérifie de nouveau. Chaque étape apparaît sur la
page, avec sa durée et ce qu'elle a constaté. En ligne de commande :

```
python -m aistack.cli.dock list
python -m aistack.cli.dock show <proposition>
journalctl -u aistack-dock -n 50
```

Une fois la proposition exécutée, son pourquoi entre dans la Time
Machine comme explication du conteneur changé (sujet
`<projet compose>/<service>`, par exemple `wordpress/wordpress`), avec
son auteur, son résultat et le nom de la proposition. Après la
reconstruction du graphe, le changement y apparaît comme une activité
reliée aux personnes qui l'ont proposé et validé, aux images avant et
après, et à son explication.

## Revenir à l'image d'avant une mise à jour

Quand un service va mal après une mise à jour de son image (Watchtower,
par exemple), répète d'abord le retour arrière en bac à sable :

```
python -m aistack.cli.sandbox rollback wordpress
python -m aistack.cli.sandbox rollback wordpress --container wp_app
```

La commande retrouve l'image que chaque conteneur de la recette faisait
tourner avant sa dernière mise à jour (l'historique des digests), la
télécharge par son digest si elle n'est plus sur la machine, restaure la
dernière sauvegarde avec elle et la vérifie comme une restauration
ordinaire. Si tout passe, elle affiche la ligne `image: …@sha256:…` à
mettre dans le fichier compose du service et la commande pour
l'appliquer. Le retour en vrai reste ton geste ; une image épinglée par
son digest n'est plus mise à jour par Watchtower, retire l'épingle une
fois le problème réglé.

## Vigie et notifications

La vigie refait le Cockpit Santé et la console toutes les 15 minutes, et
t'envoie sur **Gotify** ce qui a changé depuis son passage précédent :
- un hôte silencieux (son collecteur n'écrit plus) ;
- un test de restauration en échec ;
- la santé qui baisse, avec les nouveaux constats ;
- le Dock : une mise à jour proposée qui attend ta validation, puis
  appliquée, revenue en arrière ou en échec.

Chaque événement n'est dit qu'une fois : un constat qui reste n'est pas
répété. Les événements d'un même passage partent en un seul message ;
un hôte silencieux, un test échoué ou un retour arrière le font sonner.
Le premier passage ne fait que noter ce qui existe déjà.

Dans Gotify, crée une application « AIStack » et copie son jeton ;
ajoute dans `.env.web`, sans les afficher :

```
AISTACK_GOTIFY_URL=https://gotify.<nom_de_domaine>
AISTACK_GOTIFY_TOKEN=<jeton de l'application>
```

Avec Docker, la vigie est le service `vigil` : `docker compose up -d`,
puis `docker compose exec vigil python -m aistack.cli.vigil --test` pour
un message d'essai et `docker compose logs -f vigil` pour la suivre. En
installation git : `deploy/systemd/aistack-vigil.service`. Sans ces deux
variables, la vigie tourne quand même et dit que les notifications sont
coupées.

## Relance au démarrage

Au démarrage de la machine, des dizaines de conteneurs démarrent en même
temps. Quelques-uns se lèvent « en marche » mais inutilisables : un
programme resté bloqué à l'initialisation, ou un conteneur qui partage le
réseau d'un autre (`network_mode: container:…`) et dont le réseau a été
remplacé depuis. La politique de redémarrage de Docker ne voit rien, car
rien n'est tombé. Le service `restart-watch` les repère et les relance
dans l'ordre que leurs dépendances demandent.

Un conteneur est jugé bloqué à l'un de ces trois signes : son contrôle de
santé dit « unhealthy » ; il partage le réseau d'un conteneur démarré
après lui ; ou, s'il n'a aucun contrôle de santé, la sonde que tu as
déclarée pour lui ne répond pas. Un conteneur arrêté n'est jamais relancé.

Garde-fous : la surveillance n'agit que pendant 30 minutes après son
propre démarrage (qui suit celui de Docker), seulement sur un conteneur vu
bloqué deux passages de suite, au plus deux fois par heure et par
conteneur. Elle redémarre un conteneur après l'autre, chacun seulement
quand le précédent répond ; si l'un ne revient pas, elle s'arrête là et
te prévient par Gotify. Hors de la fenêtre, elle note sans agir.

L'écran « Relance au démarrage » de la console montre la fenêtre, les
conteneurs bloqués et le journal des décisions. Les réglages (fenêtre,
tentatives, conteneurs jamais touchés, ordre imposé, sondes) sont dans
`./config/restart_watch.yml`. Pour voir ce qu'elle ferait sans rien
relancer : `docker compose exec restart-watch python -m
aistack.cli.restart_watch --once --dry-run --ignore-window`. En
installation git : `deploy/systemd/aistack-restart-watch.service`.

## Nouveautés

Quand tu ajoutes un conteneur, AIStack le voit déjà comme un écart
d'inventaire dans le Cockpit. La vigie te le dit maintenant par Gotify, et
l'écran « Nouveautés » de la console le propose.

La vigie, qui passe toutes les 15 minutes, annonce un conteneur que
aucun service ne déclare, une seule fois, quand elle l'a vu à **deux
passages de suite** : un conteneur qui ne vit que quelques minutes n'est
jamais annoncé. Au tout premier passage, elle note seulement ce qui est
là : les conteneurs non déclarés le jour de l'installation ne sont pas
des nouveautés, ils restent listés sur l'écran.

L'écran montre chaque conteneur en attente (où il tourne, son image, ses
ports, s'il demande le GPU) avec un formulaire prérempli : le nom, la
catégorie (une catégorie existante, ou une nouvelle) et une description.
**Déclarer** ajoute le service à `./config/service_categorization.yml`
sans toucher au reste du fichier (tes commentaires et ta mise en page
restent) et garde une copie datée à côté
(`service_categorization.yml.avant-arrivals-…`). Si le fichier a une
forme que l'écran ne sait pas modifier (une catégorie avec
`services: []`), il le dit et ne touche à rien. **Ignorer** écarte le
conteneur ; il se reprend depuis la liste « Écartés ». Seul un
administrateur peut écrire.

Une machine qui répond en SSH, fait tourner Docker et n'est déclarée
nulle part est proposée de la même façon, avec les lignes à ajouter à
`hosts.yml` une fois le collecteur installé dessus (voir « Traçabilité
des hôtes »). Elle n'est jamais ajoutée d'un clic : sans collecteur, elle
serait un hôte silencieux. Une machine déjà suivie est reconnue grâce à
`address:` dans `hosts.yml` ; « Déjà connue » écarte les autres.

Le scan des machines est **désactivé** : il essaie tous les utilisateurs
SSH déclarés contre toutes les machines du réseau, ce qui est une action.
Pour que la vigie le lance, mets par exemple `machine_scan_hours: 24`
dans `./config/arrivals.yml` ; il faut `nmap` dans l'image (livré depuis
cette version, reconstruis l'image) et la clé nommée dans
`network_discovery.yml` lisible dans le conteneur. Tu peux aussi le
lancer à la main : `docker compose exec vigil python -m
aistack.cli.network_docker_discover`. Les machines trouvées par la
**première** observation qui en contient sont la référence : elles ne
sont pas des nouveautés.

Réglages dans `./config/arrivals.yml` : `confirm_passes`, `machine_scan_hours`,
`ignore` (conteneurs jamais proposés) et `known_hosts` (adresses connues).

## Budget disque des données d'AIStack

Les données d'AIStack (le dossier des données : historique, graphe de la
Time Machine, relevés des collecteurs) ont un budget déclaré dans
`./config/data_budget.yml` : 2 Go par défaut. Le Cockpit Santé a un
domaine **Données d'AIStack** : un constat à 80 % du budget, avec le
nombre de jours avant de l'atteindre au rythme des sept derniers jours,
et un constat urgent au-delà, que la vigie envoie sur Gotify.

Chaque jour, la vigie **compresse** les observations de plus de 90 jours
(`compress_after_days`) de `history`, `docker-diff` et `docker-events`,
sur place : rien n'est effacé, AIStack les lit comme avant et la Time
Machine se reconstruit à l'identique.

```
docker compose exec web python -m aistack.cli.data_budget
docker compose exec web python -m aistack.cli.data_budget --compress --dry-run
docker compose exec web python -m aistack.cli.data_budget --compress
```

## Traçabilité des hôtes

Ce qui change sur les hôtes eux-mêmes — le serveur, et les autres
machines que tu suis —, et non dans leurs conteneurs, entre dans la Time
Machine :
- les paquets installés, mis à jour ou retirés (dpkg, apt), datés par
  les journaux des hôtes ;
- les fichiers de `/etc`, de `/usr/local/bin` et `/usr/local/sbin`, les
  crontabs, et les fichiers compose et `.env` des projets sous `/srv` et
  `/opt` ;
- les unités systemd activées ou désactivées.

D'un fichier, AIStack garde la taille, les droits, le propriétaire et
une empreinte calculée avec une clé propre à l'hôte, **jamais son
contenu**. Au premier passage, l'historique des paquets encore présent
dans les journaux est repris, sur environ huit mois.

Le collecteur est un seul fichier, qui tourne sur chaque hôte en root
toutes les 15 minutes : il ne fait que lire, sans réseau, et n'écrit
que dans son dossier. Installation sur le serveur, depuis une copie du
dépôt, pour un hôte nommé `server` dont les relevés vont dans le dossier
de données d'AIStack (`/srv/aistack/data` avec Docker) :

```
cd <copie du dépôt>
OUT=/srv/aistack/data/hosts/server
install -d -m 0750 "$OUT"
sudo install -m 0755 src/aistack/host_collector.py /usr/local/sbin/aistack-host-collector
sudo cp deploy/host-collector/aistack-host-collector.service deploy/host-collector/aistack-host-collector.timer /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/aistack-host-collector.service.d
printf '[Service]\nEnvironment=HOST=server\nEnvironment=OUTPUT=%s\nReadWritePaths=%s\n' "$OUT" "$OUT" \
  | sudo tee /etc/systemd/system/aistack-host-collector.service.d/host.conf
sudo systemctl daemon-reload && sudo systemctl start aistack-host-collector
journalctl -u aistack-host-collector -n 5 --no-pager
sudo systemctl enable --now aistack-host-collector.timer
```

Puis déclare l'hôte dans `./config/hosts.yml` (`server:` avec
`directory: hosts/server`). Sur une autre machine, les mêmes trois
fichiers (copiés avec `scp`) et un dossier que le serveur lit, par exemple
un disque partagé en NFS, déclaré dans `hosts.yml` par son chemin absolu. Ce qui ne doit pas être suivi (un fichier
qui change tout seul) s'écrit dans `/etc/aistack-host-collector.conf`
(`ignore = <chemin>`), comme ce qui doit l'être en plus
(`watch = <dossier>`, `glob = <motif>`).

Pour voir où en est chaque hôte — dernier passage, événements par
sorte, hôte silencieux (plus de passage depuis une heure) ou illisible
(disque partagé non monté) :

```
python -m aistack.cli.hosts
python -m aistack.cli.hosts --last 10
```

Après la reconstruction du graphe
(`docker compose exec web python -m aistack.cli.timemachine_rebuild`),
le ruban de la Time Machine a un groupe **Hôtes** : une ligne par hôte,
un repère par événement ; le nœud d'un événement dit ce qui a changé
(versions, état d'une unité, ligne de commande apt, ce qui a changé d'un
fichier : taille, droits, propriétaire, contenu).

Un hôte silencieux est aussi un constat du Cockpit Santé, dans le
domaine **Hôtes** : il compte dans le score, apparaît dans le plan
d'action et s'ouvre dans l'assistant de pannes. Le délai se règle dans
`./config/hosts.yml` (`silent_after_minutes`).

## Comparer les moteurs d'IA locaux

`python -m aistack.cli.ai_compare --engine ollama@127.0.0.1:11434/qwen2.5:7b --engine 'openai_chat@127.0.0.1:18095/olala?effort=low&label=Olala'` pose les mêmes questions que la page Sécurité à chaque moteur, un par un, sur les constats les plus graves du dernier rapport (`--finding` pour en nommer, `--max` pour en changer le nombre), et écrit un rapport markdown sous `ai-compare/` du dossier de données : durée, réponse, et quelques signaux automatiques (un « vous » là où la page tutoie, le mot « owner », une commande qui modifie, une réponse vide). `--dry-run` ne pose aucune question. Rien n'est modifié sur aucune machine. À toi de lire et de choisir le moteur.

## Évaluation de sécurité

`python -m aistack.cli.security_assess` (ou `docker compose exec web python
-m aistack.cli.security_assess`) dit ce que l'hôte expose : les ports qui
écoutent sur toutes les interfaces, à qui ils appartiennent et, une fois le
relevé du pare-feu installé, d'où chacun peut être joint. Il ne fait que
lire. Il sort avec le code 1 quand un point est à corriger ou urgent.
`--propose` affiche le bloc `declared_ports` pour `security.yml` et
n'applique rien.

Déclare ce qui est à toi dans `security.yml` (`declared_ports` : port et
rôle) ; un port déclaré n'est plus signalé. Les ports sensibles (SSH,
partages, bases de données) sont à laisser non déclarés tant que tu n'as pas
lu ce que le pare-feu laisse entrer.

Le conteneur ne peut pas lire le pare-feu : un petit service sur l'hôte
l'écrit toutes les dix minutes là où AIStack le lit. Il ne change aucune
règle. À installer une fois (en root) :

```bash
sudo install -m 0755 src/aistack/firewall_snapshot.py /usr/local/sbin/aistack-firewall-snapshot
sudo cp deploy/firewall-snapshot/aistack-firewall-snapshot.service deploy/firewall-snapshot/aistack-firewall-snapshot.timer /etc/systemd/system/
sudo install -d -o <propriétaire> -g <groupe> <données>/security-host   # le compte avec lequel AIStack lit ses données
sudo mkdir -p /etc/systemd/system/aistack-firewall-snapshot.service.d
# host.conf : [Service], Environment=OUTPUT=<données>/security-host et ReadWritePaths=<le même>
sudo systemctl daemon-reload && sudo systemctl enable --now aistack-firewall-snapshot.timer
```

`<données>` est le dossier derrière `reports/generated` (`./data` sauf si
les Réglages l'ont déplacé). Un relevé de plus de deux heures n'est pas
utilisé ; le rapport le dit.

Refus (T3b) : chaque passage lit aussi les compteurs (`iptables-save -c`) et
ajoute à `firewall-refusals.jsonl`, gardé sept jours, le nombre de paquets
refusés par `DOCKER-USER` (venus de hors du LAN et du VPN, vers un port
publié), par la politique par défaut d'`INPUT`, par ufw et par les autres
chaînes. Le rapport les additionne sur `refusal_window_hours` (24) et dit
combien, jamais qui : un compteur ne porte aucune adresse. Les compteurs
repartent de zéro à un redémarrage ou un rechargement des règles ; le
rapport en tient compte. Une unité installée avant cette version demande
seulement que son script soit recopié (la ligne `install` ci-dessus).
`refusal_watch_per_hour` dans `security.yml` vaut 0 à la livraison : le
chiffre reste une information tant que tu n'as pas vu le chiffre habituel
et fixé un seuil au-dessus.

Journaux (T3c) : une troisième unité, `aistack-host-logs`, compte ce que les
journaux de l'hôte disent de qui a essayé d'entrer, sur les dernières 24 heures
et par sorte de réseau (le LAN, le VPN, l'extérieur) : les connexions SSH
échouées, les paquets refusés et journalisés par `DOCKER-USER` et, quand Nginx
Proxy Manager garde ses journaux sur l'hôte, les requêtes par classe de statut
et par hôte virtuel, les sondes (`/.env`, `/.git` : personne d'autre qu'un
balayeur ne les demande) et les chemins d'application (`wp-login.php`,
`xmlrpc.php`), avec combien de chacun ont reçu une réponse de succès (2xx). Une
sonde qu'un hôte virtuel traite par un succès est un constat à surveiller quel
que soit le seuil (un hôte qui répond 200 à tous les chemins, une application
monopage, s'accepte par son nom dans `accepted_proxy_hosts`). Elle n'écrit que des comptes,
jamais une adresse, un chemin, un nom de compte ni une ligne de journal. On
l'installe comme l'hygiène de l'hôte :

```
sudo install -m 0755 src/aistack/host_logs.py /usr/local/sbin/aistack-host-logs
sudo cp deploy/host-logs/aistack-host-logs.service deploy/host-logs/aistack-host-logs.timer /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/aistack-host-logs.service.d
# host.conf : OUTPUT et ReadWritePaths (le dossier du relevé du pare-feu),
# AISTACK_LOGS_VPN (le réseau du VPN) et, avec un proxy sur l'hôte, AISTACK_LOGS_NPM
sudo systemctl daemon-reload && sudo systemctl enable --now aistack-host-logs.timer
```

Sur un autre hôte, la sortie est `/var/lib/aistack-hotes/<hôte>/security`,
comme pour l'hygiène. Les chiffres restent une information tant que tu n'as pas
fixé `ssh_failed_outside_watch` et `npm_scans_outside_watch` dans
`security.yml` au-dessus du chiffre habituel du rapport ; ensuite, le chiffre
venu de l'extérieur, ou d'une origine inconnue, est à surveiller. Une source de
journal illisible est un constat, pas un hôte tranquille.

Alertes (T4a) : la vigie lance l'évaluation à chaque passage (15 minutes) et
lit le rapport qu'elle vient d'écrire. Un constat **à corriger** ou **urgent**
est dit tout de suite sur Gotify (l'urgent sonne), une seule fois tant qu'il
dure ; un constat qui disparaît puis revient est redit. Les constats **à
surveiller** partent en un seul message par jour, à `digest_hour` (8) dans
`digest_timezone` (Europe/Paris), avec depuis combien de temps chacun dure, et
seulement s'il y en a ; un constat qui apparaît après cette heure attend le
lendemain. Le message du jour dit aussi si le rapport n'a pas été refait depuis
plus de trois heures. Le premier passage après la mise à jour note ce qui est
là sans rien dire.

Tes propres changements : `python -m aistack.cli.security_window --for 2h` ouvre
une **fenêtre de maintenance** (4 heures au plus, `window_max_hours`),
`--show` dit si elle est ouverte, `--end` la ferme ; elle se ferme seule et le
dit une fois. Pendant la fenêtre, la dérive des fichiers et des unités est
comptée mais pas dite, quelle que soit sa gravité sauf urgente ; le reste
(port ouvert, secret, connexions échouées, proxy) est dit comme d'habitude. Un
constat retenu ainsi est dit à la fin de la fenêtre s'il dure encore. Ouvertures
et fermetures sont notées dans `security-window.jsonl`. Sans effet sur aucun
hôte : une fausse alerte coûte un message, jamais une panne.

Séries : à chaque passage la vigie ajoute une ligne à `security-series.jsonl`
(constats par gravité et par domaine, ports, refus du pare-feu, tentatives SSH,
sondes et chemins d'application du proxy, dérive, mises à jour en attente) :
des comptes, jamais une adresse, un chemin ou un contenu. `series_days` (90)
fixe combien de jours sont gardés. Elles nourrissent les graphes de la page
Sécurité. Un rapport qui n'a pas été refait n'est pas
ajouté deux fois : un trou, pas une ligne plate. L'image doit être reconstruite
(`docker compose build && docker compose up -d`).

La page Sécurité (T4b) : la carte **Sécurité** de la console (réseau local
seulement) affiche une pastille quand un constat **à surveiller** ou pire dure
sans qu'une fenêtre de maintenance le retienne. Le chiffre les compte ; la
couleur est celle du pire (jaune à surveiller, orange à corriger, rouge
urgent) et son mot est écrit dans la pastille ; pas de pastille, rien à
regarder. La page `/security/` range les constats sous *Attaques possibles*
(journaux, refus, changements de fichiers et de services) et *Vulnérabilités*
(ports ouverts, conteneurs, mises à jour, images, droits des fichiers), dit les
sources que la surveillance n'a pas pu lire, tient la fenêtre de maintenance
(l'ouvrir de 30 minutes à 4 heures, ou la fermer, depuis la page) et dessine
des graphes sur 24 heures, 7 ou 30 jours. Un trou dans une courbe veut dire
qu'une source n'a pas été lue. Chaque constat a une fiche : ce que cela veut
dire, comment le vérifier avec des commandes de lecture, que faire en
général : un texte écrit à la main, le même pour tous. Sur ton clic, l'IA
**locale** (le modèle Ollama d'`ai_runtime.yml`, jamais Gemini) explique et
suggère ; elle ne reçoit que le titre, la gravité et quelques lignes de
preuve coupées, rien ne sort de ta machine, et rien de ce qu'elle dit n'est
jamais exécuté : relis une commande avant de la copier. La page demande de
reconstruire l'application web (`docker compose build && docker compose up -d`),
et la carte demande une entrée dans ton `config/console_links.yml` si tu en
gardes une copie.

L'application web, le seul service avec un port public, ne tient aucun
socket Docker : `docker-compose.yml` lui fait lire Docker par
`docker-proxy`, un proxy en lecture seule sur la boucle locale de l'hôte
(`127.0.0.1:2376` ; `AISTACK_DOCKER_PROXY_PORT` le déplace). Il refuse
toute écriture par une erreur 403. Les autres services gardent le socket ;
le rapport les liste sous `accepted`, et `aistack-docker-proxy` avec eux.
Qui lit le proxy voit encore les variables d'environnement de chaque
conteneur.

Une seconde unité fait de même, chaque heure, pour les paquets de l'hôte
et les droits des fichiers qui portent des secrets. Elle lit (`apt-get -s`
simule et ne change rien ; seuls le mode, le propriétaire et le groupe de
chaque fichier sont lus, jamais son contenu) et ne change rien :

```bash
sudo install -m 0755 src/aistack/host_hygiene.py /usr/local/sbin/aistack-host-hygiene
sudo cp deploy/host-hygiene/aistack-host-hygiene.service deploy/host-hygiene/aistack-host-hygiene.timer /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/aistack-host-hygiene.service.d
# host.conf : [Service], Environment=OUTPUT=<données>/security-host et ReadWritePaths=<le même>
sudo systemctl daemon-reload && sudo systemctl enable --now aistack-host-hygiene.timer
```

Une mise à jour de sécurité en attente, un redémarrage requis depuis plus de
`max_reboot_pending_days`, des listes de paquets plus vieilles que
`max_apt_age_days` et un fichier secret qu'un groupe peut lire sont des
constats à surveiller ; un fichier secret que n'importe quel utilisateur peut
lire est à corriger. `accepted_files` dans `security.yml` accepte un fichier
par son chemin.

Dérive (T3a) : le rapport lit aussi ce que les collecteurs d'hôtes d'`ADR-0020`
ont vu changer pendant les dernières `drift_window_hours` (24) sur chaque hôte
tracé. Un changement dans un chemin sensible (comptes, sudo, SSH, pare-feu,
VPN, onduleur, tunnel, `/usr/local`, tâches planifiées) ou une unité nouvellement
activée est à surveiller, sauf si un passage d'apt sur l'hôte l'explique ; la
file des imprimantes, l'horloge matérielle et les fichiers `*.dpkg-new` sont
comptés, et `accepted_drift` dans `security.yml` accepte les chemins que tu
changes volontairement. Le constat nomme le chemin et ce qui lui est arrivé,
jamais un contenu. Rien n'est installé pour cela.

Sur les autres hôtes, la même unité n'envoie rien toute seule : elle écrit
dans le dossier du collecteur de l'hôte, sous `security`
(`OUTPUT=/var/lib/aistack-hotes/<hôte>/security`, et le même chemin en
`ReadWritePaths`), et la poussée des relevés des hôtes (toutes les 15
minutes) l'amène à la MSI. Le rapport nomme alors chaque constat avec son
hôte. Un relevé de plus de 25 heures est écarté et le rapport le dit ; l'hôte
peut simplement être éteint. Un hôte sans dossier `security` n'est pas
signalé.

## Contrôles du démarrage

Après un redémarrage, tu lances toujours les mêmes contrôles à la main.
AIStack les reprend par tranches (`ADR-0032`) ; la première installe sur
l'hôte une petite unité qui écrit les faits que ces contrôles lisent : quand
l'hôte a démarré, les unités en échec, les systèmes de fichiers montés,
chaque conteneur avec son état et sa santé, les règles de `DOCKER-USER`, les
modules KVM, comment s'est terminée la période précédente, l'onduleur et le
statut HTTP des sondes que tu déclares. Elle écrit **des faits seulement**,
jamais un verdict, et aucune adresse, URL, nom d'utilisateur ni ligne de
journal ; une sonde est écrite sous son étiquette. Ses commandes forment une
liste fermée dans le script, aucune par un shell, et elle ne change rien sur
l'hôte. Les contrôles et l'indicateur du bandeau de santé viennent aux
tranches suivantes ; d'ici là, rien ne lit le fichier, donc installer l'unité
est sans effet.

```
sudo install -m 0755 src/aistack/boot_facts.py /usr/local/sbin/aistack-boot-facts
sudo cp deploy/boot-facts/aistack-boot-facts.service deploy/boot-facts/aistack-boot-facts.timer /etc/systemd/system/
sudo mkdir -p /etc/systemd/system/aistack-boot-facts.service.d
# host.conf : OUTPUT et ReadWritePaths (un dossier à lui, par ex. <données>/boot-host),
# et, si tu les veux, AISTACK_BOOT_UPS (le nom de l'onduleur pour upsc) et AISTACK_BOOT_PROBES (étiquette=url)
sudo systemctl daemon-reload && sudo systemctl enable --now aistack-boot-facts.timer
sudo systemctl start aistack-boot-facts.service && journalctl -u aistack-boot-facts -n 5
```

Une source illisible (Docker, le pare-feu, l'onduleur) le dit dans le fichier,
sous `sources` ; elle n'est jamais prise pour un hôte en bonne santé.

Les contrôles eux-mêmes sont lancés par `python -m aistack.cli.boot_check` (depuis
le dossier d'installation, avec l'utilisateur qui possède AIStack) : il lit les
faits, les juge d'après `boot_checks.yml` et écrit `boot-check.json` dans
`reports/generated`. Un contrôle pour lequel tu n'as rien déclaré est
*ignoré* et le dit ; celui dont la source n'a pas répondu est *inconnu* ;
aucun des deux n'est une réussite. Avant `settle_minutes` après le démarrage,
ce qui échoue est *en attente*, pas une anomalie. Le code de sortie dit
comment va le démarrage (0 bien, 1 à surveiller, 2 à corriger, 3 non jugé).
`--suggest` affiche ce que disent les faits sous forme de déclaration
(conteneurs, montages, règles `DOCKER-USER`, sondes) à copier dans ton
`boot_checks.yml` ; relis-la d'abord, car AIStack ne devine jamais ce qu'est un
démarrage sain.

**L'indicateur et la page.** La vigie lance ces contrôles à chaque passage
(toutes les 15 minutes). Dans le bandeau d'état de santé de la console, une
personne connectée voit une pastille de plus : *Démarrage : tout va bien
depuis 5 h 12* tant que chaque contrôle passe maintenant (le temps est compté
depuis le démarrage de l'hôte, et il est juste à chaque chargement), *en cours
de vérification* pendant les minutes d'attente, *n à surveiller* ou *n à
corriger* en orange ou en rouge quand des contrôles échouent, et *non jugé*
(gris) quand il n'y a pas de verdict, que les faits manquent ou que le dernier
contrôle est ancien : un vert qui n'est plus renouvelé n'est jamais affiché.
Elle ouvre l'écran **Contrôles du démarrage** (réseau local seulement) :
chaque contrôle et son résultat, les noms derrière (conteneurs absents, unités
en échec) et les incidents depuis le démarrage. Un incident résolu reste
listé, marqué *résolu*, jusqu'au prochain démarrage : une pastille verte ne
cache pas ce qui s'est passé. Sans session, la pastille garde son libellé
simple et ne dit rien de l'état. Rien n'est envoyé à Gotify à ce stade.

## En cas de problème

- **L'assistant d'installation répond « Ce lien n'ouvre pas l'assistant »** :
  il faut l'adresse avec le jeton ;
  `docker compose exec web python -m aistack.cli.setup_token` la réaffiche
  (`--new` en fait une nouvelle, `--reopen` rouvre un assistant terminé).
- **La vérification de l'adresse publique échoue depuis le serveur, mais
  l'adresse répond depuis un téléphone en 4G** : la box ne renvoie pas vers
  l'intérieur une adresse publique demandée de l'intérieur (NAT loopback) ;
  ce n'est pas bloquant.
- **« Invalid callback URL » chez le fournisseur** : l'adresse de retour de
  l'adresse utilisée n'est pas déclarée à l'identique sur le client.
- **« not allowed » chez le fournisseur** : ton compte n'est pas dans un
  groupe autorisé sur le client.
- **Profil Utilisateur au lieu d'Administrateur** : le groupe du fournisseur
  ne s'appelle pas exactement `aistack_admins`.
- **La connexion ne répond plus** : utilise le compte de secours sur le
  réseau local, puis consulte `journalctl -u aistack-web -n 50 --no-pager`.
- **Le Cockpit et la console n'affichent pas le même score** : régénère-les
  ensemble.
- **Une page de la Time Machine dit que le graphe n'existe pas** : lance
  `python -m aistack.cli.timemachine_rebuild`.
