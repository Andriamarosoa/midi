# H27 — identity binding du contrat de racine administrative

Date : 2026-08-14

## Portee

Ce lot ajoute uniquement l'identity binding du contrat PASS de creation future
de `/Users/amcarene/h27-admin`, son external seal, un test, cette preuve et la
mise a jour du journal.

Aucun runner, acces Mac, observation ou creation filesystem n'a lieu.

## Liaison

Le binding rehache exactement cinq paths uniques :

```text
contract PASS corrige
contract external seal
publisher PASS
publisher identity binding
publisher identity binding external seal
```

Il preserve :

- `H27_ADMIN_ROOT_CREATE_EXECUTE=1` et aucun argument ;
- `/Users/amcarene` → leaf `h27-admin` ;
- les sept exigences fermees du futur runner ;
- tous les etats runtime/filesystem/science a faux.

## Identites

```text
identity binding
4ecb86e7e14e80ee276c6b9a8ca300de2981e127
3541 octets
1efcd187908ae791bb8740e659cc327b11c31f56af194bafffb8e498adeab0c9

external seal
7c0c8ee64f4f684c1aff63b1c37089d720d19f29
1282 octets
d1d4c3f5d47d6585cd85578b20580e29386667b9397fcb1b96681cb34128d302
```

## Etat

Etat : `IDENTITY_BINDING_ONLY_PENDING_EXTERNAL_REVIEW`.

La prochaine action autorisee est uniquement la revue externe de ce binding et
de son seal. Runner et creation reelle restent interdits.
