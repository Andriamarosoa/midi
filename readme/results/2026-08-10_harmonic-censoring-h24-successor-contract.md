# H24 — contrat successeur après la clôture terminale H23

## Autorisation

La revue externe du commit documentaire terminal `2b2d4ee2…` approuve
l’archivage H23 et autorise uniquement la définition d’un successeur distinct,
sans implémentation ni calcul :

```text
AUTHORIZED_TO_DEFINE_H23_SUCCESSOR_CONTRACT_ONLY
```

H23 reste définitivement clos avec
`H23_SYNTHETIC_HYPOTHESIS_KILLED`. Sa population ne peut être ni relancée, ni
réinterprétée, ni renommée en nouvelle population.

Contrat H24 canonique :

```text
configs/harmonic_censoring_h24_successor_contract.json
6046 octets
SHA-256 d4b543ce1752974540d0779587dd0baf28bb747085d2017da5ef31bf850541fb
```

## Post-mortem A01

Le contrat H23 demandait simultanément :

```text
graphe F0 + H1–H20
chaque arête strictement ascendante
```

Le producteur a correctement construit `H1` comme `pitch → pitch`. Ces relations
sont fondamentales et réflexives, pas des harmoniques propres ascendantes. Elles
ont donc fait échouer l’oracle strict, même en l’absence de toute arête
descendante ou `C4 → C3`.

Ce post-mortem n’altère pas le verdict H23. Il définit seulement la correction
sémantique prospective nécessaire à une nouvelle hypothèse.

## Nouveau graphe typé

H24 partitionne les relations :

```text
H1
→ FUNDAMENTAL_IDENTITY
→ q(p,1) == p
→ jamais classé comme arête ascendante

H2–H20
→ PROPER_HARMONIC_ASCENT
→ q(p,h) > p
→ arête harmonique propre strictement ascendante
```

Chaque enregistrement futur devra conserver explicitement :

```text
source_pitch
harmonic_rank
observation_coordinate
relation_type
```

L’amplitude, l’énergie et l’état temporel ne peuvent pas changer l’orientation
du graphe. Une coïncidence fréquentielle ne permet jamais de renverser la
relation source vers observation.

## Premier test successeur

Le premier identifiant est nouveau :

```text
H24-A01-GRAPH-DIRECTION
```

Il exige séparément :

- toutes les relations H1 sont identité ;
- toutes les relations H2–H20 sont strictement ascendantes ;
- aucune relation n’est descendante ;
- le nombre de relations `C4 → C3` est nul.

Quatre inverses distinctes devront être rejetées : H1 non identité, harmonique
propre rendue identité, arête descendante injectée et H1 mensongèrement typée
comme harmonique propre. Le futur oracle devra recomputer le verdict depuis les
arêtes typées persistées et ne pourra accepter un booléen du producteur.

## Nouvelle identité, aucune population actuelle

```text
hypothèse             H24
namespace population H24_SYNTHETIC_V1
namespace tests      H24_TEST_V1
manifest population absent
manifest tests       absent
```

Les cardinalités `175/72` de H23 ne sont pas héritées. Les futurs manifests et
leurs cardinalités devront être dérivés et revus séparément sous les namespaces
H24 avant toute création de population.

## Portée

Ce commit autorise seulement le JSON de contrat, ses tests structurels et la
documentation. Il n’implémente aucun evaluator/oracle H24, ne crée aucun
manifest, fixture ou waveform et n’exécute aucun test scientifique. Données
réelles, H17, entraînement, export, live et locked-test restent interdits.

La prochaine action est uniquement la revue externe de ce contrat.
