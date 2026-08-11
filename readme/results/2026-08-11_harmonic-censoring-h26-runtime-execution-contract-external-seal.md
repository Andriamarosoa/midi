# Seal externe du contrat d'exécution runtime H26

Date : 2026-08-11

## Objet

Cette étape établit uniquement l'identité SHA-256 externe du contrat
d'exécution runtime H26 approuvé. Le seal est déclaratif, ne contient pas son
propre SHA et ne crée aucune authority, claim, capability, preuve d'entrée,
receipt ou autorisation d'exécution.

## Identités scellées

```text
execution contract commit
e0e070b8b75e85fb8ef78c7d6950a13f2c69ceae

execution contract Git blob
5ab6ff43980c0dc0f32308d3f8cee14a90351ec7

exact Git blob byte length
24080

execution contract raw SHA256
c7f6da697d74f710b957ab7ad32bef0fc184bb4f16ffaef16d2e2e1abafc63f9

approved primitives commit
48d3e6015a2adaded0b27769271ebb8d70ddb98a

approved primitives Git blob
9c347a6c9fe081e0d2ac963311ea766eb5fc62f9
```

Le SHA-256 a été calculé sur les octets exacts retournés par :

```text
git cat-file blob 5ab6ff43980c0dc0f32308d3f8cee14a90351ec7
```

Le checkout de travail n'est donc pas la source du hash et une conversion
CRLF locale ne peut pas modifier cette identité.

## Frontière

Tous les états opérationnels restent `false` ou `null`. Aucun issuer,
authority, claim, slot filesystem, marker, evidence, receipt, observer,
runtime record, NumPy, BLAS, `otool`, waveform, matérialisation, P0/P1/P2,
modèle, entraînement, calibration ou locked-test n'a été créé ou exécuté.

La prochaine étape est une revue externe de ces trois fichiers déclaratifs.
Toute construction ou émission d'un artefact d'exécution exige une autorisation
séparée.
