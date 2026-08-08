# Equipe Ollama locale

`ollama_team.py` utilise les modeles Ollama installes sur le Mac comme
conseillers locaux. Il ne modifie jamais Git et ne remplace ni les tests reels,
ni les mesures, ni la decision de Codex/utilisateur.

Depuis Windows, après commit/push puis `git pull --ff-only` dans `~/midi` :

```powershell
.\OLLAMA_TEAM.ps1 models

.\OLLAMA_TEAM.ps1 run `
  -Role code_review `
  -Prompt "Relis le contrat de minage et liste uniquement les bugs concrets." `
  -ContextFile "src/polyphonic/decoder_candidate_mining.py"

.\OLLAMA_TEAM.ps1 benchmark
```

Routage par defaut :

- `qwen3:8b` : lots et tests rapides ;
- `qwen3:14b` : implementation, recherche locale, orchestration, revue et
  interpretation ;
- `qwen3.6:latest` : seconde revue rare et juge qualitatif.

Le script refuse un modèle absent au lieu de le télécharger. `run` et
`benchmark` exigent le même commit exact et un worktree propre sur Windows et
sur le Mac. Le prompt traverse SSH par l'entrée standard UTF-8, jamais dans la
ligne de commande distante. Les contextes doivent être des fichiers texte
explicites du dépôt ; `.git`, données, checkpoints, runs, secrets, audio,
modèles et tout composant de chemin nommé comme test verrouillé sont bloqués.

L'API est obligatoirement HTTP loopback, sans proxy ni redirection. Les
rapports persistants sous `tmp/local/ollama_team` ne conservent ni prompt ni
réponse en clair : seulement leurs empreintes, les tailles, les métriques et
la provenance des contextes. La réponse reste affichée au terminal pour
l'utilisateur qui a demandé l'avis.

Le routeur prend le même verrou atomique `~/midi-worker/active.lock` que le
worker TensorFlow. Avant de libérer ce verrou, il demande le déchargement du
modèle et vérifie via `/api/ps` que celui-ci n'est plus résident. Si cette
preuve échoue, le verrou est volontairement conservé avec
`requires_manual_inspection=true`; aucun calcul MIDI lourd ne doit alors être
relancé avant inspection. Si un processus est tué brutalement, vérifier le PID,
le propriétaire et les modèles résidents avant tout nettoyage manuel.
