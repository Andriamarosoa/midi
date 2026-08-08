# Équipe Ollama locale sur Mac M4

## Objet

Mettre à disposition de Codex des conseillers locaux pour le brainstorming,
la recherche bornée aux sources fournies, les tests par lot, l'implémentation,
la revue de code, l'interprétation et l'orchestration, sans leur donner
d'autorité d'écriture, d'exécution, de publication ou d'ouverture du test
verrouillé.

## Provenance

- Branche : `codex/independent-note-neural-v2`.
- Commit d'implémentation exécuté :
  `6ae6d9d289678fef7c852358d2e17e695207ac75`.
- Correctif de sécurité et de contrat vérifié :
  `af5437eebc4a1e41aebb6e5db546aea669befd11`.
- Mac : Apple M4, 16 Gio de mémoire unifiée, macOS 15.5.
- Ollama : `0.32.6`.
- Modèles installés, sans téléchargement automatique : `qwen3:8b` Q4_K_M,
  `qwen3:14b` Q4_K_M et `qwen3.6:latest` 36B MoE Q4_K_M.
- Synchronisation du code : `git pull --ff-only` dans `~/midi`; checkout
  propre au commit exact ci-dessus.
- `locked_test_used=false`; aucun entraînement, export, live, classement ou
  sélection de seuil n'a été exécuté.

## Implémentation

- `OLLAMA_TEAM.ps1` fournit depuis Windows les actions `run`, `models`,
  `status` et `benchmark` via SSH.
- `scripts/local/ollama_team.py` appelle seulement l'API loopback du Mac et
  refuse tout endpoint LAN.
- Le commit Git distant doit être identique au commit local et les deux
  worktrees doivent être propres avant `run` ou `benchmark`.
- Les prompts sont transportés sur l'entrée standard SSH UTF-8, jamais dans
  les arguments du processus distant.
- Les contextes sont explicites, limités en taille et restreints aux fichiers
  texte du dépôt. Données, runs, checkpoints, secrets, audio, modèles et toute
  composante de chemin nommée comme test verrouillé sont refusés.
- L'accès HTTP désactive les proxies et refuse toute redirection ; l'URL
  initiale et l'URL finale doivent rester sur le loopback.
- Le routeur prend le même répertoire atomique
  `/Users/amcarene/midi-worker/active.lock` que le worker TensorFlow. Un appel
  Ollama et un job MIDI lourd ne peuvent donc pas démarrer en parallèle. Le
  verrou n'est libéré qu'après déchargement demandé puis absence du modèle
  confirmée par `/api/ps`; un échec conserve le verrou pour inspection.
- Les réponses locales restent consultatives. Elles ne modifient aucun fichier
  et ne remplacent ni les tests, ni les mesures, ni la revue finale.
- Les nouveaux rapports persistants ne contiennent plus le corps de la
  réponse : seulement son SHA-256 et son nombre de caractères.

## Validation

- Compilation réussie avec Python 3.9.
- Analyse syntaxique PowerShell réussie.
- Windows : 24 tests ciblés réussis, comprenant les 9 tests du routeur et les
  15 tests du contrat de transport Mac.
- Mac : 9 tests du routeur réussis après le `git pull` exact.
- Revue locale du diff complet par `qwen3:14b` : verdict `approve`, aucun
  constat; cette revue est une aide, pas une preuve autonome.
- Premier vrai appel par le wrapper : rôle `code_review`, modèle
  `qwen3:14b`, contexte
  `src/polyphonic/decoder_candidate_mining.py` SHA-256
  `29dd0129b6773bc866abafc7cfb24230f09d4626271ad7797833946b974b7b81`.
  Il a correctement classé ce module comme contrat encore isolé du décodeur de
  production. Mesures : 16,503 s murales, 770 tokens de prompt à
  102,47 tokens/s, 50 tokens générés à 11,70 tokens/s.
- Rapport local de cet appel :
  `/Users/amcarene/midi/tmp/local/ollama_team/20260808T201408808521Z_code_review_qwen3-14b.json`,
  SHA-256
  `a4e78ae8cda4d445c9fe4645f0486def898698a80f826e74498fe2ee45a103ff`.

Le rapport du premier appel et le rapport de benchmark ci-dessous ont été
produits avant le durcissement : le premier conservait la réponse complète et
le second des extraits. Ils restent des preuves historiques locales. Tous les
rapports créés à partir de `af5437ee` omettent désormais ces contenus.

## Validation du durcissement `af5437ee`

- Windows : 38 tests ciblés réussis, syntaxe Python, analyse PowerShell et
  `git diff --check` réussis.
- Mac au checkout propre exact : 23 tests Ollama/contrat candidat réussis.
- Un vrai appel `code_review` a traversé le wrapper durci avec les deux
  worktrees propres. Après l'appel, `active_lock=false` et
  `running_models=[]` confirment la libération de ressource attendue.
- Rapport persistant brut :
  `/Users/amcarene/midi/tmp/local/ollama_team/20260808T205831525138Z_code_review_qwen3-14b.json`,
  SHA-256
  `0da128ecd3c436aace1fcfe9de8ee2795b9fc14120880b46152ca08b45a1a2d6`.
  Il contient `response_sha256` et `response_characters=4150`, mais aucun champ
  `response`.
- La réponse 14B de ce contrôle était générique, ignorait le format demandé et
  inventait le chemin `src/ollama/ollama_cli.py`. Elle n'est donc pas retenue
  comme revue de code ni comme approbation ; les tests et la revue externe
  restent l'autorité.
- `locked_test_used=false`; aucun entraînement, calcul validation, export ou
  live n'a été exécuté.

## Benchmark séquentiel intégré

| Modèle | Mur | Chargement | Génération | Taille chargée | VRAM | Fin |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `qwen3:8b` | 7,679 s | 3,029 s | 20,44 tok/s | 5,19 Gio | 5,19 Gio | `stop` |
| `qwen3:14b` | 11,396 s | 3,953 s | 11,72 tok/s | 9,38 Gio | 9,38 Gio | `stop` |
| `qwen3.6:latest` | 68,064 s | 23,543 s | 3,19 tok/s | 21,48 Gio | 7,79 Gio | `stop` |

Rapport local :
`/Users/amcarene/midi/tmp/local/ollama_team/20260808T201551993379Z_benchmark.json`,
SHA-256
`fe73ea4bc7035e49c7dfbdc06701460d19fe72a0ed3babdbab090d1bae32de87`.

Le 36B dépasse les 16 Gio physiques et a laissé 676,62 Mio de swap chiffré
utilisé après le benchmark. Il est donc réservé aux secondes opinions rares;
le 14B est l'orchestrateur et conseiller principal, et le 8B traite les lots
rapides.

## Sécurité réseau

L'option Ollama `expose` était active. Elle a été remise à `0`, Ollama a été
redémarré et le listener vérifié est maintenant exclusivement
`127.0.0.1:11434`. Un appel direct depuis Windows vers l'adresse du Mac échoue,
tandis que le wrapper SSH continue de lister les trois modèles. Aucun mot de
passe, jeton ou contenu de données n'est versionné.

## Horloge du Mac

Les noms de rapports conservent l'horodatage brut du Mac. Mesure simultanée :

- Windows UTC : `2026-08-08T09:19:16.0691066Z`;
- Mac UTC brut : `2026-08-08T20:18:59Z`;
- avance du Mac : environ `39 582,931` secondes, soit 10 h 59 min 42,931 s.

Les heures brutes des artefacts ne doivent donc pas être interprétées comme
une chronologie UTC réelle sans cette correction.

## Limites et prochaine utilisation

- Ollama n'effectue pas de recherche web autonome. Une recherche externe doit
  fournir des sources actuelles et vérifiables avant synthèse locale.
- Un modèle peut proposer un patch ou un diagnostic erroné; Codex doit encore
  inspecter le code, exécuter les tests et vérifier les artefacts.
- Le contrat candidat a depuis été corrigé, mais le contrôle 14B a aussi montré
  qu'un modèle local peut ignorer une consigne précise. La prochaine porte est
  donc une revue ChatGPT du commit `af5437ee`; aucun minage, train ou calcul
  validation n'est lancé automatiquement par cette infrastructure.
