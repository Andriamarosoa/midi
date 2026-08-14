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

## Identites

```text
contract
9c536d6c5198a439fffc74b0b36510dedeb94910
3981 octets
f2e2292990de56d001d7e25a047a430865181bfea49f2c875911815679d221df

external seal
de9f83cfa079009bb5571995984004a945459b84
1174 octets
5327764a4bcf27ca4d1ea8f93d0bf24bf469730cbeb70103de26469e6878c74f
```

## Etat

Etat : `CONTRACT_ONLY_PENDING_EXTERNAL_REVIEW`.

La prochaine action autorisee est uniquement la revue externe de ce contrat et
de son seal. Identity binding, runner et creation reelle restent interdits.
