# H16 — durcissement futur de la provenance opérationnelle

## Portée

H16 est une modification d'infrastructure pour de futurs runners uniquement.
Elle ne corrige pas rétroactivement H14, ne rouvre pas H8 et n'autorise aucune
nouvelle expérience.

## Phases persistées

Avant chaque phase majeure, l'orchestrateur écrit atomiquement un petit JSON :

```text
opening
inference
decoder
target
reconciliation
metrics
publication
```

Pour une phase liée à une prise, seuls l'index et la clé d'enregistrement sont
ajoutés. Les phases globales conservent ces champs à `null`.

## Provenance d'échec future

Le rapport fail-closed conserve désormais :

- phase courante ;
- type d'exception ;
- message sur une ligne, limité à `512` caractères ;
- message entièrement remplacé si un vocabulaire scientifique sensible est
  détecté ;
- au plus `32` emplacements de pile avec seulement nom de fichier, fonction et
  numéro de ligne ;
- index et clé de prise lorsque la phase en possède ;
- état de consommation et SHA du contrat.

La pile ne contient ni ligne source, ni variable locale, ni valeur. Le state de
consommation, la phase et le rapport d'échec utilisent tous un remplacement JSON
atomique afin de ne pas exposer de fichier partiel.

## Interdictions de journalisation

La provenance ne doit contenir aucun S0/S1/D1, target, classe, équilibre de
classes, probabilité, score, AUC, résultat bootstrap ou intermédiaire
scientifique. Le test synthétique force un message
`S1=0.91 target=1 AUC=0.88` et vérifie qu'aucun de ces termes/valeurs ne survit
dans le JSON persistant.

## Validation synthétique

Les tests couvrent :

- ordre exact des cinq phases par prise ;
- passage global à `metrics`, puis `publication` ;
- phase `inference` et identité de la première prise lors d'un échec synthétique ;
- redaction du message scientifique ;
- pile bornée et fermée aux seuls champs `file/function/line` ;
- publication atomique toujours conditionnée au succès complet ;
- claim, consommation et absence de retry inchangés.

`71` tests H7–H13 ont réussi en `18,384 s`. La suite H11–H13 ciblée avait
auparavant réussi `32` tests en `7,544 s`. `py_compile` et `git diff --check`
ont également réussi.

Empreintes de travail avant commit :

- orchestrateur H11/H16 : `80d7d17361a69203526dc40f79a9b2659dfc916d`;
- tests synthétiques : `e9891e70b1ae9b63a3c09967023851cc085d8b00`.

## État scientifique

```text
scientific execution authorized  false
real runner invoked              false
H8 opened                        false
model loaded                     false
inference run                    false
scientific metric computed       false
locked test used                 false
H14/H8 retry authorized          false
```

Les contrats scellés H12/H13 conservent volontairement leur liaison à
l'ancien blob H11. H16 ne les met pas à jour et ne les rend pas exécutables :
un futur runner devra disposer d'un nouveau contrat de liaison, préenregistré
et revu séparément.
