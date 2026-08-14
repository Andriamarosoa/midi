# H27 - contrat de source immutable du creator du control bundle

La revue externe de `53335c83dffc7551e3f0e2f3236503ef92970599`
conclut `PASS`. Ce lot definit uniquement le contrat et le seal de la future
source immutable du creator, sans creer ni observer cette source.

La racine finale est fixee a
`/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1`.
Le source ferme contiendra exactement l'entrypoint
`h27_reviewed_control_bundle_creator.py` et `manifest.json`. Les quatre
identites creator revues et les 130 identites amont forment 134 paths uniques
qui devront tous etre rehashes avant toute observation de la racine.

La publication future reste distincte : sept controles statiques, neuf etapes
de publication atomique sans overwrite et douze regles fail-closed. L'identite
exacte du futur entrypoint devra provenir d'un commit ulterieur distinct,
reviewed PASS et scelle ; aucun placeholder ou fallback vers le checkout
courant n'est permis.

Identites exactes :

- contrat : `08a75b332320fce18e13b5bdb2ae201f6dc821bd` / `7535` octets /
  `200242f8058c810dc335c8e6cbbaa937b936d572c553eb68cb7960d275808821` ;
- seal : `608303627999107f5f41ab2117d2cf32344aac11` / `1401` octets /
  `7632b7d0a1ebeb2e1dcbf608520b1da8df80adc8f92ab62e9cdeca1f4ac484c7`.

Aucune implementation, racine, registre, reservation, consommation, bundle,
operation filesystem ou science n'a ete ouverte.

Validation locale sans calcul scientifique : test cible `3/3`, suite H27
`421/421`, puis `git diff --check` propre avant commit.
