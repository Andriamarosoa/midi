# H27 Review 4 — correction du loader figé et nouveau scellement

## Autorisation

Après l'arrêt pré-consommation archivé dans `c956d941...`, la revue externe a
rendu `PASS pour le correctif local — aucune reprise Mac encore`. Elle a exigé
deux commits : A pour le runner et ses tests, B pour son nouveau binding/seal.

## Commit A

`245ff1436ec6ecfbeb23b7aa962016dc098482b1` corrige uniquement
`frozen_module()` dans le runner de contrôle. Le module privé est désormais :

- refusé si son nom existe déjà dans `sys.modules`;
- inscrit avec l'identité exacte pendant `exec`;
- contrôlé contre un remplacement par le code exécuté;
- retiré dans `finally`, après succès comme après exception.

Les régressions couvrent le chargement réel d'une `dataclass`, l'absence après
succès, la collision intacte, le nettoyage après exception et le remplacement
malveillant de l'entrée.

Nouvelle identité du runner :

```text
size     26857
Git blob 6d7a4ade1abf7fd771a2d08d289ec976f8bba889
SHA-256  ae7d535943e7820ad4529579f99ca68d6e4009d344c15430de91fa0f32f99b8c
```

## Lot B

Le binding de composition référence exactement le commit A et la nouvelle
identité du runner. Son identité est :

```text
size     5955
Git blob cba1f35b3eab61e70f4ea342f4d906a16e61e32b
SHA-256  816ce4f2690b00ebdd0eda637c4a6bc6a7d25eb354076b6443659fb7c92ac33f
```

Le nouveau seal lie ce binding et le runner. Son identité est :

```text
size     1640
Git blob e7b1ce4ca927e10f7064449928130e403f84c9d9
SHA-256  0874fcafc3f515203f1db499c6806bf38e8c1e4448c806b7f46559cc8bb6afe0
```

Le matérialiseur reste strictement inchangé :

```text
size     33706
Git blob 8cdafbd6a08ea893daa2d6f41cb62166bf9162cd
SHA-256  2ecaabf1e1880688244b06ecb03a9b3eb7831d4659e209aa11e36b7b60948be3
```

## Validation locale

```text
Ran 15 tests in 0.354s
OK (skipped=1)
py_compile: PASS
git diff --check: PASS
```

Le skip est la régression POSIX de mutation staging, non exécutable sous
Windows; son contrôle d'ordre reste exécuté. Aucun SSH, ACK, fichier Mac,
runtime distant, authority, claim, population ou calcul scientifique n'a été
touché pendant ce correctif.

## Frontière

Les six anciens fichiers Mac restent intacts. Aucune reprise Mac n'est
autorisée par ce lot; A+B doivent recevoir une revue externe stricte. Une future
autorisation devra utiliser un nouveau répertoire immutable pour le runner et
ses deux nouveaux artefacts de composition, sans remplacer l'ancien bootstrap.
