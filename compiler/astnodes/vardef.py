from .declaration import Declaration
from .expr import Expr
from .typedvar import TypedVar

class VarDef(Declaration):

    def __init__(self, location:[int], var:[TypedVar], value:Expr, isAttr:bool=False):
        super().__init__(location, "VarDef")
        self.var = var
        self.value = value
        self.isAttr = isAttr

    def visitChildren(self, typechecker):
        typechecker.visit(self.value)
        return typechecker.VarDef(self)

    def visit(self, visitor):
        return visitor.VarDef(self)

    def toJSON(self, dump_location=True):
        d = super().toJSON(dump_location)
        d["var"] = self.var.toJSON(dump_location)
        d["value"] = self.value.toJSON(dump_location)
        return d

    def getIdentifier(self):
        return self.var.identifier
