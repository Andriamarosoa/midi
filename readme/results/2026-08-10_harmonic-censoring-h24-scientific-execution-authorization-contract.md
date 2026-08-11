# H24 — contrat d'autorisation d'exécution scientifique

## Verdict opérationnel précédent

La population locale Mac `H24_SYNTHETIC_V1` a été matérialisée une seule fois,
puis auditée en lecture seule. L'audit administratif a confirmé :

- `175` fixtures uniques dans l'ordre scellé ;
- `525` fichiers fixture et `527` fichiers publiés au total ;
- `175` waveforms de `100352` octets, sans décodage scientifique pendant
  l'audit ;
- staging absent et success présent ;
- `scientific_tests_executed=0` et `locked_test_used=false`.

Les liaisons publiées sont :

- marker : `3185adfdba761590062378d7a230d9b990913d3197c2e9d1b006abbc0e62b85d` ;
- terminal : `50ec58c81d1a0ae533599676536d141c7f98ac337686c1baf66517bc3e39c54eb` ;
- receipt : `8a8128dc97c61f4203a89e116787f9eae319e7c146fbcd06b4432c4108f92cd5` ;
- index : `b45b63c477a3db13d161779bb28067c0b2b6fa5c4cc80c985199e9347e1eff15` ;
- IDs ordonnés : `d4b23a898d8775f772e91933ace7c90c2e7b5a808e32bf9955088287bbe9670f`.

## Portée de ce commit

Ce commit applique uniquement
`AUTHORIZED_TO_DEFINE_H24_SCIENTIFIC_EXECUTION_AUTHORIZATION_CONTRACT_ONLY`.
Le nouveau contrat a le SHA-256 :

`63355a01d6edb58c8cb3d41bebcd18264314a6b19a6ad8de96650a59541e9f68`.

Il lie la population publiée aux contrats, manifests et sources H24 existants.
Il définit un futur mécanisme fail-closed, sans l'implémenter :

1. capability scientifique process-local distincte ;
2. seal et activation scientifique séparés et revus ;
3. binding OS exact et worktree propre ;
4. rehash administratif complet des `525` fichiers avant émission ;
5. claim scientifique `O_EXCL` distinct du marker de matérialisation ;
6. décodage des waveforms seulement après ce claim ;
7. ordre fermé `P0 (27) → P1 (35) → P2 (10)` avec kill rule ;
8. terminal atomique et aucun retry après consommation.

## Correction de revue : transcript et terminal

La revue externe de `02bb76b2…` a validé la topologie, la dormance et les
liaisons de population, mais a refusé l'implémentation du runner tant que la
preuve scientifique persistée n'était pas normativement fermée. La portée
suivante a donc été appliquée, sans élargissement :

`AUTHORIZED_TO_CORRECT_H24_SCIENTIFIC_EXECUTION_CONTRACT_TRANSCRIPT_AND_TERMINAL_CLOSURE_ONLY`.

Le contrat révisé impose maintenant :

- un transcript final de exactement `72` lignes JSONL canoniques UTF-8/LF,
  dans l'ordre scellé `P0 (27) → P1 (35) → P2 (10)` ;
- un schéma fermé par record et quatre états seulement : preuve persistée,
  suffixe kill-rule, erreur opérationnelle et suffixe d'échec opérationnel ;
- une chaîne SHA-256 record par record, initialisée par `64` zéros, qui rend
  toute suppression, insertion, duplication ou permutation invalide ;
- pour chaque preuve exécutée, le chemin relatif, la taille et le SHA-256 des
  octets d'evidence persistés, sans booléen PASS/FAIL du producteur ;
- la réouverture et le rehash du transcript et de toutes les preuves depuis le
  disque avant finalisation ;
- un finalizer pur et indépendant qui recalcule chaque oracle, le premier
  échec, les compteurs et le suffixe `NOT_RUN` uniquement depuis les octets
  persistés ;
- un terminal qui lie explicitement transcript, dernier maillon, preuves
  ordonnées, claim scientifique et les quatre hashes de population ;
- un terminal `H24_EXECUTION_INCONCLUSIVE_CONSUMED` pour toute erreur ordinaire
  post-claim pouvant être finalisée ; crash brutal, timeout, SIGKILL, panne ou
  erreur de publication laissent le claim consommé, les partiels non
  autoritatifs et interdisent tout retry, même si aucun terminal n'a pu être
  publié.

Le SHA canonique de la liste ordonnée des `72` IDs est
`3d9c9178ece6b8f0631baf4392bc92f0aa074ed987875e0cb208ab0f90201376`.
Le SHA-256 brut du contrat révisé est
`00f67158248a879a754d39e3ed452a9b8926ee4c9adab8d023d92be1138e988e`.

## Implémentation dormante approuvée en portée

Après approbation de la fermeture précédente, la portée
`AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_SCIENTIFIC_CAPABILITY_AND_RUNNER_ONLY`
a été appliquée. Le contrat passe au schéma `3`, SHA-256
`426a80be3f409380fc30e5d35fa0d90ae340dd475b72be319c871b79ebb531f4`.

Deux modules dormants sont ajoutés :

- `harmonic_censoring_h24_scientific_capability.py` vérifie le contrat,
  l'activation OS, HEAD/worktree, les blobs source, le runtime arm64 exact, les
  quatre artefacts de publication et les `525` fichiers sans décoder les
  waveforms. La capability est process-local, sans constructeur public et
  refuse copie, pickle, replace ou fabrication manuelle ;
- `run_harmonic_censoring_h24_scientific.py` implémente le claim `O_EXCL`, les
  preuves canoniques, les `72` records hash-chain, la publication atomique et
  le finalizer indépendant relisant les octets persistés.

Le registre de producteurs scientifiques reste explicitement
`H24_EVIDENCE_PRODUCER_REGISTRY_IMPLEMENTED=false`. Le runner refuse donc
avant le claim. Le seal et l'activation scientifiques sont absents ; l'issuer
public refuse avant tout accès à la population si le binding OS manque. Les
tests de transcript utilisent uniquement des preuves mock dans des répertoires
temporaires et patchent le recomputer : aucun evaluator/oracle scientifique
réel n'est exécuté.

## Correction des gardes topologiques one-shot

La revue externe de `e705afe5c21f84f53ea2ebd3e95b8236ee591999` a
approuvé la structure dormante, mais a refusé le passage aux producteurs tant
que les chemins du futur seal pouvaient entrer dans la population publiée ou
s'imbriquer entre eux. La portée appliquée est strictement
`AUTHORIZED_TO_CORRECT_H24_DORMANT_SCIENTIFIC_PATH_TOPOLOGY_GUARDS_ONLY`.

Le preflight pré-claim rejette maintenant `claim`, `staging`, `success` ou
`terminal` s'ils sont situés dans le namespace de contrôle de matérialisation
`tmp/local/harmonic_censoring_h24_synthetic_v1`. Il rejette aussi toute
sortie de premier niveau qui serait un ancêtre de ce namespace, ainsi que toute
relation ancêtre/descendant entre les sept chemins one-shot, sauf exactement :

- `success -> scientific_transcript.jsonl` ;
- `success -> evidence` ;
- `staging -> scientific_transcript.jsonl.part`.

Cela interdit notamment un claim sous la population, un terminal sous success,
un claim dont le parent est staging, ou un success descendant de staging. Les
tests adversariaux appellent le garde pur sans créer de fichier. Le contrat
passe au schéma `4`, SHA-256
`4d33f80b27d8e5086548596fb377d00a8327cff53f12540969709f456ed21ea9`.

## Dormance

Ce commit implémente les types et frontières dormants, mais n'émet aucune
capability et ne crée ni seal, ni activation, ni claim scientifique réel. Il ne
lit pas les waveforms publiées, ne lance aucun evaluator/oracle et n'exécute
aucun P0/P1/P2. Il n'utilise ni données réelles, ni H17, ni locked-test, ni
modèle/checkpoint, ni training.

La population publiée est immutable : aucune réparation, régénération ou
seconde matérialisation n'est autorisée.

## Vérification

La suite administrative ciblée H24/H23/H20, incluant le correctif topologique,
réussit avec `200` tests en `3,121 s`. `py_compile` et `git diff --check`
réussissent également.

## Étape suivante

## Implémentation exacte des 72 producteurs, toujours dormante

La revue externe du correctif topologique a accordé exactement
`AUTHORIZED_TO_DEFINE_AND_IMPLEMENT_H24_EXACT_72_EVIDENCE_PRODUCERS_ONLY`.
Le registre suit l'ordre scellé des `72` tests (`27` P0, `35` P1, `10` P2).
`H24-A01-GRAPH-DIRECTION` possède un producteur indépendant qui persiste le
graphe typé complet, les diagnostics et les sept mutations inverses fermées.
Les `71` autres producteurs réutilisent les noyaux de mesure H23 déjà
versionnés par un adaptateur strict `H23 fixture -> H24-F-<fixture>` et
consomment uniquement les waveforms et targets H24 dont les octets auront été
vérifiés après un futur claim. Chaque résultat est projeté exactement vers les
champs `primary`/`inverse` du schéma H24; `pass`, `verdict` et tout verdict de
producteur restent interdits.

Cette implémentation ne crée aucun seal ni activation. L'issuer public échoue
avant résolution du registre, accès population, import NumPy et claim. Les
tests de ce commit invoquent seulement A01 analytique et A06 contractuel; ils
ne décodent aucune waveform publiée et n'exécutent aucun P0/P1/P2 réel.

Le contrat passe au schéma `5`, SHA-256
`879cadea244c5d209de36bbcb644ecdb35b656ede416e84d43c7dc17008d2a55`.
La suite administrative H24/H23/H20 complète réussit avec `206` tests : les
`199` tests H24/H23 incluant les six nouveaux tests producteurs, plus les
`7` gardes H20. `py_compile` et `git diff --check` réussissent également.

## Correction des bindings producteurs et suppression de la resynthèse

La revue stricte de `4737e74cc7623492eb714f977889ed7505809dbb` a
refusé le passage au seal. D'une part, le futur seal ne liait pas le blob du
nouveau module producteur ni les trois entrées H23 qu'il exécute. D'autre part,
`18` évaluateurs prédécesseurs atteignaient transitivement une fonction de
resynthèse de waveform.

La portée corrective appliquée est exactement
`AUTHORIZED_TO_CORRECT_H24_EXACT_72_EVIDENCE_PRODUCER_BINDINGS_AND_NO_RESYNTHESIS_ONLY`.
Activation et seal futurs doivent maintenant lier : module producteur H24,
runner H23, harness H23 et SHA brut du contrat scientifique H23, en plus de la
capability, du runner et du contrat H24. L'issuer vérifiera tous ces blobs et
octets avant capability issuance.

Les `18` producteurs dont le call graph H23 atteignait
`_projected_harmonic_waveform`, `_render_source`, `_synthesize_h23_fixture` ou
`_waveform_from_sources` possèdent désormais des overrides H24. Ceux-ci ne
lisent que les waveforms H24 publiées, leurs spécifications scellées et des
transformations numériques des arrays décodés. Les autres producteurs restent
adossés aux évaluateurs H23 dont le call graph est statiquement exempt de ces
quatre symboles. Les tests reconstruisent le call graph et exigent l'égalité
exacte entre l'ensemble des `18` voies dangereuses et l'ensemble des overrides.

Le contrat passe au schéma `6`, SHA-256
`9a814216a460d1041edd577c21f3e898735946ad28d99c81cc996ac1e738e3fb`.
La suite administrative H24/H23/H20 complète réussit avec `209` tests en
`3,065 s`; `py_compile` et `git diff --check` réussissent également.
Toujours aucun seal, activation, capability issuance, claim, accès population,
décodage waveform, P0/P1/P2, H17, locked-test, modèle ou training.

## Étape suivante

Uniquement la revue externe du commit exact des producteurs. Un autre cycle
séparé restera obligatoire pour définir un seal/activation scientifique. Tant
que ce cycle n'est pas approuvé, capability issuance, claim, population,
waveforms et exécution P0/P1/P2 restent interdits.

## Correction du binding au HEAD d'activation OS-bound

La revue stricte du commit réel
`ed087827e63f8186886026a93d56530a205816ec` a approuvé les `18` overrides
sans resynthèse, mais a refusé la fermeture d'autorité : les blobs étaient
vérifiés au commit d'implémentation revu sans être comparés au HEAD
d'activation réellement exécuté.

La portée appliquée est exactement
`AUTHORIZED_TO_CORRECT_H24_OS_BOUND_ACTIVATION_HEAD_SOURCE_AND_PREDECESSOR_CONTRACT_BINDINGS_ONLY`.
Avant toute capability issuance, chacun des cinq blobs — capability H24,
runner H24, producteurs H24, runner H23 et harness H23 — doit maintenant être
identique au blob scellé dans le commit d'implémentation **et** dans le commit
d'activation OS-bound. Le contrat scientifique H23 doit simultanément égaler
le SHA déjà scellé
`719eba0aa440fc1e77ae7d204adee9e5b51517f455fad3bfed7e761d3c00a74a`
dans le seal, les octets du checkout et les octets Git du commit d'activation.

Le contrat passe au schéma `7`, SHA-256
`a0726827400617e87de4cc0a57d2ded4998d7c9a54bf0c81fa3c39cdfc69d6e9`.
La suite administrative H24/H23/H20 complète réussit avec `211` tests en
`3,051 s`; `py_compile` et `git diff --check` réussissent également.
Les `72` producteurs et leurs mesures sont inchangés. Toujours aucun seal,
activation, capability, claim, accès population, décodage waveform, P0/P1/P2,
H17, locked-test, modèle ou training.

## Étape suivante

Uniquement la revue externe de ce correctif d'autorité exact. Toute création
de seal/activation ou exécution scientifique exige encore une autorisation
séparée.

## Seal scientifique H24 dormant

La revue externe a approuvé
`22bf87831838fa0c0467ae1f54be788c91d47951` et autorisé exactement
`AUTHORIZED_TO_DEFINE_AND_COMMIT_H24_SCIENTIFIC_AUTHORIZATION_SEAL_ONLY`.
Le seal créé à
`configs/harmonic_censoring_h24_scientific_execution_authorization_seal.json`
a le SHA-256
`818e53cd510bdd5b055372ad213e1a76d83af2d74adee7d158626b3f85346c61`.

Il lie exactement :

- le commit d'implémentation approuvé `22bf8783…` et sa topologie de six
  fichiers ;
- les blobs capability H24, runner H24, producteurs H24, runner H23 et
  harness H23 ;
- le contrat H24 schéma `7` (`a0726827…`) et le contrat H23 (`719eba0a…`) ;
- CPython `3.11.9`, NumPy `1.26.4`, arm64, CPU et les cinq variables de threads
  fixées à `1` ;
- les sept chemins one-shot hors du namespace immuable de population.

Le seal exige encore la revue de son commit exact. Aucun fichier d'activation
H24 n'existe, aucune variable OS-bound n'est injectée et l'issuer reste dormant
avant population et NumPy. Aucun claim, waveform, P0/P1/P2, H17, locked-test,
modèle ou training n'a été utilisé.
La suite administrative H24/H23/H20 complète réussit avec `216` tests en
`3,172 s`; `git diff --check` réussit également.

## Étape suivante

Uniquement la revue externe du commit exact du seal. La création d'une
activation resterait un cycle séparé et n'est pas autorisée ici.

## Activation H24 dormante

La revue externe a approuvé
`db738d35c907b9954b4765a0af023fa4b59f871b` et autorisé exactement
`AUTHORIZED_TO_DEFINE_AND_COMMIT_H24_SCIENTIFIC_ACTIVATION_ONLY`.
L'activation versionnée à
`configs/harmonic_censoring_h24_scientific_execution_activation.json` a le
SHA-256
`4082cf4edc4612c8934133f6882c1e3769cd4af58f6a64efd29310a5807d75a1`.

Elle lie le seal approuvé `818e53cd…`, le commit d'implémentation
`22bf8783…`, les cinq blobs exécutables et les contrats H24/H23 déjà scellés.
Son objet `external_review` exige encore la revue du commit exact
d'activation. La variable OS
`H24_SCIENTIFIC_EXECUTION_AUTHORIZATION_COMMIT` n'est ni définie ni injectée;
la présence du fichier ne permet donc aucune capability issuance.

Aucun claim, waveform, population decode, P0/P1/P2, H17, locked-test, modèle,
calibration ou training n'a été utilisé.
La suite administrative H24/H23/H20 complète réussit avec `220` tests en
`3,359 s`; `git diff --check` réussit également.

## Étape suivante

Uniquement la revue externe du commit exact d'activation. L'injection du
binding OS et toute exécution scientifique restent interdites sans nouvelle
autorisation explicite.

## Incident du preflight zéro-science et correction du binding marker

Après revue de l'activation et binding OS exact au commit
`8f23054e8f58eed98ff4d1453d2a15d021aa36fd`, l'unique invocation autorisée de
`issue_h24_scientific_execution_capability()` a échoué fail-closed avec
`H24 population marker SHA mismatch`, avant émission de capability.

Le diagnostic administratif, sans relance, a établi :

- marqueur publié : `1805` octets ;
- SHA-256 réel :
  `3185adfdba761590062378d7a230d9b990913d3197c2e9d1b006abbc0e62b85d` ;
- valeur du contrat schéma `7` : `65` caractères, avec un zéro supplémentaire
  après `1590` ;
- claim scientifique, success et terminal scientifiques absents ;
- aucun décodage waveform, NumPy scientifique, P0/P1/P2 ou retry.

La portée externe
`AUTHORIZED_TO_CORRECT_H24_PUBLISHED_POPULATION_MARKER_SHA_BINDING_AND_DORMANT_IMPLEMENTATION_BINDINGS_ONLY`
autorise uniquement la correction de ce digest et des bindings administratifs
dormants correspondants. Le contrat passe au schéma `8`, SHA-256
`d587358ad1dfebf9e7d4ea3eaeb632b080e8bc68e14fe4caa331cd803048387b`.
Les producteurs, le runner, les `72` mesures, les `18` overrides et les octets
de population restent strictement inchangés.

Le seal `818e53cd…`, l'activation `4082cf4e…` et le binding OS historique vers
`8f23054e…` ne sont pas rafraîchis dans cette portée. Ils lient l'ancien SHA du
contrat et sont donc volontairement obsolètes : l'issuer doit refuser avant
toute capability tant qu'un nouveau cycle seal/activation/binding OS n'a pas
été séparément autorisé et revu.

La vérification administrative comprend `213` tests H24/H23 et `7` gardes H20,
soit `220` tests réussis. `py_compile` et `git diff --check` réussissent aussi.

## Étape suivante

Uniquement la revue externe du commit exact de correction. Aucune relance de
l'issuer, capability, claim, population decode, P0/P1/P2, H17, locked-test,
modèle, calibration ou training n'est autorisée.

## Correction du validateur de topologie du seal de remplacement

La revue externe du commit `696a94ea88e03c233f2c145aab2cf8e4f897ac59`
a approuvé le binding marker, puis a confirmé un second défaut purement
administratif : `_validate_seal()` exigeait toujours l'ancienne topologie
d'implémentation à `6` fichiers. Un seal honnête liant la topologie corrective
à `8` fichiers aurait donc été rejeté.

La portée
`AUTHORIZED_TO_CORRECT_H24_REPLACEMENT_SEAL_TOPOLOGY_VALIDATION_AND_REBASE_DORMANT_AUTHORITY_BINDINGS_ONLY`
autorise ce micro-correctif sans création de seal. Le validateur exige désormais
la topologie exacte du nouveau commit candidat ; le contrat passe au schéma `9`,
SHA-256
`8049f8d613cb45eba80e5d10b0fcc440b25ac317ec4cdac1c02ffbba735ad1af`.
Comme le blob capability change, le futur seal devra lier le commit exact de ce
correctif, son nouveau blob et son vrai `git diff-tree`.

Le seal `818e53cd…`, l'activation `4082cf4e…` et le binding OS `8f23054e…`
restent physiquement inchangés et obsolètes. Le seal historique est maintenant
explicitement rejeté par le validateur de topologie avant toute capability.
Runner, producteurs, `72` mesures, `18` overrides, manifests et population
restent inchangés.

La vérification administrative comprend `215` tests H24/H23 et `7` gardes
H20, soit `222` tests réussis. `py_compile` et `git diff --check` réussissent.

## Étape suivante

Uniquement la revue externe de ce commit dormant. Aucun remplacement de seal,
activation, binding OS, issuer, capability, claim, population decode,
P0/P1/P2, H17, locked-test, modèle, calibration ou training n'est autorisé.
