# H27 - contrat du gate one-shot du constructeur

La revue externe de `5a0b8d3d3f301ed4357bd1853af778bd6794f406`
conclut `PASS`. Ce lot definit uniquement le contrat declaratif et le seal
externe du futur gate one-shot qui pourra consommer l'artefact d'autorite et
invoquer le constructeur deja scelle.

La chaine lie artefact, seal, binding, binding seal et 112 identites amont,
soit 116 chemins uniques a rehasher. L'ordre futur est ferme : artefact exact,
HEAD attendu, worktree propre, rehash116, registre, reservation, consommation
atomique, puis invocation unique. `single_use=true` et `consumed=false` restent
inchanges dans ce lot.

La premiere revue de `18ee84e2fd4edba39681effc315d9f5762f132fd`
conclut `FAIL` : le checkout propre au HEAD `46a6bdf8...` ne contient pas les
quatre fichiers d'autorite crees ensuite. La micro-correction separe donc le
checkout cible exact `/Users/amcarene/midi-worker/repository` du bundle de
controle administratif immuable exact
`/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1`. Les 112
predecesseurs et le constructor proviennent du checkout cible; gate, seal et
les quatre fichiers de chaine d'autorite proviennent uniquement du bundle de
controle. Toute selection implicite est interdite et la creation de ce bundle
reste soumise a un contrat/revue/autorisation futurs distincts.

Aucun registre n'est ouvert, aucune identite/nonce n'est reservee, aucune
autorite n'est consommee et aucune invocation, destination, ecriture filesystem,
population ou science n'a lieu.

Contrat corrige exact : blob `1bdc95411520793c2f1ff0c08ef2245e569ef2a0`,
`6387` octets, SHA-256
`0134f4c459ac9d4e642da70dbcf257f34998db064e568ea0e039b58d5952f215`.
Seal corrige exact : blob `099703d92d9cfd761f5aa9065467fff1516d5a46`, `1673`
octets, SHA-256
`6cd9cc7f67c60ea71804fd01137ee2fddd1947c0fb0e56d3bc7d0db362054778`.

Validation locale : `3/3` tests administratifs cibles, `391/391` tests H27 et
`git diff --check` sans anomalie.
