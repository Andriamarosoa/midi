# Correctif portable CRLF/LF du préflight de minage borné

## Anomalie constatée avant le replay

Après l'approbation externe de `9ed93e759ebda93f7915ee2ae2cae5ac1f86b346`,
le Mac a été synchronisé proprement sur ce commit. Le préflight manuel des
sept fichiers scellés s'est arrêté sans invoquer le CLI, TensorFlow, le
contexte, le checkpoint ou un actif audio/labels : la politique audio
versionnée ne possédait pas la même représentation d'octets sur les deux hôtes.

| Entrée | Attendu dans le protocole initial | Mac | Constat |
| --- | --- | --- | --- |
| manifeste | `b28cb17…` | identique | conforme |
| plan Policy A v2 | `a8347e4e…` | identique | conforme |
| registre d'actifs | `12dd74f2…` | identique | conforme |
| checkpoint | `1ce8ac44…` | identique | conforme |
| YAML modèle | `24528578…` | identique | conforme |
| décodeur référence | `c16be482…` | identique | conforme |
| politique audio | `bf4c731e…` | `45edbb71…` | divergence CRLF/LF |

La divergence est reproduite sans ambiguïté : le blob Git et le checkout Mac
ont le SHA `45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e`
(LF), tandis que le checkout Windows portait la même syntaxe JSON avec CRLF et
le SHA `bf4c731e9289bc88beaa85c87a7e19622f7cc4ec217de491c700a7282e0e0651c`.
Il ne s'agit ni d'une modification musicale, ni d'un actif différent.

## Correctif sans calcul scientifique

`.gitattributes` impose maintenant `text eol=lf` aux quatre fichiers versionnés
dont les octets sont scellés par le protocole : protocole lui-même, YAML modèle,
décodeur référence et politique audio. Le protocole utilise le SHA LF
canonique `45ed…` pour la politique audio. Les plans, registres, actifs et
checkpoints ne sont pas modifiés.

## Vérification locale

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest `
  tests.test_mine_decoder_candidates `
  tests.test_decoder_candidate_labels `
  tests.test_decoder_candidate_mining `
  tests.test_decoder_candidate_snapshot_protocol `
  tests.test_decoder_candidate_asset_evidence
```

Résultat : **42 tests réussis en 1,721 s**; `py_compile` et
`git diff --check` réussissent. Le nouveau test vérifie le SHA LF canonique du
protocole et l'attribut Git explicite de la politique audio.

## Porte suivante

Ce correctif nécessite une revue externe avant toute nouvelle synchronisation
Mac. Après approbation, le même préflight doit confirmer les sept SHA, le
worktree propre, l'absence de verrou et le répertoire de sortie inexistant,
puis une unique passe CPU train-only de 12 prises peut démarrer. Aucun fit,
calibration, validation, export, live ou test verrouillé n'est autorisé.
