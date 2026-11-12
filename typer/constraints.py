# =============================================================================
# constraints.py — MOTEUR 2 : inférence par contraintes de sous-typage.
#
# Même idée que hm.py (on parcourt le programme et on pose des contraintes),
# mais les contraintes sont des inégalités  s <: t  envoyées au Solver.
# Ce moteur accepte ce que Hindley-Milner refuse :
#   - les UNIONS          : if c then 1 else "a"   ->   "a" | 1
#   - les SINGLETONS      : "rouge" a le type "rouge" (pas seulement Str)
#   - l'OCCURRENCE TYPING : après « if x is Int », x est un Int dans la branche then
# =============================================================================

from .types import TVar, TFun, TPair, TLit, TUnion, INT, BOOL, STR, rename, is_subtype, make_union
from .syntax import Lit, Var, Lam, App, Let, If, Pair, IfIs
from .solver import Solver, TypeError_


# Fonctions prédéfinies, disponibles dans tous les programmes (comme une bibliothèque).
BUILTINS = {
    "add": TFun(INT, TFun(INT, INT)),   # add : Int -> Int -> Int   (addition)
    "length": TFun(STR, INT),           # length : Str -> Int       (longueur d'un texte)
    "not": TFun(BOOL, BOOL),            # not : Bool -> Bool
}


class Checker:
    def __init__(self):
        self.solver = Solver()           # le solveur qui reçoit toutes les contraintes
        self.counter = 0                 # pour fabriquer des inconnues neuves

    def fresh(self) -> TVar:
        v = TVar(f"t{self.counter}")
        self.counter += 1
        return v

    def generate(self, env: dict, e):
        """Renvoie le type de e. Les contraintes partent directement au solveur."""

        if isinstance(e, Lit):                        # --- littéral ---
            # Un littéral a un type SINGLETON : 5 a le type 5 (plus précis que Int).
            if not isinstance(e.value, (bool, int, str)):
                raise TypeError_(f"littéral non supporté : {e.value!r}")
            return TLit(e.value)

        if isinstance(e, Var):                        # --- variable ---
            if e.name not in env:
                raise TypeError_(f"variable inconnue : {e.name}")
            return env[e.name]

        if isinstance(e, Lam):                        # --- fun x -> body ---
            # Si le paramètre est annoté, on prend ce type ; sinon c'est une inconnue.
            a = e.ann if e.ann is not None else self.fresh()
            t_body = self.generate({**env, e.param: a}, e.body)
            return TFun(a, t_body)

        if isinstance(e, App):                        # --- f arg ---
            t_fn = self.generate(env, e.fn)
            t_arg = self.generate(env, e.arg)
            r = self.fresh()                          # type du résultat
            # La fonction doit pouvoir être utilisée comme une fonction
            # qui reçoit t_arg et renvoie r :   t_fn <: t_arg -> r
            # (grâce à la contravariance, cela vérifie  t_arg <: paramètre de f)
            self.solver.constrain(t_fn, TFun(t_arg, r))
            return r

        if isinstance(e, If):                         # --- if c then a else b ---
            t_c = self.generate(env, e.cond)
            self.solver.constrain(t_c, BOOL)          # la condition doit être un Bool
            t_a = self.generate(env, e.then_)
            t_b = self.generate(env, e.else_)
            r = self.fresh()                          # type du résultat
            # Différence clé avec HM : on n'exige PAS t_a = t_b.
            # On dit seulement que les DEUX entrent dans r : r sera donc t_a | t_b.
            self.solver.constrain(t_a, r)
            self.solver.constrain(t_b, r)
            return r

        if isinstance(e, Pair):                       # --- (a, b) ---
            return TPair(self.generate(env, e.fst), self.generate(env, e.snd))

        if isinstance(e, Let):                        # --- let x = v in body ---
            t_val = self.generate(env, e.value)
            return self.generate({**env, e.name: t_val}, e.body)

        if isinstance(e, IfIs):                       # --- if x is T then a else b ---
            if e.var not in env:
                raise TypeError_(f"variable inconnue : {e.var}")
            # 1) Que sait-on de x en ce moment ? (le solveur est incrémental)
            current = self.solver.resolve(env[e.var])
            if isinstance(current, TVar):
                raise TypeError_(f"type de {e.var} inconnu : annotez-le pour pouvoir le tester")
            # 2) On découpe le type de x en ses cas possibles.
            cases = current.members if isinstance(current, TUnion) else [current]
            yes, no = [], []                          # cas où le test réussit / échoue
            for m in cases:
                if is_subtype(m, e.typ):              # ce cas passe toujours le test
                    yes.append(m)                     #   (ex. 1 avec « is Int »)
                elif is_subtype(e.typ, m):            # le test est plus précis que ce cas
                    yes.append(e.typ)                 #   (ex. Int avec « is 1 ») :
                    no.append(m)                      #   les deux branches sont possibles
                else:                                 # ce cas ne passe jamais le test
                    no.append(m)
            # 3) On type chaque branche avec le type AFFINÉ de x.
            t_a = self.generate({**env, e.var: make_union(yes)}, e.then_)
            t_b = self.generate({**env, e.var: make_union(no)}, e.else_)
            r = self.fresh()                          # comme pour If : union des branches
            self.solver.constrain(t_a, r)
            self.solver.constrain(t_b, r)
            return r

        raise TypeError_(f"expression inconnue : {e!r}")


def check(e, env=None):
    """Donne le type d'un programme e avec le moteur de contraintes."""
    checker = Checker()
    t = checker.generate({**BUILTINS, **(env or {})}, e)   # génération + résolution
    return rename(checker.solver.resolve(t))               # lecture de la solution
