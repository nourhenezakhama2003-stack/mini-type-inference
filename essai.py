# Démonstration : lancer avec  python essai.py
from typer.syntax import Lit, Var, Lam, App, Let, If, IfIs
from typer.types import show, BOOL, INT
from typer import hm, constraints

# Le programme :  if cond then 1 else "a"
prog = If(Var("cond"), Lit(1), Lit("a"))

# Moteur 1 : Hindley-Milner refuse (une valeur = un seul type)
try:
    print("HM          :", show(hm.infer(prog, {"cond": BOOL})))
except hm.TypeError_ as err:
    print("HM          : ERREUR ->", err)

# Moteur 2 : contraintes de sous-typage, accepte avec une union
print("Contraintes :", show(constraints.check(prog, {"cond": BOOL})))

# Occurrence typing :
#   let x = if cond then 1 else "a" in
#   if x is Int then add x 1 else length x
prog2 = Let("x", prog,
            IfIs("x", INT,
                 App(App(Var("add"), Var("x")), Lit(1)),
                 App(Var("length"), Var("x"))))
print("Occurrence  :", show(constraints.check(prog2, {"cond": BOOL})))
