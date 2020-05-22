from .stmt import Stmt
from .expr import Expr

class ReturnStmt(Stmt):

    def __init__(self, location:[int], value:Expr):
        super().__init__(location, "ReturnStmt")
        self.value = value

    def typecheck(self, typechecker):
        if self.value != None:
            typechecker.typecheck(self.value)
        typechecker.ReturnStmt(self)

    def toJSON(self):
        d = super().toJSON()
        d["value"] = self.value.toJSON()
        return d
