# =============================================================================
# hm.py — MOTEUR 1 : Hindley-Milner (l'algorithme classique).
#
# Principe, en deux phases (comme un exercice de physique) :
#   Phase 1 « generate » : on parcourt le programme et on ÉCRIT des équations
#                          entre types (les contraintes), sans les résoudre.
#   Phase 2 « unify »    : on RÉSOUT ces équations.
#
# Limite (voulue, c'est le point de départ du moteur 2) : ici une valeur n'a
# qu'UN seul type. « if c then 1 else "a" » est donc refusé.
# =============================================================================

from dataclasses import dataclass
from .types import TCon, TVar, TFun, TPair, INT, BOOL, STR, rename
from .syntax import Lit, Var, Lam, App, Let, If, Pair


class TypeError_(Exception):
    """Erreur de typage. (Le _ évite de cacher le TypeError déjà fourni par Python.)"""


# -----------------------------------------------------------------------------
# Inconnues « fraîches » : chaque appel à fresh() donne une NOUVELLE inconnue.
# -----------------------------------------------------------------------------
_counter = 0                                   # compteur global


def fresh() -> TVar:
    global _counter                            # on modifie la variable globale
    v = TVar(f"t{_counter}")                   # t0, puis t1, puis t2...
    _counter += 1
    return v


# -----------------------------------------------------------------------------
# Schémas de types : pour le polymorphisme du let.
# « id = fun x -> x » marche pour TOUT type 'a. On le note : pour tout a, a -> a.
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Scheme:
    """« Pour tout vars, type » (en maths : ∀a. a -> a)."""
    vars: frozenset    # les inconnues « génériques », remplaçables à chaque usage
    type: object


def free_vars(t) -> set:
    """Toutes les inconnues présentes dans un type."""
    if isinstance(t, TVar):
        return {t}
    if isinstance(t, TFun):
        return free_vars(t.arg) | free_vars(t.ret)   # | = union d'ensembles
    if isinstance(t, TPair):
        return free_vars(t.fst) | free_vars(t.snd)
    if isinstance(t, Scheme):                         # dans un schéma, les vars
        return free_vars(t.type) - t.vars             # génériques ne comptent pas
    return set()                                      # TCon : aucune inconnue


def instantiate(s: Scheme):
    """À chaque utilisation d'un schéma, on remplace ses inconnues génériques
    par des inconnues NEUVES. Ainsi « id 1 » et « id true » ne se gênent pas."""
    fresh_map = {v: fresh() for v in s.vars}          # 'a -> t7, par exemple
    return apply(fresh_map, s.type)


# -----------------------------------------------------------------------------
# PHASE 1 : génération des contraintes
# -----------------------------------------------------------------------------
def generate(env: dict, e) -> tuple:
    """Renvoie (type de l'expression e, liste de contraintes).
    'env' (environnement) : dictionnaire nom de variable -> son type.
    Une contrainte (t1, t2) veut dire : t1 doit être égal à t2."""

    if isinstance(e, Lit):                            # --- littéral ---
        if isinstance(e.value, bool):                 # bool AVANT int (True est un int en Python)
            return BOOL, []
        if isinstance(e.value, int):
            return INT, []
        if isinstance(e.value, str):
            return STR, []
        raise TypeError_(f"littéral non supporté : {e.value!r}")

    if isinstance(e, Var):                            # --- variable ---
        if e.name not in env:                         # variable jamais définie
            raise TypeError_(f"variable inconnue : {e.name}")
        t = env[e.name]
        if isinstance(t, Scheme):                     # variable polymorphe (venue d'un let)
            return instantiate(t), []
        return t, []                                  # aucune contrainte nouvelle

    if isinstance(e, Lam):                            # --- fun x -> body ---
        a = fresh()                                   # type de x : inconnu, on l'appelle a
        t_body, c = generate({**env, e.param: a}, e.body)  # on type le corps en sachant x : a
        return TFun(a, t_body), c                     # la fonction a le type a -> t_body

    if isinstance(e, App):                            # --- f arg ---
        t_fn, c1 = generate(env, e.fn)                # type de la fonction
        t_arg, c2 = generate(env, e.arg)              # type de l'argument
        r = fresh()                                   # type du résultat : inconnu
        # Équation : la fonction doit être de type  (type de l'arg) -> r
        return r, c1 + c2 + [(t_fn, TFun(t_arg, r))]

    if isinstance(e, If):                             # --- if c then a else b ---
        t_c, c1 = generate(env, e.cond)
        t_a, c2 = generate(env, e.then_)
        t_b, c3 = generate(env, e.else_)
        # Deux équations : la condition est un Bool, et les deux branches
        # ont le MÊME type (c'est la limite de Hindley-Milner).
        return t_a, c1 + c2 + c3 + [(t_c, BOOL), (t_a, t_b)]

    if isinstance(e, Pair):                           # --- (a, b) ---
        t1, c1 = generate(env, e.fst)
        t2, c2 = generate(env, e.snd)
        return TPair(t1, t2), c1 + c2

    if isinstance(e, Let):                            # --- let x = v in body ---
        t_val, c1 = generate(env, e.value)            # 1) type de la valeur
        s = solve(c1)                                 # 2) on résout tout de suite ses équations
        t_val = apply(s, t_val)                       #    pour connaître son vrai type
        # 3) Généralisation : les inconnues de t_val qui ne viennent PAS de
        #    l'environnement peuvent prendre n'importe quel type -> génériques.
        env_vars = set()
        for v in env.values():
            env_vars |= free_vars(apply(s, v))
        scheme = Scheme(frozenset(free_vars(t_val) - env_vars), t_val)
        t_body, c2 = generate({**env, e.name: scheme}, e.body)  # 4) on type le corps
        return t_body, c1 + c2

    raise TypeError_(f"expression inconnue : {e!r}")


# -----------------------------------------------------------------------------
# PHASE 2 : résolution par unification
# Une « substitution » est un dictionnaire : inconnue -> type trouvé.
# -----------------------------------------------------------------------------
def apply(subst: dict, t):
    """Remplace dans t chaque inconnue déjà résolue par sa valeur."""
    if isinstance(t, TVar):
        if t in subst:                                # on connaît sa valeur :
            return apply(subst, subst[t])             # on la remplace (récursif, car
        return t                                      # la valeur peut contenir d'autres inconnues)
    if isinstance(t, TFun):
        return TFun(apply(subst, t.arg), apply(subst, t.ret))
    if isinstance(t, TPair):
        return TPair(apply(subst, t.fst), apply(subst, t.snd))
    if isinstance(t, Scheme):                         # on ne touche pas aux vars génériques
        inner = {k: v for k, v in subst.items() if k not in t.vars}
        return Scheme(t.vars, apply(inner, t.type))
    return t                                          # TCon : rien à remplacer


def occurs(v: TVar, t) -> bool:
    """L'inconnue v apparaît-elle à l'intérieur de t ?"""
    return v in free_vars(t)


def unify(t1, t2, subst: dict) -> dict:
    """Résout l'équation t1 = t2. Renvoie la substitution enrichie, ou lève une erreur."""
    t1, t2 = apply(subst, t1), apply(subst, t2)       # on utilise ce qu'on sait déjà
    if t1 == t2:                                      # déjà égaux : rien à faire
        return subst
    if isinstance(t1, TVar):                          # t1 est une inconnue :
        return bind(t1, t2, subst)                    #   on la fixe à t2
    if isinstance(t2, TVar):                          # t2 est une inconnue :
        return bind(t2, t1, subst)                    #   on la fixe à t1
    if isinstance(t1, TFun) and isinstance(t2, TFun): # deux fonctions :
        subst = unify(t1.arg, t2.arg, subst)          #   arguments égaux
        return unify(t1.ret, t2.ret, subst)           #   et résultats égaux
    if isinstance(t1, TPair) and isinstance(t2, TPair):
        subst = unify(t1.fst, t2.fst, subst)
        return unify(t1.snd, t2.snd, subst)
    # Tous les autres cas : types incompatibles (ex. Int = Str)
    from .types import show
    raise TypeError_(f"impossible d'unifier {show(t1)} et {show(t2)}")


def bind(v: TVar, t, subst: dict) -> dict:
    """Fixe l'inconnue v au type t."""
    if occurs(v, t):
        # Exemple : fun x -> x x  donne  t0 = t0 -> t1.
        # t0 devrait se contenir lui-même : type infini, donc refusé.
        raise TypeError_(f"occurs check : {v.name} apparaît dans son propre type")
    return {**subst, v: t}                            # nouveau dictionnaire avec v -> t


def solve(constraints: list) -> dict:
    """Résout toute une liste d'équations, une par une."""
    subst = {}
    for t1, t2 in constraints:
        subst = unify(t1, t2, subst)
    return subst


# -----------------------------------------------------------------------------
# Point d'entrée
# -----------------------------------------------------------------------------
def infer(e, env=None):
    """Donne le type d'un programme e (ou lève TypeError_)."""
    global _counter
    _counter = 0                                      # repartir de t0 à chaque appel
    t, constraints = generate(env or {}, e)           # phase 1
    subst = solve(constraints)                        # phase 2
    return rename(apply(subst, t))                    # type final, joliment renommé
