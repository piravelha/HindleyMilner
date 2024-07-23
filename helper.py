from typing import TypeAlias, overload, Any
from dataclasses import dataclass
from enum import Enum
from lark import Lark

with open("grammar.lark") as f:
  grammar = f.read()

parser = Lark(grammar)

MonoType: TypeAlias = """
  TypeVariable
  | TypeApplication
"""

PolyType: TypeAlias = """
  MonoType
  | TypeQuantifier
"""


class TypeFunction(Enum):
  Int = "Int"
  Bool = "Bool"
  Function = "->"
  List = "List"

@dataclass
class TypeVariable:
  name: str
  def __repr__(self):
    return self.name

@dataclass
class TypeApplication:
  name: TypeFunction
  args: list[MonoType]
  def __repr__(self):
    if self.name == TypeFunction.Function:
      return str(self.args[0]) + " -> " \
        + str(self.args[1])
    return " ".join(
      [str(self.name.value)] + [
        str(a) for a in self.args])

Int = TypeApplication(TypeFunction.Int, [])
Bool = TypeApplication(TypeFunction.Bool, [])
def Function(param: MonoType, body: MonoType):
  return TypeApplication(TypeFunction.Function, [param, body])
Var = TypeVariable

@dataclass
class TypeQuantifier:
  param: str
  body: PolyType
  def __repr__(self):
    return "forall " + self.param \
      + ". " + str(self.body)

class Context:
  def __init__(self, raw: dict[str, PolyType]):
    self.raw = raw
  def __repr__(self):
    return "Context(" + str(self.raw) + ")"

Applyable: TypeAlias = """
  MonoType
  | PolyType
  | Context
"""

RawSubstitution: TypeAlias = dict[str, MonoType]

class Substitution:
  @overload
  def apply(self, x: MonoType) -> MonoType: ...
  @overload
  def apply(self, x: PolyType) -> PolyType: ...
  @overload
  def apply(self, x: Context) -> Context: ...
  @overload
  def apply(self, x: 'Substitution') -> 'Substitution': ...
  def apply(self, x: Any) -> Any:
    if isinstance(x, Substitution):
      return combine(x, self)
    return apply(self, x)
  def __init__(self, raw: RawSubstitution):
    self.raw = raw
  def __repr__(self):
    return "Substitution(" + str(self.raw) + ")"

Mapping: TypeAlias = dict[str, TypeVariable]

#########
# APPLY #
#########

def apply(s: Substitution, value: Applyable):
  if isinstance(value, Context):
    return Context({k: apply(s, v)
      for k, v in value.raw.items()})
  if isinstance(value, TypeVariable):
    if s.raw.get(value.name):
      return s.raw[value.name]
    return value
  if isinstance(value, TypeApplication):
    return TypeApplication(
      value.name,
      [apply(s, a) for a in value.args])
  if isinstance(value, TypeQuantifier):
    return TypeQuantifier(
      value.param,
      apply(s, value.body))


###########
# COMBINE #
###########

def combine(a: Substitution, b: Substitution):
  result = a.raw.copy()
  for k, v in b.raw.items():
    result[k] = a.apply(v)
  return Substitution(result)


#####################
# NEW TYPE VARIABLE #
#####################

current_typevar = -1
def new_typevar() -> TypeVariable:
  global current_typevar
  current_typevar += 1
  letters = "abcdefghijklmnopqrstuvwxyz"
  mod = current_typevar % 26
  return TypeVariable("_" + letters[mod] + \
    str(int(current_typevar / 26) or ""))


###############
# INSTANTIATE #
###############

def instantiate(
    poly: PolyType,
    mappings: Mapping = {}) -> MonoType:
  if isinstance(poly, TypeVariable):
    return mappings.get(poly.name, poly)
  if isinstance(poly, TypeApplication):
    return TypeApplication(
      poly.name,
      [instantiate(a, mappings) for a in poly.args])
  if isinstance(poly, TypeQuantifier):
    mappings[poly.param] = new_typevar()
    return instantiate(poly.body, mappings)


##############
# GENERALIZE #
##############

def diff(a: list[str], b: list[str]) -> list[str]:
  bset = set(b)
  return [v for v in a if v not in bset]

def free_vars(poly: PolyType) -> list[str]:
  if isinstance(poly, TypeVariable):
    return [poly.name]
  if isinstance(poly, TypeApplication):
    return [x
      for a in poly.args
      for x in free_vars(a)]
  if isinstance(poly, TypeQuantifier):
    return [v
      for v in free_vars(poly.body)
      if v != poly.param]

def generalize(ctx: Context, mono: MonoType):
  ctx_free = [x
    for v in ctx.raw.values()
    for x in free_vars(v)]
  mono_free = free_vars(mono)
  frees = diff(mono_free, ctx_free)
  poly: PolyType = mono
  for free in frees:
    poly = TypeQuantifier(free, poly)
  return poly


#########
# UNIFY #
#########

def unify(a: MonoType, b: MonoType) -> Substitution:
  if isinstance(a, TypeVariable) and isinstance(b, TypeVariable) and a.name == b.name:
    return Substitution({})
  if isinstance(a, TypeVariable):
    return Substitution({a.name: b})
  if isinstance(b, TypeVariable):
    return Substitution({b.name: a})
  if a.name != b.name or len(a.args) != len(b.args):
    assert False
  combined = Substitution({})
  for a_, b_ in zip(a.args, b.args):
    combined = combined.apply(unify(
      combined.apply(a_),
      combined.apply(b_)))
  return combined
