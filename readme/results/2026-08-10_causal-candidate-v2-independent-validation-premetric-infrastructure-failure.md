# Échec d'infrastructure pré-métrique — validation indépendante V2

## Classification

`premetric_infrastructure_failure`

La tentative n'est pas une observation scientifique. La cohorte indépendante
n'a pas été consommée, mais l'autorisation one-job est définitivement consommée.
Aucun retry ni réutilisation de cette autorisation n'est permis.

## Provenance exacte

- Commit exécuté : `78f46628f430b9cdbe0e2b9ea042f05d0b141762`.
- SHA-256 de la demande one-job :
  `3145330a5bcd57cffb218914d3c545779ca54ce6634f716d49fae742dd922808`.
- SHA-256 de l'approbation externe :
  `5cda72a5f3dcc6f25534f0e633e3095af45bc26ffd1881ef75e5581f881c8612`.
- Job : `causal-candidate-v2-independent-cpu-20260810`.
- Device demandé : `cpu`.
- Timeout externe : `900 s`.
- Marqueur persistant :
  `tmp/local/causal_candidate_v2_independent_validation_one_job_20260810.claimed.json`.
- Taille du marqueur : `370` octets.
- SHA-256 du marqueur :
  `c0b544e2faed44df45985ccb9abfd13ed067966e907fe4f0f4c2bb83433225eb`.

Le marqueur est une preuve de consommation. Il doit rester présent et ne doit
jamais être supprimé, modifié ou réutilisé.

## Point d'arrêt observé

L'exécution a échoué immédiatement avec :

```text
RuntimeError: Fail closed: independent validation asset-evidence read is not authorized.
```

Le contrat d'exécution avait correctement autorisé l'usage du registre déjà
construit et scellé, mais le runner appelait encore le lecteur générique. Ce
lecteur reste intentionnellement fermé par le protocole scientifique historique
avec `reader_authorized_now=false`. L'autorité d'exécution et l'autorité
générique de construction/lecture sont deux capacités distinctes.

Après l'arrêt :

- destination scientifique absente ;
- verrou lourd absent ;
- aucun rapport final ou partiel ;
- aucun chargement TensorFlow scientifique ;
- aucun modèle ou checkpoint chargé ;
- aucun audio ou label ouvert ;
- aucune inférence, aucun décodage A/B et aucune métrique ;
- `locked_test_used=false`.

Donc :

```text
scientific_cohort_consumed = false
original_one_job_authorization_consumed = true
retry_original_authorization_allowed = false
```

## Correctif autorisé, sans calcul

Le correctif ajoute une capability d'évidence réservée à l'exécution, dérivée
par identité du contrat d'exécution scellé et du cohort scellé. Cette capability
lie sans valeur fournie par l'appelant :

- protocole fermé exact ;
- manifeste exact ;
- registre SHA-256
  `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee` ;
- protocole builder SHA-256
  `d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015` ;
- exactement `30` prises et `20` groupes indépendants.

La nouvelle voie relit uniquement le registre canonique au chemin scellé,
vérifie ses octets, sa provenance, ses clés ordonnées et les objets exacts du
snapshot, puis rehache les `30` audio et `30` labels avant de rendre une
capability validée. Les contrôles par prise juste avant ouverture restent
obligatoires. Le lecteur générique demeure fermé et son ancien échec reste testé.

Le correctif ne modifie ni le contrat d'exécution JSON, ni le protocole fermé,
ni le modèle, le standardiseur, le seuil, la cohorte ou les règles A/B. Il ne
crée aucun job, approval, marqueur ou nouvelle autorisation et n'exécute aucune
donnée réelle. Une nouvelle tentative distincte nécessiterait une nouvelle
préinscription, une nouvelle autorisation et une revue externe séparée.

Validation locale du correctif : `py_compile`, `70` tests synthétiques et de
provenance réussis en `17,089 s`, puis `git diff --check`. Les deux JSON scellés
du contrat d'exécution et du protocole fermé sont byte-identiques au parent
`78f46628f430b9cdbe0e2b9ea042f05d0b141762`.
