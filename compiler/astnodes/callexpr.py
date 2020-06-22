from .expr import Expr
from .identifier import Identifier

class CallExpr(Expr):

    def __init__(self, location:[int], function:Identifier, args:[Expr]):
        super().__init__(location, "CallExpr")
        self.function = function
        self.args = args

    def visitChildren(self, typechecker):
        for a in self.args:
            typechecker.visit(a)
        return typechecker.CallExpr(self)

    def visit(self, visitor):
        return visitor.CallExpr(self)

    def toJSON(self, dump_location=True):
        d = super().toJSON(dump_location)
        d["function"] = self.function.toJSON(dump_location)
        d["args"] = [a.toJSON(dump_location) for a in self.args]
        return d


