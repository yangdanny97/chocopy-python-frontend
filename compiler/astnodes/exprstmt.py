from .stmt import Stmt
from .expr import Expr

class ExprStmt(Stmt):

    def __init__(self, location:[int], expr:Expr):
        super().__init__(location, "ExprStmt")
        self.expr = expr

    def visit(self, typechecker):
        typechecker.visit(self.expr)

    def toJSON(self):
        d = super().toJSON()
        d["expr"] = self.expr.toJSON()
        return d

