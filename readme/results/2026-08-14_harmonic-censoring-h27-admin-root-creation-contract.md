# H27 — contrat de creation one-shot de la racine administrative

Date : 2026-08-14

## Contexte

La publication de source approuvee s'est arretee deux fois avant effet : le
leaf `/Users/amcarene/h27-admin/creator` et sa racine
`/Users/amcarene/h27-admin` sont absents. L'autorisation publisher reste non
consommee ; aucune observation final/staging ou creation n'a eu lieu.

## Portee du lot

Ce lot ajoute seulement :

- le contrat declaratif de creation future de `/Users/amcarene/h27-admin` ;
- son external seal ;
- un test structurel ;
- cette preuve et la mise a jour du journal.

Il n'ajoute aucun runner et n'effectue aucune operation Mac.

## Contrat ferme

Le parent exact `/Users/amcarene` devra preexister, etre un repertoire reel,
non symlink et rester ancre par un `dirfd` verifie. La seule cible possible est
le leaf `h27-admin`, obligatoirement absent avant effet.

```text
4 preflights
→ probe cible unique
→ revalidation parent
→ mkdir("h27-admin") premier et seul effet irreversible
→ fsync parent
→ ouverture O_NOFOLLOW et verification inode/dev
→ revalidation parent
→ succes terminal
```

`mkdir -p`, creation ou modification d'un autre chemin, retry, cleanup, repair
et recreation sont interdits. Le contrat interdit aussi toute observation du
child `creator`, des roots publisher, du registre, du bundle ou de la science.

Apres la premiere revue externe, le meme stage fixe aussi :

- l'ACK futur exact `H27_ADMIN_ROOT_CREATE_EXECUTE=1` et zero argument ;
- le dictionnaire ferme des quatorze regles ;
- sept exigences fermees pour un futur runner distinct : commit ulterieur,
  revue externe PASS, identity binding, seal externe, execution exclusive du
  blob Git exact et aucun fallback checkout/worktree.

## Identites

```text
contract
7ac98b37e745f2b3d1dc906c7392d21f8129019b
4505 octets
82e4bbe797493f99b7ef8e72073d9b761fd9036155fa74175b98b90e6bb4e32a

external seal
93597fd6d62db66d11c967466c663dece8b397de
1335 octets
4bd891cd9f008cb84702f8be1767be1f794361c2fe4cc9aeb070f56ee9efabbf
```

## Etat

Etat : `CONTRACT_ONLY_PENDING_EXTERNAL_REVIEW`.

La prochaine action autorisee est uniquement la revue externe de ce contrat et
de son seal. Identity binding, runner et creation reelle restent interdits.
