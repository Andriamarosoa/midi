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

- marker : `3185adfdba7615900062378d7a230d9b990913d3197c2e9d1b006abbc0e62b85d` ;
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
`AUTHORIZED_TO_CORRECT_H24_DORMANT_SCIENTIFIC_PATH_TOPOLOGY_GUARDS`.

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
`4f061cb2c426ce28872ede54821bc6fdf227cda211b8957d0b546342cc781d06`.

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
réussit avec `200` tests en `3,492 s`. `py_compile` et `git diff --check`
réussissent également.

## Étape suivante

Uniquement la revue externe du commit d'implémentation dormant exact. Une
autorisation séparée sera nécessaire avant de définir les `72` producteurs
scientifiques, puis un autre cycle sera requis pour seal/activation. P0/P1/P2
restent interdits.
