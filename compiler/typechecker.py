from .astnodes import *
from .types import *
from collections import defaultdict


class TypeChecker:
    def __init__(self):
        # typechecker attributes and their chocopy typing judgement analogues:
        # O : symbolTable
        # M : classes
        # C : currentClass
        # R : expReturnType

        # stack of hashtables representing scope
        # each table holds identifier->type mappings defined in that scppe
        self.symbolTable = [defaultdict(lambda: None)]

        # standard library functions
        self.symbolTable[0]["print"] = FuncType([ObjectType()], NoneType())
        self.symbolTable[0]["input"] = FuncType([], StrType())
        self.symbolTable[0]["len"] = FuncType([ObjectType()], IntType())

        # type hierachy: dictionary of class->superclass mappings
        self.superclasses = defaultdict(lambda: None)

        # set up default class hierarchy
        self.superclasses["object"] = None
        self.superclasses["int"] = "object"
        self.superclasses["bool"] = "object"
        self.superclasses["str"] = "object"
        self.superclasses["<None>"] = "object"
        self.superclasses["<Empty>"] = "object"

        # symbol tables for each class's methods
        self.classes = defaultdict(lambda: {})

        self.classes["object"] = {"__init__": FuncType([], ObjectType())}
        self.classes["int"] = {"__init__": FuncType([], IntType())}
        self.classes["bool"] = {"__init__": FuncType([], BoolType())}
        self.classes["str"] = {"__init__": FuncType([], StrType())}

        self.INT_TYPE = IntType()
        self.STR_TYPE = StrType()
        self.BOOL_TYPE = BoolType()
        self.NONE_TYPE = NoneType()
        self.EMPTY_TYPE = EmptyType()
        self.OBJECT_TYPE = ObjectType()

        self.errors = []  # list of errors encountered
        self.currentClass = None  # name of current class
        self.expReturnType = None  # expected return type of current function

        self.program = None

    def typecheck(self, node):
        node.typecheck(self)

    def enterScope(self):
        self.symbolTable.append(defaultdict(lambda: None))

    def exitScope(self):
        self.symbolTable.pop()

    # SYMBOL TABLE LOOKUPS

    def getType(self, var: str):
        # get the type of an identifier in the current scope, or None if not found
        for table in self.symbolTable[::-1]:
            if var in table:
                return table[var]
        return None

    def getLocalType(self, var: str):
        # get the type of an identifier in the current scope, or None if not found
        # ignore global variables
        for table in self.symbolTable[1:][::-1]:
            if var in table:
                return table[var]
        return None

    def getNonLocalType(self, var: str):
        # get the type of an identifier outside the current scope, or None if not found
        # ignore global variables
        for table in self.symbolTable[1:-1][::-1]:
            if var in table:
                return table[var]
        return None

    def getGlobal(self, var: str):
        return self.symbolTable[0][var]

    def addType(self, var: str, t: SymbolType):
        self.symbolTable[-1][var] = t

    def defInCurrentScope(self, var: str) -> bool:
        # return if the name was defined in the current scope
        return self.symbolTable[-1][var] is not None

    # CLASSES

    def getMethod(self, className: str, methodName: str):
        if methodName not in self.classes[className]:
            if self.superclasses[className] is None:
                return None
            return self.getMethod(self.superclasses[className], methodName)
        if not isinstance(self.classes[className][methodName], FuncType):
            return None
        return self.classes[className][methodName]

    def getAttr(self, className: str, attrName: str):
        if attrName not in self.classes[className]:
            if self.superclasses[className] is None:
                return None
            return self.getAttr(self.superclasses[className], attrName)
        if not isinstance(self.classes[className][attrName], ValueType):
            return None
        return self.classes[className][attrName]

    def getAttrOrMethod(self, className: str, name: str):
        if name not in self.classes[className]:
            if self.superclasses[className] is None:
                return None
            return self.getAttrOrMethod(self.superclasses[className], name)
        return self.classes[className][name]

    def classExists(self, className: str) -> bool:
        # we cannot check for None because it is a defaultdict
        return className in self.classes

    # TYPE HIERARCHY UTILS

    def isSubClass(self, a: str, b: str) -> bool:
        # return if a is the same class or subclass of b
        curr = a
        while curr is not None:
            if curr == b:
                return True
            else:
                curr = self.superclasses[curr]
        return False

    def isSubtype(self, a: SymbolType, b: SymbolType) -> bool:
        # return if a is a subtype of b
        if b == self.OBJECT_TYPE:
            return True
        if isinstance(a, ClassValueType) and isinstance(b, ClassValueType):
            return self.isSubClass(a.className, b.className)
        return a == b

    def canAssign(self, a: SymbolType, b: SymbolType) -> bool:
        # return if value of type a can be assigned/passed to type b (ex: b = a)
        if self.isSubtype(a, b):
            return True
        if a == self.NONE_TYPE and b not in [self.INT_TYPE, self.STR_TYPE, self.BOOL_TYPE]:
            return True
        if isinstance(b, ListValueType) and a == self.EMPTY_TYPE:
            return True
        if (isinstance(b, ListValueType) and isinstance(a, ListValueType)
                and a.elementType == self.NONE_TYPE):
            return self.canAssign(a.elementType, b.elementType)
        return False

    # ERROR HANDLING

    def addError(self, node: Node, message: str):
        message = "Semantic Error: {}. Line {:d} Col {:d}".format(
            message, node.location[0], node.location[1])
        node.errorMsg = message
        self.program.errors.errors.append(
            CompilerError(node.location, message))
        self.errors.append(message)

    # DECLARATIONS (returns type of declaration, besides Program)

    def Program(self, node: Program):
        self.program = node
        # add all classnames before checking globals/functions/class decl bodies
        for d in self.declarations:
            if isinstance(d, ClassDef):
                if self.classExists(className):
                    self.addError(
                        node.name, "Classes cannot shadow other classes: {}".format(node.name))
                    continue
                self.classes[className] = {}
        for d in self.declarations:
            identifier = d.getIdentifier()
            name = identifier.name
            if self.defInCurrentScope(name) or self.classExists(name):
                self.addError(
                    identifier, "Duplicate declaration of identifier: {}".format(name))
                continue
            dType = d.typecheck(self)
            if dType is not None:
                self.addType(name, dType)
        for s in self.statements:
            s.typecheck(self)

    def VarDef(self, node: VarDef):
        varName = node.getIdentifier().name
        annotationType = self.typecheck(node.var.type)
        if not canAssign(node.value.inferredType, annotationType):
            self.addError(node, "Expected {}, got {}".format(
                str(annotationType), str(node.value.inferredType)))
            # TODO is this attached to the right node? do we return anything special
        return annotationType

    def ClassDef(self, node: ClassDef):
        className = node.name.name
        self.currentClass = className
        superclass = node.superclass.name
        if not self.classExists(superclass):
            self.addError(node.superclass,
                          "Unknown superclass: {}".format(node.name))
        if superclass in ["int", "bool", "str", className]:
            self.addError(node.superclass,
                          "Illegal superclass: {}".format(node.name))
        self.superclasses[className, superclass]
        # add all attrs and methods before checking method bodies
        for d in node.declarations:
            if isinstance(d, FuncDef):  # methods
                funcName = d.getIdentifier().name
                if self.classes[className][funcName]:
                    self.addError(node.getIdentifier(),
                                  "Duplicate declaration of identifier: {}".format(funcName))
                    continue
                t = self.getAttrOrMethod(className, funcName)
                if not isinstance(t, FuncType):
                    self.addError(node.getIdentifier(
                    ), "Method name shadows attribute: {}".format(funcName))
                    continue
                if funcName != "__init__":  # for all methods besides constructor, check signatures match
                    if not t.methodEquals(funcType):  # excluding self argument
                        self.addError(node.getIdentifier(
                        ), "Redefined method doesn't match superclass signature: {}".format(funcName))
                        continue
                self.classes[className][funcName] = FuncType([t for t in self.typecheck(
                    d.params)], self.typecheck(d.returnType))
            if isinstance(d, VarDef):  # attributes
                attrName = d.getIdentifier().name
                if self.getAttrOrMethod(className, attrName):
                    self.addError(node.getIdentifier(),
                                  "Cannot redefine attribute: {}".format(funcName))
                    continue
                self.classes[className][attrName] = self.typecheck(d.var)
        for d in node.declarations:
            node.typecheck(self)
        self.currentClass = None
        return None

    def FuncDef(self, node: FuncDef):
        funcName = node.getIdentifier().name
        rType = self.typecheck(d.returnType)
        funcType = FuncType([t for to in self.typecheck(
                            d.params)], rType)
        self.expReturnType = rType
        if not node.isMethod:  # top level function decl OR nested function
            if self.classExists(funcName):
                self.addError(node.getIdentifier(),
                              "Functions cannot shadow classes: {}".format(funcName))
                return
            if self.defInCurrentScope(funcName):
                self.addError(node.getIdentifier(
                ), "Duplicate declaration of identifier: {}".format(funcName))
                return
        else:  # method decl
            if (len(node.params) == 0 or node.params[0].identifier.name != "self" or
                    (not isinstance(funcType.parameters[0], ClassValueType)) or
                    funcType.parameters[0].className != self.currentClass):
                self.addError(
                    node, "Missing self argument in method: {}".format(funcName))
                return
        for p in node.params:
            t = self.typecheck(p)
            if self.defInCurrentScope(p.identifier.name) or self.classExists(name):
                self.addError(
                    p.identifier, "Duplicate parameter name: {}".format(name))
                continue
            if t is not None:
                self.addType(p.identifier.name, t)
        for d in node.declarations:
            identifier = d.getIdentifier()
            name = identifier.name
            if self.defInCurrentScope(name) or self.classExists(name):
                self.addError(
                    identifier, "Duplicate declaration of identifier: {}".format(name))
                continue
            dType = d.typecheck(self)
            if dType is not None:
                self.addType(name, dType)
        hasReturn = False
        for s in node.statements:
            self.typecheck(s)
            if s.isReturn:
                hasReturn = True
        if not hasReturn and self.expReturnType != self.NONE_TYPE:
            self.addError(node.statements[-1], "Expected return statement")
        self.expReturnType = None
        return funcType

    # STATEMENTS (returns None) AND EXPRESSIONS (returns inferred type)

    def NonLocalDecl(self, node: NonLocalDecl):
        if self.expReturnType is None:
            self.addError(node, "Nonlocal decl outside of function")
            return
        identifier = node.identifier
        name = identifier.name
        t = self.getNonLocalType(name)
        if t is None or not isinstance(t, ValueType):
            self.addError(
                identifier, "Unknown nonlocal variable: {}".format(name))
            return
        return t

    def GlobalDecl(self, node: GlobalDecl):
        if self.expReturnType is None:
            self.addError(node, "Global decl outside of function")
            return
        identifier = node.identifier
        name = identifier.name
        t = self.getGlobal(name)
        if t is None or not isinstance(t, ValueType):
            self.addError(
                identifier, "Unknown global variable: {}".format(name))
            return
        return t

    def AssignStmt(self, node: AssignStmt):
        # variables can only be assigned to if they're defined in current scope
        pass # TODO

    def IfStmt(self, node: IfStmt):
        # isReturn=True if there's >=1 statement in BOTH branches that have isReturn=True
        # if a branch is empty, isReturn=False 
        if node.condition.inferredType != self.BOOL_TYPE:
            self.addError(node.condition, "Expected {}, got {}".format(
                str(self.BOOL_TYPE), str(node.condition.inferredType))
            return
        thenBody = False
        elseBody = False
        for s in node.thenBody:
            if s.isReturn:
                thenBody = True
        for s in node.elseBody:
            if s.isReturn:
                elseBody = True
        node.isReturn = (thenBody and elseBody)

    def BinaryExpr(self, node: BinaryExpr):
        return node.inferredType # TODO

    def IndexExpr(self, node: IndexExpr):
        return node.inferredType # TODO

    def UnaryExpr(self, node: UnaryExpr):
        return node.inferredType # TODO

    def CallExpr(self, node: CallExpr):
        return node.inferredType # TODO

    def ForStmt(self, node: ForStmt):
        # set isReturn=True if any statement in body has isReturn=True
        iterType = node.iterable.inferredType
        if isinstance(iterType, ListValueType):
            if self.canAssign(iterType.elementType, node.identifier.inferredType):
                self.addError(node.condition, "Expected {}, got {}".format(
                    str(node.identifier.inferredType), str(iterType.elementType))
                    return
        elif self.STR_TYPE == iterType:
            if self.canAssign(self.STR_TYPE, node.identifier.inferredType):
                self.addError(node.condition, "Expected {}, got {}".format(
                    str(node.identifier.inferredType), str(self.STR_TYPE))
                    return
        else:
            self.addError(node.condition, "Expected iterable, got {}".format(str(node.condition.inferredType))
            return
        for s in node.body:
            if s.isReturn:
                node.isReturn = True

    def ListExpr(self, node: ListExpr):
        if len(elements) == 0:
            node.inferredType = self.EMPTY_TYPE
        return node.inferredType # TODO

    def WhileStmt(self, node: WhileStmt):
        if node.condition.inferredType != self.BOOL_TYPE:
            self.addError(node.condition, "Expected {}, got {}".format(
                str(self.BOOL_TYPE), str(node.condition.inferredType))
            return
        for s in node.body:
            if s.isReturn:
                node.isReturn = True

    def ReturnStmt(self, node: ReturnStmt):
        if self.expReturnType is None:
            self.addError(
                node, "Return statement outside of function definition")
        elif node.value is None and not self.canAssign(self.NONE_TYPE, self.expReturnType):
            self.addError(node, "Expected {}, got {}".format(
                str(self.expReturnType), str(node.value.inferredType)))
        elif not self.canAssign(node.value.inferredType, self.expReturnType):
            self.addError(node, "Expected {}, got {}".format(
                str(self.expReturnType), str(node.value.inferredType)))
        return

    def Identifier(self, node: Identifier):
        varType = self.getLocalType(node.name)
        if varType is not None and isinstance(varType, ValueType):
            node.inferredType = varType
        else:
            self.addError(node, "Not a variable: {}".format(node.name))
            node.inferredType = self.OBJECT_TYPE
        return node.inferredType

    def MemberExpr(self, node: MemberExpr):
        return node.inferredType # TODO

    def IfExpr(self, node: IfExpr):
        return node.inferredType # TODO

    def MethodCallExpr(self, node: MethodCallExpr):
        return node.inferredType # TODO

    # LITERALS

    def BooleanLiteral(self, node: BooleanLiteral):
        node.inferredType = BoolType()
        return node.inferredType

    def IntegerLiteral(self, node: IntegerLiteral):
        node.inferredType = IntType()
        return node.inferredType

    def NoneLiteral(self, node: NoneLiteral):
        node.inferredType = NoneType()
        return node.inferredType

    def StringLiteral(self, node: StringLiteral):
        node.inferredType = StrType()
        return node.inferredType

    # TYPES

    def TypedVar(self, node: TypedVar):
        # return the type of the annotaton
        return self.typecheck(node.type)

    def ListType(self, node: ListType):
        return ListValueType(node.elementType.typecheck(self))

    def ClassType(self, node: ClassType):
        if not self.classExists(node.name):
            self.addError(node, "Unknown class: {}".format(node.name))
            return ClassValueType(node.className)
        else:
            return self.OBJECT_TYPE
