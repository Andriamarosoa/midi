# Validation desktop du checkpoint sélectionné — 2026-07-29

## Périmètre

La sélection Kaggle `epoch-08` du run
`polyphonic_multisource_20260728_192326` a été installée localement puis
exportée en TFLite float16 et ONNX. Tous les contrôles utilisent uniquement le
split validation. Le test verrouillé n’a pas été ouvert.

## Reproductibilité et parité

- SHA-256 de `selected.keras` :
  `aaec718882bd1344461ecffa3475dceb10edcad5b2e265b1494977f6e1c9834c`.
- SHA-256 TFLite :
  `4a4df49d34c1fd359fab98c20bb598f37c7f42f22493c70923a2e829176df744`.
- Le TFLite exporté est bit à bit identique au TFLite du bundle desktop
  actuellement déployé.
- Les sorties TFLite et ONNX ont une concordance de décision frame/onset de
  100 % sur 96 exemples de validation.
- ONNX opset 18 passe ; p95 CPU avec un thread : 3,25 ms pour un budget de hop
  de 5,80 ms.

Les poids utiles sont donc reproduits. La différence testée en live/WAV vient
principalement des nouveaux seuils sélectionnés (`frame=0,55`,
`onset=0,635`) contre ceux du bundle stable (`frame=0,535`,
`onset=0,665`), et non d’un nouveau comportement appris.

## Stabilité TFLite

Deux benchmarks saturés de 3 sessions × 600 inférences ont conservé un p95
généralement sous le budget du hop, mais aucun nombre de threads n’a satisfait
simultanément toutes les limites strictes sur les pointes, le taux de
dépassement et la variation inter-session.

Lors de la seconde passe :

- 1 thread : p95 4,34 ms ;
- 3 threads : p95 3,37 ms, mais 0,33 % d’inférences au-dessus du hop ;
- résultat du garde-fou strict : échec.

Le pipeline WAV réel reste sous le budget p95 : 4,62 ms sur Guitar-TECHS et
4,76 ms sur GuitarSet. Le candidat demeure utilisable pour diagnostic, mais
ne mérite pas une promotion automatique. Le runtime retombe désormais sur un
thread si aucune recommandation stricte n’existe, au lieu de planter sur une
valeur `null`.

## Comparaison alignée WAV/MIDI

Deux extraits déterministes du sous-ensemble de validation ont été transcrits
avec le bundle stable et avec les nouveaux seuils.

### Guitar-TECHS direct input, 30 s

- 32 notes de référence ;
- baseline : F1 onset 0,0370, 21 faux positifs, 31 notes manquantes ;
- candidat : F1 onset 0,0357, 23 faux positifs, 31 notes manquantes ;
- seulement une attaque physique détectée pour 64 onsets annotés dans
  l’extrait ;
- 22 notes du candidat sur 24 sont soutenues spectralement, contre 20 sur 22
  pour le baseline.

Les hauteurs émises peuvent donc être plausibles spectralement, mais leur
timing et leur attribution aux attaques sont largement incorrects. Le domaine
Guitar-TECHS reste le principal échec.

### GuitarSet, 22,32 s

- 127 notes de référence ;
- F1 onset : 0,2966 → 0,3025 ;
- F1 onset+offset : 0,2542 → 0,2437 ;
- faux positifs : 74 → 75 ;
- références fragmentées : 2 → 4 ;
- notes spectralement soutenues : 105/109 → 108/111 ;
- notes non soutenues : 2 dans les deux cas.

Le seuil onset plus bas récupère une note appariée, mais dégrade les offsets et
double la fragmentation. Le gain est insuffisant pour une promotion.

## Diagnostic global

La sélection validation-only compte 444 faux NoteOn à l’octave, soit 20,96 %
des faux NoteOn causaux. Les erreurs Guitar-TECHS sont surtout des octaves vers
le bas, tandis que GAPS contient davantage d’octaves vers le haut. Les audits
alignés montrent peu de faux positifs correspondant aux intervalles
harmoniques supérieurs classiques : le problème dominant est l’attaque, le
timing, la fragmentation et l’alias d’octave dépendant du corpus.

## Décision

Le bundle `artifacts/guitar_midi_polyphonic_v2_2_0` reste le bundle desktop
stable. Le candidat du 29 juillet n’est pas promu.

La prochaine expérience doit modifier un seul élément : rendre la détection
d’attaque causale adaptative au domaine Guitar-TECHS, puis revalider les mêmes
WAV et les métriques événementielles avant tout changement de seuil ou nouveau
train.
