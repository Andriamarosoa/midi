# Résultat — état du produit desktop monophonique

> Date de consolidation : 2026-07-28
> Statut : accepté dans son périmètre monophonique

## Contrat

- Guitare propre monophonique.
- Plage MIDI 40–76.
- Fenêtres causales 512, 1024, 2048 et 4096.
- Hop de 256 échantillons à 44,1 kHz.
- Sorties pitch, activité et informations harmoniques.
- Profil live `safe_low_ghost`.

## Validation

| Contrôle | Résultat |
|---|---:|
| Parité TFLite | réussie |
| Parité ONNX | réussie |
| Backpressure | réussi |
| Perte audio lors du contrôle matériel | 0 |
| Guitar-TECHS direct, top-1 pitch | 94,67 % |
| Guitar-TECHS micro + ampli, top-1 pitch | 90,20 % |
| IDMT D1, top-1 pitch | 81,20 % |
| IDMT D2, top-1 pitch | 49,73 % |

Le manifest de livraison marque le produit prêt pour ce périmètre précis.

## Limites

- Une sortie softmax unique ne peut pas transcrire des accords.
- Le profil anti-fantômes peut fusionner des répétitions rapides de la même
  hauteur.
- IDMT D2 est hors du domaine garanti.
- Ce produit reste un secours stable ; il ne remplace pas l’objectif
  polyphonique.

## Preuves

- `artifacts/guitar_midi_v1_0_0/release_manifest.json`
- `artifacts/guitar_midi_v1_0_0/metadata.json`
- `artifacts/guitar_midi_v1_0_0/parity_report.json`
- `artifacts/guitar_midi_v1_0_0/onnx_report.json`
- `artifacts/guitar_midi_v1_0_0/external_sources_report.json`
