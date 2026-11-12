# Tests du moteur 1 (Hindley-Milner). Lancer avec : python -m pytest -q
import pytest
from typer.syntax import Lit, Var, Lam, App, Let, If, Pair
from typer.types import show
from typer.hm import infer, TypeError_


def t(e):
    """Raccourci : le type de e, sous forme de texte."""
    return show(infer(e))


def test_literals():
    assert t(Lit(1)) == "Int"
    assert t(Lit(True)) == "Bool"
    assert t(Lit("foo")) == "Str"


def test_identity():
    # fun x -> x  marche pour n'importe quel type 'a
    assert t(Lam("x", Var("x"))) == "'a -> 'a"


def test_application():
    assert t(App(Lam("x", Var("x")), Lit(True))) == "Bool"


def test_twice():
    # fun f -> fun x -> f (f x)
    e = Lam("f", Lam("x", App(Var("f"), App(Var("f"), Var("x")))))
    assert t(e) == "('a -> 'a) -> 'a -> 'a"


def test_pair():
    assert t(Pair(Lit(1), Lit(True))) == "(Int * Bool)"


def test_if_same_types():
    assert t(If(Lit(True), Lit(1), Lit(2))) == "Int"


def test_let_polymorphism():
    # let id = fun x -> x in (id 1, id true)
    # id est utilisé avec deux types différents : c'est le polymorphisme du let.
    e = Let("id", Lam("x", Var("x")),
            Pair(App(Var("id"), Lit(1)), App(Var("id"), Lit(True))))
    assert t(e) == "(Int * Bool)"


def test_lambda_param_is_not_polymorphic():
    # fun f -> (f 1, f true) : f est un paramètre, pas un let -> refusé
    e = Lam("f", Pair(App(Var("f"), Lit(1)), App(Var("f"), Lit(True))))
    with pytest.raises(TypeError_):
        infer(e)


def test_condition_must_be_bool():
    with pytest.raises(TypeError_):
        infer(If(Lit(1), Lit(1), Lit(2)))


def test_hm_rejects_union():
    # LA LIMITE DE HINDLEY-MILNER : deux branches de types différents.
    # Le moteur 2 (constraints.py) accepte ce programme.
    with pytest.raises(TypeError_):
        infer(If(Lit(True), Lit(1), Lit("a")))


def test_occurs_check():
    # fun x -> x x : demanderait un type infini
    with pytest.raises(TypeError_):
        infer(Lam("x", App(Var("x"), Var("x"))))


def test_unknown_variable():
    with pytest.raises(TypeError_):
        infer(Var("y"))
