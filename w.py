from helper import *
from lark import Tree, Token

def W(env: Context, expr: Tree | Token) \
    -> tuple[Substitution, MonoType]:
  if isinstance(expr, Token):
    return Substitution({}), instantiate(env.raw[expr.value])
  if expr.data == "abstraction":
    param, body = expr.children
    param = str(param)
    beta = new_typevar()
    env.raw.update({param: beta})
    s1, t1 = W(env, body)
    return s1, s1.apply(TypeApplication(
      TypeFunction.Function,
      [beta, t1]))
  if expr.data == "application":
    left, right = expr.children
    beta = new_typevar()
    s1, t1 = W(env, left)
    s2, t2 = W(s1.apply(env), right)
    s3 = unify(s2.apply(t1), TypeApplication(
      TypeFunction.Function,
      [t2, beta]))
    return s3.apply(s2.apply(s1)), s3.apply(beta)
  assert False, "lol Komik"

text = """
  (x.x z) y
"""

tree = parser.parse(text)
s, type = W(Context({
  "y": Function(Int, Bool),
  "z": Int,
}), tree)
print(type)
