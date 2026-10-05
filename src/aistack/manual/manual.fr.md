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
- **l'adresse du réseau local** (par exemple `http://GIGABYTE:8186`) : tout ce
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

## Synchroniser le smartphone

*Réseau local, connexion requise, synchronisation réservée aux
administrateurs.* Choisir, dans la bibliothèque musicale, ce qui est copié
vers le téléphone :

- coche des répertoires dans l'arbre (la recherche et *Tout replier* /
  *Tout déplier* aident) ; un sous-répertoire d'un répertoire coché est
  inclus d'office ;
- la carte **Capacité** compare la sélection à la capacité déclarée et
  refuse une sélection trop grosse ;
- **Synchroniser avec le smartphone** applique la sélection dans le dossier
  cible ; Syncthing l'envoie ensuite au téléphone, dont l'avancement
  s'affiche quand l'appareil est déclaré.

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
surveillance CPU. Pour l'une d'elles :

1. **Commencer →** : un modèle d'IA local (Ollama) lit le constat et propose
   une explication et une prochaine étape — jamais une source de vérité ;
2. l'assistant guide pas à pas ; le lien **Besoin d'aide pour ouvrir un
   terminal ?** explique comment se connecter au serveur ;
3. pour la seule correction qu'AIStack sait appliquer d'un clic (déclarer un
   conteneur « au ralenti » dans les priorités CPU), **Appliquer** l'écrit,
   puis un nouveau diagnostic vérifie qu'elle a réellement agi.

Chaque raisonnement de l'IA est gardé dans l'historique du sujet.

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

Le détail des prérequis et des précautions est dans la section *How to
install* du README du dépôt. Dans l'ordre :

1. **Prérequis** : un hôte Linux avec systemd, Docker et Docker Compose,
   Python 3.13, git, un fournisseur OpenID Connect (Pocket ID) joignable en
   HTTPS, et un reverse proxy avec TLS pour l'adresse publique. En option :
   Ollama (l'IA), Syncthing (la musique), Beszel (les métriques).
2. **Le code** : cloner le dépôt dans `/srv/aistack`, créer l'environnement
   Python (`python3.13 -m venv .venv`, puis
   `.venv/bin/python -m pip install -e ".[dev]"`), et vérifier que
   `pytest -q` et `python -m aistack.cli.knowledge_integrity` passent.
3. **Les déclarations** : sous `src/aistack/*/definitions/` (avec Docker,
   dans `./config`, voir plus bas), au minimum le
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
10. **Passer en production** quand d'autres personnes utilisent AIStack :
    `phase: production` dans `instance_config.yml`, puis redémarrer
    `aistack-web`.

### Avec Docker

L'image Docker fait tourner AIStack lui-même : le
fichier `docker-compose.yml` du dépôt démarre l'application web et les
cinq collecteurs, six services d'une même image. Les prérequis, le
fournisseur d'identité et le reverse proxy sont les mêmes ; Python, git
et les unités systemd ne servent plus.

```
mkdir -p /srv/aistack && cd /srv/aistack
# y copier docker-compose.yml et .env.example depuis le dépôt
cp .env.example .env        # AISTACK_VERSION, tes identifiants d'utilisateur et de groupe, le groupe du socket Docker
mkdir -p config data
touch .env.web && chmod 600 .env.web
docker compose pull && docker compose up -d
```

Au premier démarrage, `./config` reçoit toutes les déclarations
qu'AIStack livre, avec les valeurs de l'hôte de référence. AIStack
démarre quand même, et **chaque page affiche « ⚠ À configurer »** en
haut : ce lien ouvre la page **Premier démarrage** (`/setup`), qui dit ce
qu'il reste à déclarer, dans quel fichier, et les valeurs utilisées
aujourd'hui :

1. **l'hôte et ses ports** — `./config/instance_config.yml` ;
2. **le fournisseur d'identité et l'adresse publique** —
   `./config/authentication.yml` ;
3. **le client OpenID Connect** — son identifiant et son secret dans
   `.env.web` ;
4. *recommandé* : **le compte de secours** —
   `docker compose exec web python -m aistack.cli.web_admin_password`,
   puis colle la ligne dans `.env.web`.

Après chaque modification, `docker compose restart`. Une déclaration
compte comme faite dès que son fichier a été modifié ; un fichier que tu
as déposé toi-même dans `./config` avant le premier démarrage n'est
jamais signalé. Quand tout l'indispensable est déclaré, le lien
disparaît.

Quand une nouvelle version change une déclaration livrée : une copie que
tu n'as jamais modifiée suit la nouvelle version au démarrage ; un
fichier que tu as modifié, ou déposé toi-même, n'est jamais touché, mais
**Paramètres → Déclarations livrées** montre la différence et la commande
qui prend la version livrée, jusqu'à ce que tu cliques « Vu, je garde mon
fichier ».

Chaque dossier de l'hôte que nomment tes déclarations (disques de
sauvegarde, musique) s'ajoute à la fin des `volumes:` de `x-aistack`,
au même chemin, en lecture seule.

## En cas de problème

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
