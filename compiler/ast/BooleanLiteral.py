from Literal import Literal

class BooleanLiteral(Literal):

    def __init__(self, location:[int], value:bool):
        super().__init__(self, location, "BooleanLiteral")
        self.value = value

    def typecheck(self, typechecker):
        typechecker.BooleanLiteral(self)


