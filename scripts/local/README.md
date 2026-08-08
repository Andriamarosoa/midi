# Equipe Ollama locale

`ollama_team.py` utilise les modeles Ollama installes sur le Mac comme
conseillers locaux. Il ne modifie jamais Git et ne remplace ni les tests reels,
ni les mesures, ni la decision de Codex/utilisateur.

Depuis Windows, apres commit/push puis `git pull --ff-only` dans `~/midi` :

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

Le script refuse un modele absent au lieu de le telecharger. Les contextes
doivent etre des fichiers texte explicites du depot ; `.git`, donnees,
checkpoints, runs, secrets, audio et modeles sont bloques. Le prompt complet
n'est pas conserve : seul son SHA-256 l'est. Les rapports locaux vont sous
`tmp/local/ollama_team`, donc hors Git.

Le routeur prend le meme verrou atomique `~/midi-worker/active.lock` que le
worker TensorFlow. Un job Ollama et un calcul MIDI lourd ne peuvent donc pas
demarrer en parallele. Si un processus est tue brutalement, verifier le PID et
le proprietaire avant tout nettoyage manuel du verrou.
