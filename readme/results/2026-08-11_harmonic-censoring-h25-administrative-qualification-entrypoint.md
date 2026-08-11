# H25 — correction de l'entrypoint de qualification administrative

## Portée

Après approbation du harness real-OS au commit
`a2cbed888e4ec1d8598411ae1491c38baa628d66`, une unique tentative de
qualification administrative a été préparée sur un worktree Mac détaché et
séparé du checkout scientifique H24.

Le préflight avait confirmé :

```text
HEAD H25       a2cbed888e4ec1d8598411ae1491c38baa628d66
contrat SHA    a50189acc47c1999935212e8549403992a663dee316fa3e88812eca159043fd4
worktree       propre
destination    absente
workers H25    0
checkout H24   4d31fa333683f83f2a35117ab5597faf1a7784a6, inchangé
```

## Anomalie pré-entrypoint

La commande suivante a été lancée une seule fois :

```text
/Users/amcarene/midi-worker/.venv/bin/python \
  tmp/local/h25_admin_lifecycle_qualification_driver.py
```

Elle a quitté avec le code `1` avant `main()` :

```text
ModuleNotFoundError:
No module named 'src.polyphonic.harmonic_censoring_h25_lifecycle_qualification'
```

L'exécution d'un fichier par son chemin place son répertoire `tmp/local` en
tête de `sys.path`, pas la racine du dépôt. Le module demandé existait bien
dans Git et sur disque. Aucun répertoire de qualification n'a été créé,
`0/13` probes OS et `0/6` cas administratifs ont été exécutés, aucun surrogate
claim n'a été créé ou consommé et aucun worker n'est resté vivant.

Le pilote externe a rendu le verdict :

```text
CONFIRMED_H25_ADMINISTRATIVE_QUALIFICATION_LAUNCH_PREENTRY_FAILURE
NON_CONSUMING
```

Il a autorisé uniquement la correction et le commit de l'entrypoint, sans
nouvelle exécution de qualification.

## Correction

Le driver devient un module suivi :

```text
src.polyphonic.run_h25_preclaim_admin_lifecycle_qualification

src/polyphonic/run_h25_preclaim_admin_lifecycle_qualification.py
15286 octets
SHA-256 7112991f67b4a91ae5d17f89e1c5a32db3a1b7013b1b5d98c447df6862e1b20e

tests/test_h25_admin_qualification_entrypoint.py
4701 octets
SHA-256 b3269f93276df437eb27e71f2e44b8f1b7172b2932caa4bfe48f424d1b701023
```

La seule forme d'exécution prévue est désormais :

```bash
H25_ADMIN_LIFECYCLE_QUALIFICATION_EXECUTE=1 \
H25_ADMIN_LIFECYCLE_QUALIFICATION_EXPECTED_COMMIT=<SHA-40-revu> \
python -m src.polyphonic.run_h25_preclaim_admin_lifecycle_qualification
```

L'entrypoint refuse avant Git et avant toute création de sortie :

- l'absence de l'acknowledgement littéral `1` ;
- un SHA attendu absent, abrégé, non hexadécimal ou non minuscule ;
- un HEAD différent du SHA complet fourni ;
- un worktree sale ;
- un contrat dont le SHA diffère ;
- tout argument de commande inattendu.

Un contrôle d'import sans exécution est disponible uniquement sous :

```bash
python -m src.polyphonic.run_h25_preclaim_admin_lifecycle_qualification \
  --entrypoint-check
```

Il refuse la présence de l'acknowledgement d'exécution, ne lance aucune sonde
et ne crée aucun namespace.

## Tests zéro-exécution

```text
python -m py_compile \
  src/polyphonic/run_h25_preclaim_admin_lifecycle_qualification.py \
  tests/test_h25_admin_qualification_entrypoint.py

python -m unittest tests.test_h25_admin_qualification_entrypoint -v

5 tests réussis en 0,425 s
```

Ces tests couvrent réellement l'invocation `python -m`, le refus de
l'acknowledgement en mode contrôle, les deux gardes d'autorité avant Git et le
rejet des arguments inconnus. Ils vérifient que l'état de la destination reste
strictement inchangé.

## Frontière maintenue

Aucune qualification enregistrée, aucun surrogate claim, aucune capability ou
claim scientifique H25, population, waveform, NumPy scientifique, P0/P1/P2
scientifique, donnée réelle, H17, locked-test, modèle, checkpoint, calibration
ou entraînement n'a été utilisé.

La prochaine action est uniquement la revue externe de ce correctif
d'entrypoint. Une nouvelle exécution administrative reste interdite sans une
autorisation séparée sur le commit exact revu.
