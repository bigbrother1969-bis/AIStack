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

Le code d'AIStack qui ne sert plus passe d'abord par une **quarantaine**
(`OPS-0012`) avant d'être effacé : il reste en place six semaines, et toute
utilisation est enregistrée. Tant qu'elle n'est pas vide, la quarantaine
compte dans la dette technique (15 points, une fois) ; une ligne de la
carte dit combien d'éléments elle contient, la date de révision et le
nombre d'utilisations constatées, et nomme ceux qui ont servi ou sont prêts
à effacer. Le détail : `python -m aistack.cli.quarantine_report` (avec
Docker : `docker compose exec web python -m aistack.cli.quarantine_report`).

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
viennent de quatre sources importées (messages de commit, commentaires des
tests de restauration, réponses de l'IA, notes de session) et des
administrateurs.

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
   `pytest -q` et `python -m aistack.cli.knowledge_integrity` passent.
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
