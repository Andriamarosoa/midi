# H27 — identity binding du contrat control-parent

La revue externe de `a07522cbac45097acb53e24f06b61bb2a6060ce0`
conclut `PASS` pour le contrat déclaratif control-parent et son seal exacts.

Le présent lot lie uniquement cinq identités byte-exactes :

1. contrat control-parent PASS : `a9b37b3081ad79b773f3a7291a508665d623307a` ;
2. external seal du contrat : `9edefaa15313be5d3a618b4b3ada012e14ef039b` ;
3. admin-root creator : `4fd4c77881f9801ec9d78494231a7c053b478da5` ;
4. binding du creator : `283312559e7c9a2cdfe52ed7102a7821ccb4e96b` ;
5. seal du binding : `696ca0c006202c63a1942b3da71078097b64c257`.

Le binding préserve exactement le parent `/Users/amcarene/h27-admin`, device
`16777233`, inode `1445438`, la future cible
`/Users/amcarene/h27-admin/control`, type directory, mode `0700`, ACK
`H27_CONTROL_PARENT_CREATE_EXECUTE=1` et les compteurs `3 / 4 / 7 / 15 / 7`.
Le graphe contient cinq chemins uniques, reste acyclique et sans
self/back-reference.

Identités byte-exactes du présent lot :

- binding : `4c84d7d62b177b23feef55a4cb4b2521212fc0ff`, `3531` octets,
  SHA-256 `f9e15642e6747bc4e2073c09c243c6999065fc5085a5e850d31b10e39dd86a36` ;
- external seal du binding : `2189` octets, SHA-256
  `1497c1f827d52468a915beea710267c231d10c57d47512b2233c53cc17bcb98a`.

Portée : binding, son external seal, test, README et présent rapport seulement.
Aucun runner, accès Mac, observation/création du parent control, ouverture ou
modification du registry, detach checkout, réservation/consommation, creator,
bundle, constructor/materializer, science ou locked-test.

État : `H27_CONTROL_PARENT_CREATION_CONTRACT_IDENTITY_BINDING_PENDING_EXTERNAL_REVIEW`.
