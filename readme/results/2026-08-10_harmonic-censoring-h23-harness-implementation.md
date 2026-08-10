# H23 — implémentation pure du resolver/materializer

## Portée

Cette étape implémente uniquement la frontière déterministe autorisée par la
revue externe de `1e5075f5d9eb23bdab077bed3faeb6c58c61942e`.

Elle ne synthétise aucune forme d'onde, n'exécute aucun test P0/P1/P2, n'ouvre
aucun audio ou label projet, ne charge aucun checkpoint ou modèle et ne réalise
aucun fit ou calibrage. H17 et le test verrouillé restent fermés.

## Implémentation

Le nouveau module `src/polyphonic/harmonic_censoring_h23.py` :

- exige le chemin canonique du contrat et son SHA-256 brut
  `719eba0aa440fc1e77ae7d204adee9e5b51517f455fad3bfed7e761d3c00a74a` ;
- refuse CRLF, clé JSON dupliquée et nombre JSON non fini ;
- vérifie l'identité du contrat, la revue externe et les drapeaux
  implementation-only ;
- vérifie les trois domaines `24..76`, `40..76`, `40..128`, la matrice
  `37 × 6`, le timeline causal et le schéma d'état exact ;
- développe les six bases et les 17 familles one-factor-at-a-time en exactement
  `175` spécifications uniques ;
- dérive chaque seed par les huit premiers octets little-endian de
  `SHA256(UTF8("H23|" + fixture_id))` ;
- conserve dans chaque spec le transform waveform, le target/oracle résolu et
  le SHA du contrat, puis calcule son SHA-256 canonique ;
- résout les 72 entrées du catalogue avec tous les champs hérités, dans l'ordre
  exact `P0=27`, `P1=35`, `P2=10` ;
- produit en mémoire deux manifests canoniques explicitement non exécutés ;
- expose une garde qui refuse toute exécution tant que l'autorisation du
  contrat et celle de la revue ne sont pas toutes deux vraies.

Le contrat est aussi forcé en LF dans `.gitattributes`.

## Identités déterministes obtenues sans science

La simple résolution contractuelle en mémoire donne :

```text
fixtures                           175
tests                               72
fixture manifest SHA-256
acfa37b987deb19884c9f60cf3410717b68788eb466396402aaf992b3224e19c
resolved-test manifest SHA-256
0d059d3f2540f2b08279bb8363e9036ae0f71b2bea11575bfebfce76b7fe7504
```

Ces deux manifests n'ont pas été publiés comme artefacts scientifiques. Ils
portent respectivement `waveforms_synthesized=false` et
`tests_executed=false`.

## Vérification non scientifique

Commande ciblée :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest tests.test_harmonic_censoring_h23_harness
```

Résultat initial :

```text
8 tests réussis en 0,022 s
```

Les tests vérifient uniquement les octets/structures du contrat, les comptes,
l'ordre, les IDs, seeds, hashes, quelques targets résolus, le déterminisme des
manifests et le refus de toute exécution. Les fichiers temporaires de test sont
des copies textuelles du contrat ; aucune fixture audio n'est créée.

La vérification finale élargie aux contrats H17/H20 historiques donne `25`
tests réussis en `0,352 s`; `py_compile` et `git diff --check` réussissent aussi.

## État et prochaine porte

```text
implementation_authorized             true
synthetic_execution_authorized         false
reviewed synthetic execution           false
scientific_execution_authorized        false
real_data_access_authorized            false
training_authorized                    false
real_data_used                         false
H17_population_used                    false
locked_test_used                       false
fit_performed                          false
```

La prochaine étape est uniquement la revue externe de ce commit. Même après
approbation du code, la synthèse effective des 175 fixtures et l'exécution P0
exigeront un contrat d'exécution séparé : cette implémentation ne les autorise
pas.
