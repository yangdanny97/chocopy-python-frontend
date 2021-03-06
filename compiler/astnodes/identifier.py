from .expr import Expr

class Identifier(Expr):

    def __init__(self, location:[int], name:str):
        super().__init__(location, "Identifier")
        self.name = name

    def visit(self, typechecker):
        return typechecker.Identifier(self)

    def toJSON(self):
        d = super().toJSON()
        d["name"] = self.name
        return d

