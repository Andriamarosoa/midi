# H27 — micro-correction dormante du parent publisher

## Portée

La preuve terminale creator-leaf au commit
`81acfa74ea9b6007bed3d02ce1ac7eec9d6a5ef9` est revue `PASS`. Ce lot modifie
uniquement la voie publisher dormante en ajoutant une nouvelle version du
publisher. Le publisher PASS historique reste byte-identique sous son path
d'origine. Le lot ajoute aussi le nouveau binding de parent terminal, son seal
externe, adapte le test, puis met à jour README et rapport.

Aucune publication, observation des roots final/staging, exécution du creator,
réservation/consommation de registre, bundle, science ou locked-test n'a lieu.

## Durcissement exact

Le parent publisher reste `/Users/amcarene/h27-admin/creator`, mais les deux
vérifications suivantes sont maintenant obligatoires :

```text
fd parent       = (device 16777233, inode 1447071)
entrée nommée   = (device 16777233, inode 1447071)
```

Le tuple est exigé lors de l'ouverture `O_NOFOLLOW`, donc avant toute
observation final/staging. Il est revalidé immédiatement avant la création du
staging — premier effet irréversible — et avant le succès terminal.

Tous les anciens invariants du publisher sont conservés : 139 identités Git,
dirfd stable, probes relatifs, écritures exclusives/no-follow, fermeture du set
de fichiers, `renameatx_np(..., RENAME_EXCL)`, fsync, aucun cleanup/retry/repair.

## Identités

| Objet | Git blob | Octets | SHA-256 brut |
|---|---:|---:|---:|
| publisher terminal-parent | `60287a98eb0a7ff227bfcff49e72935b4a40dafc` | 17187 | `c84a64767a2cf3912ae8aaca0d74accc634b1219b202825a74a36d0c72481859` |
| binding parent terminal | `7ae682b72594832a2a72b484b1e8dff2e4b30152` | 4380 | `9691a3aa1cb82b02fd113c62e2acc96f197b3c05412d27f3c21dae7e5b0a4830` |
| seal externe | `c852b08cbdaf2992cb87a8b454b8fcae3ef62a37` | 1857 | `57f0d4e360397591381e836b09378a874be94e6eec9aeff630f9bd466b7451bb` |

Le binding conserve les trois identités du publisher PASS précédent et lie la
preuve terminale creator-leaf revue PASS. Il ferme aussi les dictionnaires
exacts d'exécution, safeguards, autorités et états dormants.

## Validation locale

```text
python -m py_compile scripts/h27_publish_reviewed_creator_source_terminal_parent_one_shot.py
python -B -m unittest tests.test_harmonic_censoring_h27_reviewed_creator_source_publisher
....
Ran 4 tests
OK
python -B -m unittest discover -s tests -p 'test_harmonic_censoring_h27*.py'
Ran 452 tests
OK
```

Le test revalide les 139 blobs Git, la chaîne publisher historique, la preuve
creator-leaf, l'ordre dirfd et le refus dynamique d'un inode parent substitué.

## État

Le publisher n'a pas été exécuté. Son autorisation reste non consommée. La
seule prochaine action est la revue externe du publisher exact, du nouveau
binding et de son seal. Aucune tentative de publication n'est autorisée avant
un `PASS` explicite.
