# Tests du moteur 2 (contraintes de sous-typage). Lancer avec : python -m pytest -q
import pytest
from typer.syntax import Lit, Var, Lam, App, Let, If, Pair, IfIs
from typer.types import show, make_union, TLit, TFun, INT, STR, BOOL
from typer.constraints import check
from typer.solver import TypeError_


def t(e):
    """Raccourci : le type de e, sous forme de texte."""
    return show(check(e))


# Une condition dont on ne connaît pas la valeur : la variable « cond », de type Bool.
# (Avec Lit(True), on saurait d'avance quelle branche est prise.)
ENV = {"cond": BOOL}


def c():
    return Var("cond")


def tc(e):
    """Comme t(e), mais avec la variable « cond » disponible."""
    return show(check(e, ENV))


# --- Singletons -------------------------------------------------------------
def test_literal_is_singleton():
    assert t(Lit(5)) == "5"
    assert t(Lit("rouge")) == '"rouge"'


# --- Unions : ce que Hindley-Milner refuse ---------------------------------
def test_if_builds_union():
    assert tc(If(c(), Lit(1), Lit("a"))) == '"a" | 1'


def test_singleton_union():
    assert tc(If(c(), Lit("rouge"), Lit("vert"))) == '"rouge" | "vert"'


def test_union_absorbs_singleton():
    # 1 | Int se simplifie en Int, car 1 est déjà un Int
    e = If(c(), Lit(1), App(App(Var("add"), Lit(2)), Lit(3)))
    assert tc(e) == "Int"


# --- Inférence à partir de l'utilisation -----------------------------------
def test_param_inferred_from_use():
    # fun x -> add x 1   : x est passé à add, donc x : Int
    e = Lam("x", App(App(Var("add"), Var("x")), Lit(1)))
    assert t(e) == "Int -> Int"


def test_identity():
    assert t(Lam("x", Var("x"))) == "'a -> 'a"


def test_wrong_argument():
    with pytest.raises(TypeError_):
        check(App(Var("length"), Lit(5)))      # length attend un Str


# --- Singletons dans les annotations ---------------------------------------
FEU = make_union([TLit("rouge"), TLit("orange"), TLit("vert")])


def test_singleton_parameter_accepts():
    e = App(Lam("c", Var("c"), ann=FEU), Lit("rouge"))
    assert t(e) == '"orange" | "rouge" | "vert"'


def test_singleton_parameter_rejects():
    with pytest.raises(TypeError_):
        check(App(Lam("c", Var("c"), ann=FEU), Lit("bleu")))


# --- Contravariance ---------------------------------------------------------
def test_contravariance_ok():
    # apply_int attend une fonction Int -> Int.
    # On lui donne une fonction qui accepte PLUS (Int | Str) : c'est permis.
    apply_int = Lam("f", App(Var("f"), Lit(1)), ann=TFun(INT, INT))
    g = Lam("x", Lit(5), ann=make_union([INT, STR]))
    assert t(App(apply_int, g)) == "Int"


def test_contravariance_rejected():
    # apply_any attend une fonction qui accepte Int | Str.
    # On lui donne une fonction qui n'accepte QUE Int : refusé.
    apply_any = Lam("f", App(Var("f"), Lit(1)), ann=TFun(make_union([INT, STR]), INT))
    g = Lam("x", Lit(5), ann=INT)
    with pytest.raises(TypeError_):
        check(App(apply_any, g))


# --- Occurrence typing -------------------------------------------------------
def test_occurrence_typing():
    # let x = if cond then 1 else "a" in
    #   if x is Int then add x 1 else length x
    e = Let("x", If(c(), Lit(1), Lit("a")),
            IfIs("x", INT,
                 App(App(Var("add"), Var("x")), Lit(1)),   # ici x : 1
                 App(Var("length"), Var("x"))))             # ici x : "a"
    assert tc(e) == "Int"


def test_occurrence_typing_with_annotation():
    # fun (x: Int | Str) -> if x is Int then add x 1 else length x
    e = Lam("x", IfIs("x", INT,
                      App(App(Var("add"), Var("x")), Lit(1)),
                      App(Var("length"), Var("x"))),
            ann=make_union([INT, STR]))
    assert t(e) == "(Int | Str) -> Int"


def test_without_narrowing_it_fails():
    # Sans le test « is Int », add x 1 est refusé : x peut être un texte.
    e = Lam("x", App(App(Var("add"), Var("x")), Lit(1)), ann=make_union([INT, STR]))
    with pytest.raises(TypeError_):
        check(e)


def test_narrow_to_singleton():
    # fun (x: Str) -> if x is "ok" then x else "autre"
    e = Lam("x", IfIs("x", TLit("ok"), Var("x"), Lit("autre")), ann=STR)
    assert t(e) == 'Str -> ("autre" | "ok")'
