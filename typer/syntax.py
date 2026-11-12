# =============================================================================
# syntax.py — Comment on représente un PROGRAMME du mini-langage.
#
# On n'écrit pas les programmes comme du texte, on les construit directement
# sous forme d'ARBRE (AST = Abstract Syntax Tree, arbre de syntaxe abstraite).
# C'est d'ailleurs ce que fait Langeod chez Faveod : l'éditeur manipule
# directement l'arbre, sans syntaxe textuelle.
#
# Exemple : le programme  (fun x -> x) 5  s'écrit :
#     App(Lam("x", Var("x")), Lit(5))
#
# La grammaire du langage :
#   e ::= 5 | true | "foo"              littéraux
#       | x                             variable
#       | fun x -> e                    fonction anonyme
#       | e1 e2                         appel de fonction
#       | let x = e1 in e2              définition locale
#       | if c then a else b            condition
#       | (a, b)                        paire
#       | if x is T then a else b       test de type (occurrence typing)
# =============================================================================

from dataclasses import dataclass


@dataclass(frozen=True)
class Lit:
    """Une valeur écrite directement : 5, True, "foo"."""
    value: object


@dataclass(frozen=True)
class Var:
    """L'utilisation d'une variable : x."""
    name: str


@dataclass(frozen=True)
class Lam:
    """Une fonction : fun param -> body.
    'ann' (annotation, optionnelle) : le type déclaré du paramètre,
    comme en TypeScript : fun (x: Int | Str) -> ...
    Si ann vaut None, le moteur doit deviner le type du paramètre."""
    param: str              # nom du paramètre
    body: object            # corps de la fonction
    ann: object = None      # type annoncé du paramètre (facultatif)


@dataclass(frozen=True)
class App:
    """Un appel de fonction : fn arg (la fonction 'fn' appliquée à 'arg')."""
    fn: object
    arg: object


@dataclass(frozen=True)
class Let:
    """let name = value in body : on donne un nom à 'value' pour l'utiliser dans 'body'."""
    name: str
    value: object
    body: object


@dataclass(frozen=True)
class If:
    """if cond then then_ else else_.
    (then_ et else_ ont un _ car 'else' est un mot réservé de Python.)"""
    cond: object
    then_: object
    else_: object


@dataclass(frozen=True)
class Pair:
    """Une paire de deux valeurs : (fst, snd)."""
    fst: object
    snd: object


@dataclass(frozen=True)
class IfIs:
    """if var is typ then then_ else else_ : on TESTE le type d'une variable.
    Dans then_, le moteur sait que var a le type typ ;
    dans else_, il sait que var n'a PAS ce type. C'est l'occurrence typing."""
    var: str        # nom de la variable testée
    typ: object     # le type testé (ex. INT)
    then_: object
    else_: object
