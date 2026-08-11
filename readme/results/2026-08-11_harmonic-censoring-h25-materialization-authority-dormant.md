# H25 — autorité one-shot de matérialisation dormante

Le contrat lie le materializer approuvé au commit `0036853f…`, son blob Git et
les cinq contrats/manifests H25. L’issuer exige un futur seal et un binding OS
qui n’existent pas dans ce commit : aucune capability ne peut donc être émise.

Le futur wrapper ne retourne jamais la capability brute. Son état passe sous
lock de `ISSUED` à `CONSUMED_BEFORE_DELEGATION` avant l’appel du materializer ;
copie, deepcopy, sérialisation, reset, retry et seconde exécution sont interdits.

Aucune authority/capability n’a été émise ou consommée et aucune population,
waveform, phase scientifique, donnée réelle ou locked-test n’a été utilisée.
