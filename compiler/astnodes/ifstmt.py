from .stmt import Stmt
from .expr import Expr

class IfStmt(Stmt):

    def __init__(self, location:[int], condition:Expr, thenBody:[Stmt], elseBody:[Stmt]):
        super().__init__(location, "IfStmt")
        self.condition = condition
        self.thenBody = [s for s in thenBody if s is not None]
        self.elseBody = [s for s in elseBody if s is not None]

    def typecheck(self, typechecker):
        typechecker.typecheck(self.condition)
        typechecker.IfExpr(self)
        
        typechecker.enterScope()
        for s in self.thenBody:
            typechecker.typecheck(s)
        typechecker.exitScope()

        typechecker.enterScope()
        for s in self.elseBody:
            typechecker.typecheck(s)
        typechecker.exitScope()

    def toJSON(self):
        d = super().toJSON()
        d["condition"] = self.condition.toJSON()
        d["thenBody"] = [s.toJSON() for s in self.thenBody]
        d["elseBody"] = [s.toJSON() for s in self.elseBody]
        return d
