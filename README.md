# Mini moteur d'inférence de types par résolution de contraintes

Projet personnel en Python : un vérificateur de types pour un petit langage
fonctionnel. Il devine le type de chaque expression en **générant des
contraintes** puis en **les résolvant**.

Il contient deux moteurs :

| Moteur | Fichier | Contraintes | Ce qu'il sait faire |
|---|---|---|---|
| 1. Hindley-Milner | `typer/hm.py` | égalités `t1 = t2`, résolues par unification | inférence complète, polymorphisme du `let`, occurs check |
| 2. Sous-typage | `typer/constraints.py` + `typer/solver.py` | inégalités `s <: t`, résolues par bornes inférieures/supérieures | types union, types singletons, contravariance des fonctions, occurrence typing |

Le moteur 1 montre la limite de Hindley-Milner : `if c then 1 else "a"` est
refusé, car une valeur n'y a qu'un seul type. Le moteur 2 accepte ce programme
et lui donne le type `"a" | 1`.

## Le langage

```
e ::= 5 | true | "foo"            littéraux
    | x                           variable
    | fun x -> e                  fonction (paramètre annotable : fun (x: Int | Str) -> e)
    | e1 e2                       application
    | let x = e1 in e2
    | if c then a else b
    | (a, b)                      paire
    | if x is T then a else b     test de type (occurrence typing)
```

Les programmes sont construits directement sous forme d'arbre (AST), par exemple
`App(Lam("x", Var("x")), Lit(5))` pour `(fun x -> x) 5`.

## Exemples

```
fun f -> fun x -> f (f x)                       ('a -> 'a) -> 'a -> 'a        (moteur 1)
let id = fun x -> x in (id 1, id true)          (Int * Bool)                  (moteur 1)
if cond then 1 else "a"                         erreur (moteur 1) / "a" | 1 (moteur 2)
if cond then "rouge" else "vert"                "rouge" | "vert"              (moteur 2)
fun (x: Int | Str) ->
    if x is Int then add x 1 else length x      (Int | Str) -> Int            (moteur 2)
```

## Lancer

```
pip install pytest
python -m pytest -q      # 27 tests
python essai.py          # démonstration des deux moteurs
```

## Limites connues

- Pas de structs ni de variables de rangées (seules les paires sont gérées).
- Moteur 2 : le `let` n'est pas polymorphe, et l'affichage des types de fonctions
  polymorphes est simplifié (une inconnue est résolue par l'union de ses bornes
  inférieures, sinon par son unique borne supérieure).
- Moteur 2 : une contrainte `s <: A | B` n'est vérifiée que si `s` ne contient pas
  d'inconnue (pas de recherche avec retour arrière).
- L'occurrence typing ne s'applique qu'à une variable dont le type est déjà connu
  au moment du test (annotée, ou issue d'un `let`).
