# =============================================================================
# solver.py — Le SOLVEUR de contraintes de sous-typage (cœur du moteur 2).
#
# Différence avec Hindley-Milner :
#   HM écrit des équations       t1 = t2   (« même type »)
#   Ici on écrit des inégalités  s <: t    (« s est un cas particulier de t »)
#
# Pour chaque inconnue 'a, le solveur garde deux listes :
#   - ses BORNES INFÉRIEURES : les types qui « entrent » dans 'a
#     (ex. if c then 1 else "x"  ->  1 <: 'a  et  "x" <: 'a)
#   - ses BORNES SUPÉRIEURES : ce qu'on exige de 'a
#     (ex. on passe 'a à une fonction qui veut un Int  ->  'a <: Int)
# Règle d'or : chaque borne inférieure doit respecter chaque borne supérieure.
#
# Le solveur est INCRÉMENTAL : chaque contrainte est traitée dès qu'elle arrive.
# =============================================================================

from .types import TVar, TFun, TPair, TLit, TCon, TUnion, show, is_subtype, make_union


class TypeError_(Exception):
    """Erreur de typage."""


class Solver:
    def __init__(self):
        self.lower = {}      # inconnue -> liste de ses bornes inférieures
        self.upper = {}      # inconnue -> liste de ses bornes supérieures
        self.seen = set()    # contraintes déjà traitées (évite les boucles infinies)

    # -------------------------------------------------------------------------
    # Ajouter une contrainte  s <: t
    # -------------------------------------------------------------------------
    def constrain(self, s, t):
        if (s, t) in self.seen:              # déjà traitée : on s'arrête
            return
        self.seen.add((s, t))                # on la mémorise

        if s == t:                           # A <: A est toujours vrai
            return

        if isinstance(s, TVar):              # --- cas 1 : 'a <: t ---
            self.upper.setdefault(s, []).append(t)    # t devient une borne sup. de 'a
            for low in list(self.lower.get(s, [])):   # tout ce qui est déjà entré dans 'a
                self.constrain(low, t)                # doit aussi respecter t
            return

        if isinstance(t, TVar):              # --- cas 2 : s <: 'a ---
            self.lower.setdefault(t, []).append(s)    # s devient une borne inf. de 'a
            for up in list(self.upper.get(t, [])):    # s doit respecter toutes les
                self.constrain(s, up)                 # exigences déjà connues sur 'a
            return

        if isinstance(s, TUnion):            # --- cas 3 : (A | B) <: t ---
            for m in s.members:              # chaque membre doit tenir dans t
                self.constrain(m, t)
            return

        if isinstance(t, TUnion):            # --- cas 4 : s <: (A | B) ---
            if is_subtype(s, t):             # s doit tenir dans au moins un membre
                return
            raise TypeError_(f"{show(s)} n'est pas un sous-type de {show(t)}")

        if isinstance(s, TFun) and isinstance(t, TFun):   # --- cas 5 : fonctions ---
            self.constrain(t.arg, s.arg)     # CONTRAVARIANCE : le sens s'inverse !
            self.constrain(s.ret, t.ret)     # covariance : même sens pour le résultat
            return

        if isinstance(s, TPair) and isinstance(t, TPair): # --- cas 6 : paires ---
            self.constrain(s.fst, t.fst)     # composante par composante
            self.constrain(s.snd, t.snd)
            return

        if isinstance(s, TLit) and isinstance(t, TCon) and is_subtype(s, t):
            return                           # --- cas 7 : "rouge" <: Str, 1 <: Int ---

        # Aucun cas ne marche : erreur de type.
        raise TypeError_(f"{show(s)} n'est pas un sous-type de {show(t)}")

    # -------------------------------------------------------------------------
    # Lire la solution : quel type a finalement une inconnue ?
    # -------------------------------------------------------------------------
    def resolve(self, t, visiting=frozenset()):
        """Remplace les inconnues par ce que le solveur sait d'elles.
        - Si des types sont entrés dans 'a : 'a = l'UNION de ces types.
        - Sinon, si on exige un seul type précis de 'a : 'a = ce type.
        - Sinon : on ne sait rien, 'a reste une inconnue."""
        if isinstance(t, TVar):
            if t in visiting:                # sécurité contre les cycles 'a <: 'b <: 'a
                return t
            visiting = visiting | {t}
            lows = self.lower.get(t, [])
            if lows:                         # des types sont entrés : on fait leur union
                return make_union([self.resolve(x, visiting) for x in lows])
            ups = [self.resolve(x, visiting) for x in self.upper.get(t, [])]
            ups = list(dict.fromkeys(u for u in ups if not isinstance(u, TVar)))
            if len(ups) == 1:                # une seule exigence connue : c'est le type
                return ups[0]
            return t                         # sinon : toujours inconnue
        if isinstance(t, TFun):
            return TFun(self.resolve(t.arg, visiting), self.resolve(t.ret, visiting))
        if isinstance(t, TPair):
            return TPair(self.resolve(t.fst, visiting), self.resolve(t.snd, visiting))
        if isinstance(t, TUnion):
            return make_union([self.resolve(m, visiting) for m in t.members])
        return t                             # TCon, TLit : déjà connus
