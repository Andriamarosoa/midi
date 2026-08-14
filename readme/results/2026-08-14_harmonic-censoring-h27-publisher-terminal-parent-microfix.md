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
| publisher terminal-parent | `2941c6938fded70057810b7ea7a2f4cc60b53b78` | 17188 | `ab2e7499fd87cb46261be3b70c38a549fc37880173320053260740df02132982` |
| binding parent terminal | `6f2f7cd32e05858a2ec79b7e44440d0155931b02` | 4380 | `06f72a9ea0b85d50af1236f99d43b03550410a9c31b31a63e91bbead6ff639ad` |
| seal externe | `af976aaa897c711871085ed08a6fa51bb17f4b09` | 1857 | `2618f315b430224a77b14f4d9c07b28f25ab9d640ae17837106427ce62ac95ad` |

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
