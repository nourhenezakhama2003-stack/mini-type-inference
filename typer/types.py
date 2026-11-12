# =============================================================================
# types.py — Comment on représente un TYPE dans le programme.
#
# Un type, c'est « l'unité » d'une valeur : Int (nombre), Str (texte),
# Bool (vrai/faux), une fonction Int -> Int, etc.
# Chaque sorte de type est une petite classe Python.
# =============================================================================

from dataclasses import dataclass  # outil Python pour créer des classes simples


# frozen=True : l'objet ne peut plus être modifié après sa création.
# Avantage : on peut comparer deux types avec == et les mettre dans un set ou un dict.
@dataclass(frozen=True)
class TCon:
    """Type de base (« constante de type ») : Int, Bool ou Str."""
    name: str  # le nom du type, par exemple "Int"


@dataclass(frozen=True)
class TVar:
    """Variable de type = une INCONNUE, comme x dans une équation.
    On ne sait pas encore quel type c'est ; le moteur va le trouver."""
    name: str  # un nom unique, par exemple "t0", "t1"...


@dataclass(frozen=True)
class TFun:
    """Type d'une fonction : elle prend un 'arg' et renvoie un 'ret'.
    Exemple : TFun(INT, BOOL) s'écrit Int -> Bool."""
    arg: object  # type de ce que la fonction reçoit
    ret: object  # type de ce que la fonction renvoie


@dataclass(frozen=True)
class TPair:
    """Type d'une paire (un tuple de 2 éléments) : (Int * Bool)."""
    fst: object  # type du premier élément
    snd: object  # type du second élément


@dataclass(frozen=True)
class TLit:
    """Type SINGLETON : un type qui ne contient qu'UNE seule valeur.
    Exemple : TLit("rouge") est le type dont la seule valeur est "rouge".
    C'est plus précis que Str, qui contient tous les textes."""
    value: object  # la valeur unique : "rouge", 1, True...


@dataclass(frozen=True)
class TUnion:
    """Type UNION : « ceci OU cela ». Exemple : Int | Str.
    Une union vide (aucun membre) s'appelle Never : aucune valeur possible."""
    members: frozenset  # ensemble (non modifiable) des types possibles


# Les trois types de base, créés une seule fois pour être réutilisés partout.
INT = TCon("Int")
BOOL = TCon("Bool")
STR = TCon("Str")


# -----------------------------------------------------------------------------
# Affichage d'un type sous forme de texte lisible
# -----------------------------------------------------------------------------
def show(t) -> str:
    """Transforme un type en texte : TFun(INT, BOOL) -> "Int -> Bool"."""
    if isinstance(t, TCon):                    # type de base
        return t.name                          # on affiche juste son nom
    if isinstance(t, TVar):                    # inconnue
        return "'" + t.name                    # convention : 'a, 'b...
    if isinstance(t, TLit):                    # singleton
        if isinstance(t.value, bool):          # (bool avant int, voir base_of)
            return "true" if t.value else "false"
        if isinstance(t.value, str):           # un texte s'affiche entre guillemets
            return '"' + t.value + '"'
        return str(t.value)                    # un nombre s'affiche tel quel
    if isinstance(t, TUnion):                  # union
        if not t.members:                      # union vide
            return "Never"
        # sorted : toujours le même ordre d'affichage (utile pour les tests)
        return " | ".join(sorted(show(m) for m in t.members))
    if isinstance(t, TPair):                   # paire
        return "(" + show(t.fst) + " * " + show(t.snd) + ")"
    if isinstance(t, TFun):                    # fonction
        left = show(t.arg)                     # texte de l'argument
        right = show(t.ret)                    # texte du résultat
        # La flèche se lit de droite à gauche : a -> b -> c = a -> (b -> c).
        # Donc si l'argument est lui-même une fonction, il faut des parenthèses.
        if isinstance(t.arg, (TFun, TUnion)):
            left = "(" + left + ")"
        if isinstance(t.ret, TUnion):          # parenthèses pour la lisibilité
            right = "(" + right + ")"
        return left + " -> " + right
    raise ValueError(f"type inconnu : {t!r}")  # ne devrait jamais arriver


# -----------------------------------------------------------------------------
# Renommage : 't7 -> 't12 devient 'a -> 'b (plus joli à lire)
# -----------------------------------------------------------------------------
def rename(t):
    """Renomme les inconnues en 'a, 'b, 'c... dans leur ordre d'apparition."""
    names = {}                                 # ancienne variable -> nouveau nom

    def go(t):                                 # fonction interne récursive
        if isinstance(t, TVar):
            if t not in names:                 # première fois qu'on la voit :
                names[t] = TVar(chr(ord("a") + len(names)))  # a, puis b, puis c
            return names[t]
        if isinstance(t, TFun):                # on renomme dans les deux côtés
            return TFun(go(t.arg), go(t.ret))
        if isinstance(t, TPair):
            return TPair(go(t.fst), go(t.snd))
        if isinstance(t, TUnion):
            return TUnion(frozenset(go(m) for m in t.members))
        return t                               # TCon et TLit : rien à renommer

    return go(t)


# -----------------------------------------------------------------------------
# Sous-typage : « A est-il un cas particulier de B ? »
# Exemple : "rouge" est un Str, donc TLit("rouge") est un sous-type de STR.
# Ces fonctions servent au moteur de contraintes (constraints.py).
# -----------------------------------------------------------------------------
def base_of(lit: TLit) -> TCon:
    """Le type de base d'un singleton : "rouge" -> Str, 1 -> Int, True -> Bool."""
    # ATTENTION : en Python, True est aussi un int (True == 1) !
    # Il faut donc tester bool AVANT int, sinon True serait vu comme Int.
    if isinstance(lit.value, bool):
        return BOOL
    if isinstance(lit.value, int):
        return INT
    return STR


def is_subtype(s, t) -> bool:
    """Vrai si toute valeur de type s est aussi une valeur de type t (on écrit s <: t)."""
    if s == t:                                 # un type est sous-type de lui-même
        return True
    if isinstance(s, TUnion):                  # (A | B) <: T  si  A <: T  ET  B <: T
        return all(is_subtype(m, t) for m in s.members)
    if isinstance(t, TUnion):                  # S <: (A | B)  si  S <: A  OU  S <: B
        return any(is_subtype(s, m) for m in t.members)
    if isinstance(s, TLit) and isinstance(t, TCon):
        return base_of(s) == t                 # "rouge" <: Str, 1 <: Int
    if isinstance(s, TFun) and isinstance(t, TFun):
        # CONTRAVARIANCE : une fonction qui accepte PLUS d'arguments peut
        # remplacer une fonction qui en accepte moins. Le sens s'INVERSE
        # pour l'argument (t.arg <: s.arg) mais pas pour le résultat.
        return is_subtype(t.arg, s.arg) and is_subtype(s.ret, t.ret)
    if isinstance(s, TPair) and isinstance(t, TPair):
        return is_subtype(s.fst, t.fst) and is_subtype(s.snd, t.snd)
    return False                               # tous les autres cas : non


def make_union(types):
    """Construit l'union la plus simple possible à partir d'une liste de types.
    Exemples : [1, 1]       -> 1          (doublon retiré)
               [1, Int]     -> Int        (1 est déjà inclus dans Int)
               [1, "a"]     -> "a" | 1
               []           -> Never"""
    flat = []                                  # liste « aplatie »
    for t in types:
        if isinstance(t, TUnion):              # (A | B) | C  devient  A | B | C
            flat.extend(t.members)
        else:
            flat.append(t)
    unique = list(dict.fromkeys(flat))         # retire les doublons, garde l'ordre
    # On garde un membre seulement s'il n'est pas déjà inclus dans un AUTRE membre.
    kept = [m for m in unique
            if not any(m != o and is_subtype(m, o) for o in unique)]
    if len(kept) == 1:                         # un seul type : pas besoin d'union
        return kept[0]
    return TUnion(frozenset(kept))             # sinon : une vraie union
