from .Expr import Expr
from .MemberExpr import MemberExpr

class MethodCallExpr(Expr):

    def __init__(self, location:[int], method:MemberExpr, args:[Expr]):
        super().__init__(location, "MethodCallExpr")
        self.method = method
        self.args = args

    def typecheck(self, typechecker):
        for a in self.args:
            typechecker.typecheck(a)
        typechecker.MethodCallExpr(self)

    def toJSON(self):
        d = super().toJSON()
        d["method"] = self.method.toJSON()
        d["args"] = [a.toJSON() for a in self.args]
        return d


