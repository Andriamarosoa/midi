# H27 - contrat de l'artefact d'autorite de creation du bundle

La revue externe de `c32c785cda2f8b23c3e788ee9cfffaa77d1745ec`
conclut `PASS`. Ce lot definit uniquement le schema ferme et le seal du futur
artefact distinct, single-use et explicitement revu qui pourra autoriser la
creation du bundle. Contrat, seal, binding, binding seal et 120 identites amont
forment 124 predecesseurs uniques.

Aucun artefact reel, bundle, observation, filesystem, registre, reservation,
consommation, invocation ou science n'est ouvert.

La premiere revue de `e2672ed94806318528d07da337cccb94034653bd`
a conclu `FAIL` uniquement parce que les six valeurs de chaine, les octets
canoniques de derivation de l'identifiant et les gardes HEAD/bundle n'etaient
pas tous normatifs et testes. La micro-correction les verrouille sans ouvrir
de nouvelle portee.

Identites exactes apres micro-correction :

- contrat : `12f7645d12f4198253e41cee0a1065aabf172da9` / `6121` octets /
  `dd030822581b9f68c1611b895aceb108cffc53cd4c413ca4144f2ce38932ee88` ;
- seal : `870ef976f50e8dad1a3d497aba3c58c04feb23be` / `1172` octets /
  `3f264fb306b88867ecef0f03931ee3d7a50e8c7f6655f8afe30d430285b01849`.

Validation locale sans calcul scientifique :

- test cible : `3/3` ;
- suite H27 : `403/403` ;
- `git diff --check` : attendu propre avant commit.
