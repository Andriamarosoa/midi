# Worker local MacBook Air M4

Ce runner déporte les calculs lourds vers un Mac Apple Silicon sur le même
réseau local. Il n'utilise aucun cloud, upload public, Kaggle ou Colab.

## Périmètre

- Mac : entraînements, smokes représentatifs, validations et inférences WAV
  hors ligne.
- Windows : orchestration, Git, contrôle des résultats et tout le live audio
  (MME/WASAPI/WDM-KS/FluidSynth). Le live ne traverse jamais le LAN.
- Données : uniquement le manifeste canonique de 572 prises train et 182
  validation. Le script refuse tout autre split et ne transfère aucun test.
- Un seul job lourd peut être actif. Il tourne sur le SSD du Mac, sous
  `caffeinate`, avec PID, logs et état terminal persistants.

## Préparation du Mac

Dans Réglages Système > Général > Partage, activer **Session à distance** pour
le compte choisi. Le Mac doit être sur secteur et disposer de Python 3.11
arm64. Le runner installe ensuite TensorFlow 2.15.1 et
`tensorflow-metal==1.1.0` dans un environnement dédié. Le capot doit rester
ouvert, sauf vraie configuration clamshell alimentée avec écran externe.

Depuis Windows, dans la branche propre du worker :

```powershell
.\MAC_WORKER.ps1 configure `
  -HostName <nom-ou-ip-du-mac> `
  -UserName <compte-macos> `
  -LocalWorkspaceRoot C:\Users\user\Desktop\midi

# Demande une seule fois le mot de passe macOS et installe une clé SSH locale.
.\MAC_WORKER.ps1 pair
.\MAC_WORKER.ps1 probe
```

Le fichier réel de configuration reste sous `tmp/local/mac_worker.json`, donc
hors Git. Aucun mot de passe n'y est stocké.

## Synchronisation Git

Le code est un commit Git propre. Le Mac conserve un checkout Git sous
`/Users/<user>/midi-worker/repository`; les jobs refusent de démarrer si son
`HEAD` ne correspond pas exactement au commit demandé. Cette voie évite toute
modification de fin de ligne par une archive Windows.

Après le commit et le push depuis Windows, initialiser une seule fois le Mac :

```bash
git clone <repo-url> /Users/<user>/midi-worker/repository
git -C /Users/<user>/midi-worker/repository switch --track origin/<branche>
cp /Users/<user>/midi-worker/repository/scripts/remote/mac_worker.sh /Users/<user>/midi-worker/bin/mac_worker.sh
chmod 700 /Users/<user>/midi-worker/bin/mac_worker.sh
```

Pour chaque nouveau commit de cette branche sur le Mac :

```bash
git -C /Users/<user>/midi-worker/repository pull --ff-only
cp /Users/<user>/midi-worker/repository/scripts/remote/mac_worker.sh /Users/<user>/midi-worker/bin/mac_worker.sh
chmod 700 /Users/<user>/midi-worker/bin/mac_worker.sh
```

Puis, depuis Windows :

```powershell
.\MAC_WORKER.ps1 bootstrap
.\MAC_WORKER.ps1 sync-data -DryRun
.\MAC_WORKER.ps1 sync-data
```

`sync-data` construit une liste blanche depuis
`manifest_train_validation.csv`. Le payload actuel contient 1 209 fichiers
audio/labels, plus le manifeste, pour environ 7,94 Gio. Il est copié une fois
sur le SSD local du Mac; aucun entraînement ne lit les données par SMB.

Un checkpoint d'initialisation est transfere separement, avec reprise SFTP,
taille et SHA-256 verifies avant renommage atomique :

```powershell
.\MAC_WORKER.ps1 sync-checkpoint `
  -Checkpoint runs\polyphonic\<run>\epochs\epoch-07.keras `
  -ConfigPath <chemin-vers-mac_worker.json>
```

## Gate neuronal anti-fausses-notes

Le premier calcul du nouveau head est strictement train-only, CPU-only et
borne. Depuis un worktree isole, fournir explicitement le vrai `-ConfigPath` :

```powershell
$gateArgs = @(
  "--config", "configs/polyphonic_dual_stream_bass_independent_note.yaml",
  "--initial-checkpoint", "/Users/<user>/midi-worker/checkpoints/<sha>.keras",
  "--output-dir", "tmp/independent-note-neural-train-gate",
  "--fit-examples", "8192",
  "--dev-examples", "2048",
  "--calibration-examples", "4096",
  "--epochs", "4",
  "--maximum-runtime-minutes", "60"
)

.\MAC_WORKER.ps1 start -JobId independent-note-neural-train-gate `
  -Device cpu -WallTimeoutSeconds 3900 `
  -Module src.polyphonic.smoke_neural_independent_note `
  -ModuleArgs $gateArgs -ConfigPath <chemin-vers-mac_worker.json>
```

Cette garde prouve seulement que le head apprend a distinguer les candidats
annotes `independent_note` et `harmonic_only`. Elle ne prouve pas encore une
baisse des faux `NoteOn`; cette preuve exige ensuite une comparaison appariee
du decodeur sur validation, jamais le test verrouille.

## Porte CPU contre Metal

Apple indique qu'un petit modèle ou un petit batch peut être plus rapide sur
CPU. Avant tout train complet, exécuter exactement le même smoke représentatif
sur les deux devices :

```powershell
$smokeArgs = @(
  "--config", "configs/polyphonic_dual_stream_bass_harmonic_presence.yaml",
  "--smoke-test",
  "--representative-smoke",
  "--smoke-examples", "8192",
  "--smoke-validation-examples", "2048",
  "--workers", "1",
  "--recovery-chunk-batches", "32",
  "--maximum-runtime-minutes", "60"
)

.\MAC_WORKER.ps1 start -JobId mac-smoke-cpu `
  -Device cpu -WallTimeoutSeconds 3900 `
  -Module src.polyphonic.train -ModuleArgs $smokeArgs
.\MAC_WORKER.ps1 status -JobId mac-smoke-cpu
.\MAC_WORKER.ps1 tail -JobId mac-smoke-cpu

# À lancer seulement après la fin terminale du smoke CPU.
.\MAC_WORKER.ps1 start -JobId mac-smoke-metal `
  -Device metal -WallTimeoutSeconds 3900 `
  -Module src.polyphonic.train -ModuleArgs $smokeArgs
```

Comparer débit, loss/F1, parité, RSS, pression mémoire/swap et température
soutenue. Les 16 Gio sont unifiés entre CPU, GPU et système; conserver
`workers=1`, queue 1 et recovery tous les 32 batches au premier train.

## Suivi et récupération

```powershell
.\MAC_WORKER.ps1 status -JobId <job>
.\MAC_WORKER.ps1 tail -JobId <job> -Lines 120
.\MAC_WORKER.ps1 stop -JobId <job>
.\MAC_WORKER.ps1 pull -JobId <job> `
  -RunPath runs/polyphonic/<run> `
  -Destination C:\Users\user\Desktop\midi\tmp\local\mac_results
```

`pull` rapatrie les logs, l'état et le run demandé, puis affiche le SHA-256 de
chaque fichier. Le wrapper rapporte `exited_zero` ou `exited_nonzero`; seul le
`training_status.json` du run peut déclarer `complete`, `early_stopped` ou
`paused_for_time_budget`. Un état périmé est signalé
`alive=false, stale=true`; il ne déclenche jamais de retry automatique.

## Limites de sécurité

- Le runner refuse un dépôt source sale et exige un SHA Git complet.
- Le préflight d'un train exige exactement 572 train, 182 validation et zéro
  test.
- Une recovery A/B Windows ne doit pas être reprise directement sur macOS.
  Utiliser d'abord un checkpoint comme initialisation et valider la parité;
  toute reprise inter-OS exige une expérience distincte autorisée.
- Le classifieur `harmonic_only_vs_independent_note` ayant échoué sa garde
  train-only n'est pas relancé par cette infrastructure.
