# H26 - correction du SHA documentaire R5 dans l'overlay

R7 `5906b3ebe0a8c7ee2fb95382c8b0382d44ee906f` contenait un developpement
incorrect du prefixe `23889bc` pour R5. Le commit reel, verifie par
`git rev-parse`, est :

`23889bc9480a6dd985d4fed56ab9b3d54528f98a`.

R8 corrige uniquement cette chaine documentaire dans l'overlay et les deux
rapports. Le blob effectif du loader R5 reste
`28b32bc0981c8d0c92ed9d0c911982482eee8d76`. Aucun code, JSON scelle
historique, ordre, runtime ou calcul scientifique n'a change.
