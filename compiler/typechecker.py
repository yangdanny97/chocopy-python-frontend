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

        self.classes["object"] = {"__init__": FuncType([ObjectType()], NoneType())}
        self.classes["int"] = {"__init__": FuncType([ObjectType()], NoneType())}
        self.classes["bool"] = {"__init__": FuncType([ObjectType()], NoneType())}
        self.classes["str"] = {"__init__": FuncType([ObjectType()], NoneType())}

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

    def visit(self, node):
        return node.visit(self)

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

    def isSubtype(self, a: ValueType, b: ValueType) -> bool:
        # return if a is a subtype of b
        if b == self.OBJECT_TYPE:
            return True
        if isinstance(a, ClassValueType) and isinstance(b, ClassValueType):
            return self.isSubClass(a.className, b.className)
        return a == b

    def canAssign(self, a: ValueType, b: ValueType) -> bool:
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

    def join(self, a: ValueType, b: ValueType):
        # return closest mutual ancestor on typing tree
        if self.canAssign(a, b):
            return b
        if self.canAssign(b, a):
            return a
        if isinstance(b, ListValueType) and isinstance(a, ListValueType):
            return ListValueType(self.join(b.elementType, a.elementType))
        # if only 1 of the types is a list then the closest ancestor is object
        if isinstance(b, ListValueType) or isinstance(a, ListValueType):
            return self.OBJECT_TYPE
        # for 2 classes that aren't related by subtyping
        # find paths from A & B to root of typing tree
        aAncestors = []
        bAncestors = []
        while self.superclasses[a] is not None:
            aAncestors.append(self.superclasses[a])
            a = self.superclasses[a]
        while self.superclasses[b] is not None:
            aAncestors.append(self.superclasses[b])
            b = self.superclasses[b]
        # reverse lists to find lowest common ancestor
        aAncestors = aAncestors[::-1]
        bAncestors = bAncestors[::-1]
        for i in range(min(len(aAncestors), len(bAncestors))):
            if aAncestors[i] != bAncestors[i]:
                return aAncestors[i-1]
        # this really shouldn't be returned
        return self.OBJECT_TYPE

    # ERROR HANDLING

    def addError(self, node: Node, message: str):
        if node.errorMsg is not None: # 1 error msg per node
            return
        message = F"{message}. Line {node.location[0]} Col {node.location[1]}"
        node.errorMsg = message
        self.program.errors.errors.append(
            CompilerError(node.location, message))
        self.errors.append(message)

    def binopError(self, node):
        self.addError(node, "Cannot use operator {} on types {} and {}".format(
            node.operator, node.left.inferredType, node.right.inferredType))

    # DECLARATIONS (returns type of declaration, besides Program)

    def Program(self, node: Program):
        self.program = node
        for d in node.declarations:
            identifier = d.getIdentifier()
            if self.defInCurrentScope(identifier.name) or self.classExists(identifier.name):
                self.addError(
                    identifier, F"Duplicate declaration of identifier: {identifier.name}")
            if isinstance(d, ClassDef):
                className = d.name.name
                superclass = d.superclass.name
                if not self.classExists(superclass):
                    self.addError(d.superclass,
                                F"Unknown superclass: {superclass}")
                    continue
                if superclass in ["int", "bool", "str", className]:
                    self.addError(d.superclass,
                                F"Illegal superclass: {superclass}")
                    continue
                self.classes[d.name.name] = {}
                self.superclasses[className] = superclass
            if isinstance(d, FuncDef):
                self.addType(d.getIdentifier().name, self.getSignature(d))
            if isinstance(d, VarDef):
                self.addType(identifier.name, self.visit(d.var))
        for d in node.declarations:
            if d.getIdentifier().errorMsg is not None:
                continue
            self.visit(d)
        if len(self.errors) > 0:
            return
        for s in node.statements:
            self.visit(s)

    def VarDef(self, node: VarDef):
        varName = node.getIdentifier().name
        annotationType = self.visit(node.var)
        if not self.canAssign(node.value.inferredType, annotationType):
            self.addError(
                node, F"Expected {annotationType}, got {node.value.inferredType}")
        return annotationType

    def ClassDef(self, node: ClassDef):
        className = node.name.name
        self.currentClass = className
        # add all attrs and methods before checking method bodies
        for d in node.declarations:
            if isinstance(d, FuncDef):  # methods
                funcName = d.getIdentifier().name
                funcType = self.getSignature(d)
                if funcName in self.classes[className]:
                    self.addError(d.getIdentifier(),
                                  F"Duplicate declaration of identifier: {funcName}")
                    continue
                t = self.getAttrOrMethod(className, funcName)
                if t is not None:
                    if not isinstance(t, FuncType):
                        self.addError(d.getIdentifier(), 
                        F"Method name shadows attribute: {funcName}")
                        continue
                    # if funcName != "__init__":  # for all methods besides constructor, check signatures match
                    if not t.methodEquals(funcType):  # excluding self argument
                        self.addError(d.getIdentifier(), 
                        F"Redefined method doesn't match superclass signature: {funcName}")
                        continue
                self.classes[className][funcName] = funcType
            if isinstance(d, VarDef):  # attributes
                attrName = d.getIdentifier().name
                if self.getAttrOrMethod(className, attrName):
                    self.addError(d.getIdentifier(),
                                  F"Cannot redefine attribute: {attrName}")
                    continue
                self.classes[className][attrName] = self.visit(d.var)
        for d in node.declarations:
            self.visit(d)
        self.currentClass = None
        return None

    def getSignature(self, node:FuncDef):
        rType = self.visit(node.returnType)
        return FuncType([self.visit(t) for t in node.params], rType)

    def FuncDef(self, node: FuncDef):
        self.enterScope()
        funcName = node.getIdentifier().name
        rType = self.visit(node.returnType)
        funcType = FuncType([self.visit(t) for t in node.params], rType)
        self.expReturnType = rType
        if not node.isMethod:  # top level function decl OR nested function
            if self.classExists(funcName):
                self.addError(node.getIdentifier(),
                              F"Functions cannot shadow classes: {funcName}")
                return
            if self.defInCurrentScope(funcName):
                self.addError(node.getIdentifier(
                ), F"Duplicate declaration of identifier: {funcName}")
                return
            self.addType(funcName, funcType)
        else:  # method decl
            if (len(node.params) == 0 or node.params[0].identifier.name != "self" or
                    (not isinstance(funcType.parameters[0], ClassValueType)) or
                    funcType.parameters[0].className != self.currentClass):
                self.addError(
                    node.getIdentifier(), F"Missing self param in method: {funcName}")
                return
        for p in node.params:
            t = self.visit(p)
            pName = p.identifier.name
            if self.defInCurrentScope(pName) or self.classExists(pName):
                self.addError(
                    p.identifier, F"Duplicate parameter name: {pName}")
                continue
            if t is not None:
                self.addType(pName, t)
        
        for d in node.declarations:
            identifier = d.getIdentifier()
            name = identifier.name
            if self.defInCurrentScope(name) or self.classExists(name):
                self.addError(
                    identifier, F"Duplicate declaration of identifier: {name}")
                continue
            if isinstance(d, FuncDef):
                self.addType(name, self.getSignature(d))
            if isinstance(d, VarDef):
                self.addType(name, self.visit(d.var))
            if isinstance(d, NonLocalDecl) or isinstance(d, GlobalDecl):
                self.addType(name, self.visit(d))     
        for d in node.declarations:
            self.visit(d)
            self.expReturnType = rType
        hasReturn = False
        for s in node.statements:
            self.visit(s)
            if s.isReturn:
                hasReturn = True
        if (not hasReturn) and (not self.canAssign(self.NONE_TYPE, self.expReturnType)):
            self.addError(node.getIdentifier(), F"Expected return statement of type {self.expReturnType}")
        self.expReturnType = None
        self.exitScope()
        return funcType

    # STATEMENTS (returns None) AND EXPRESSIONS (returns inferred type)

    def NonLocalDecl(self, node: NonLocalDecl):
        if self.expReturnType is None:
            self.addError(node, "Nonlocal decl outside of function")
            return
        identifier = node.getIdentifier()
        name = identifier.name
        t = self.getNonLocalType(name)
        if t is None or not isinstance(t, ValueType):
            self.addError(
                identifier, F"Unknown nonlocal variable: {name}")
            return
        return t

    def GlobalDecl(self, node: GlobalDecl):
        if self.expReturnType is None:
            self.addError(node, "Global decl outside of function")
            return
        identifier = node.getIdentifier()
        name = identifier.name
        t = self.getGlobal(name)
        if t is None or not isinstance(t, ValueType):
            self.addError(
                identifier, F"Unknown global variable: {name}")
            return
        return t

    def AssignStmt(self, node: AssignStmt):
        # variables can only be assigned to if they're defined in current scope
        if len(node.targets) > 1 and node.value.inferredType == ListValueType(self.NONE_TYPE):
            self.addError(node.value, "Multiple assignment of [<None>] is forbidden")
        else:
            for t in node.targets:
                if isinstance(t, IndexExpr) and t.list.inferredType == self.STR_TYPE:
                    self.addError(t, F"Cannot assign to index of string")
                    return
                if isinstance(t, Identifier) and not self.defInCurrentScope(t.name):
                    self.addError(t, F"Identifier not defined in current scope: {t.name}")
                    return
                if not self.canAssign(node.value.inferredType, t.inferredType):
                    self.addError(node, F"Expected {t.inferredType}, got {node.value.inferredType}")
                    return

    def IfStmt(self, node: IfStmt):
        # isReturn=True if there's >=1 statement in BOTH branches that have isReturn=True
        # if a branch is empty, isReturn=False
        if node.condition.inferredType != self.BOOL_TYPE:
            self.addError(
                node.condition, F"Expected {self.BOOL_TYPE}, got {node.condition.inferredType}")
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
        operator = node.operator
        static_types = {self.INT_TYPE, self.BOOL_TYPE, self.STR_TYPE}
        leftType = node.left.inferredType
        rightType = node.right.inferredType

        # concatenation and addition
        if operator == "+":
            if isinstance(leftType, ListValueType) and isinstance(rightType, ListValueType):
                node.inferredType = ListValueType(self.join(leftType.elementType, rightType.elementType))
                return node.inferredType
            elif leftType == rightType and leftType in {self.STR_TYPE, self.INT_TYPE}:
                node.inferredType = leftType
                return leftType
            else:
                self.binopError(node)

        # other arithmetic operators
        elif operator in {"-", "*", "//", "%"}:
            if leftType == self.INT_TYPE and rightType == self.INT_TYPE:
                node.inferredType = self.INT_TYPE
                return self.INT_TYPE
            else:
                self.binopError(node)

        # relational operators
        elif operator in {"<", "<=", ">", ">="}:
            if leftType == self.INT_TYPE and rightType == self.INT_TYPE:
                node.inferredType = self.BOOL_TYPE
                return self.BOOL_TYPE
            else:
                self.binopError(node)
        elif operator in {"==", "!="}:
            if leftType == rightType and \
                    leftType in static_types:
                node.inferredType = self.BOOL_TYPE
                return self.BOOL_TYPE
            else:
                self.binopError(node)
        elif operator == "is":
            if leftType not in static_types and rightType not in static_types:
                node.inferredType = self.BOOL_TYPE
                return self.BOOL_TYPE
            else:
                self.binopError(node)

        # logical operators
        elif operator in {"and", "or"}:
            if leftType == self.BOOL_TYPE and rightType == self.BOOL_TYPE:
                node.inferredType = self.BOOL_TYPE
                return self.BOOL_TYPE
            else:
                self.binopError(node)

        else:
            node.inferredType = self.OBJECT_TYPE
            return self.OBJECT_TYPE

    def IndexExpr(self, node: IndexExpr):
        if node.index.inferredType != self.INT_TYPE:
            self.addError(node, F"Expected {self.INT_TYPE} index, got {node.index.inferredType}")
        # indexing into a string returns a new string
        if node.list.inferredType == self.STR_TYPE:
            node.inferredType = self.STR_TYPE
            return node.inferredType
        # indexing into a list of type T returns a value of type T
        elif isinstance(node.list.inferredType, ListValueType):
            node.inferredType = node.list.inferredType.elementType
            return node.inferredType
        else:
            self.addError(node, F"Cannot index into {node.list.inferredType}")
            node.inferredType = self.OBJECT_TYPE
            return self.OBJECT_TYPE

    def UnaryExpr(self, node: UnaryExpr):
        operandType = node.operand.inferredType
        if node.operator == "-":
            if operandType == self.INT_TYPE:
                node.inferredType = self.INT_TYPE
                return self.INT_TYPE
            else:
                self.addError(node, F"Expected int, got {operandType}")
        elif node.operator == "not":
            if operandType == self.BOOL_TYPE:
                node.inferredType = self.BOOL_TYPE
                return self.BOOL_TYPE
            else:
                self.addError(node, F"Expected bool, got {operandType}")
        else:
            node.inferredType = self.OBJECT_TYPE
            return self.OBJECT_TYPE

    def CallExpr(self, node: CallExpr):
        fname = node.function.name
        t = None
        if self.classExists(fname):
            # constructor
            t = self.getMethod(fname, "__init__")
            if len(t.parameters) != len(node.args) + 1:
                self.addError(node, F"Expected {len(t.parameters) - 1} args, got {len(node.args)}")
            else:
                for i in range(len(t.parameters) - 1):
                    if not self.canAssign(node.args[i].inferredType, t.parameters[i + 1]):
                        self.addError(node, F"Expected {t.parameters[i + 1]}, got {node.args[i].inferredType}")
                        continue
            node.inferredType = ClassValueType(fname)
        else:
            t = self.getType(fname)
            if not isinstance(t, FuncType):
                self.addError(node, F"Not a function: {fname}")
                node.inferredType = self.OBJECT_TYPE
                return self.OBJECT_TYPE
            if len(t.parameters) != len(node.args):
                self.addError(node, F"Expected {len(t.parameters)} args, got {len(node.args)}")
            else:
                for i in range(len(t.parameters)):
                    if not self.canAssign(node.args[i].inferredType, t.parameters[i]):
                        self.addError(node, F"Expected {t.parameters[i]}, got {node.args[i].inferredType}")
                        continue
            node.inferredType = t.returnType
        node.function.inferredType = t
        return node.inferredType

    def ForStmt(self, node: ForStmt):
        # set isReturn=True if any statement in body has isReturn=True
        iterType = node.iterable.inferredType
        if isinstance(iterType, ListValueType):
            if not self.canAssign(iterType.elementType, node.identifier.inferredType):
                self.addError(
                    node.identifier, F"Expected {iterType.elementType}, got {node.identifier.inferredType}")
                return
        elif self.STR_TYPE == iterType:
            if not self.canAssign(self.STR_TYPE, node.identifier.inferredType):
                self.addError(
                    node.identifier, F"Expected {self.STR_TYPE}, got {node.identifier.inferredType}")
                return
        else:
            self.addError(
                node.iterable, F"Expected iterable, got {node.iterable.inferredType}")
            return
        for s in node.body:
            if s.isReturn:
                node.isReturn = True

    def ListExpr(self, node: ListExpr):
        if len(node.elements) == 0:
            node.inferredType = self.EMPTY_TYPE
        else:
            e_type = node.elements[0].inferredType
            for e in node.elements:
                e_type = self.join(e_type, e.inferredType)
            node.inferredType = ListValueType(e_type)
        return node.inferredType

    def WhileStmt(self, node: WhileStmt):
        if node.condition.inferredType != self.BOOL_TYPE:
            self.addError(
                node.condition, F"Expected {self.BOOL_TYPE}, got {node.condition.inferredType}")
            return
        for s in node.body:
            if s.isReturn:
                node.isReturn = True

    def ReturnStmt(self, node: ReturnStmt):
        if self.expReturnType is None:
            self.addError(
                node, "Return statement outside of function definition")
        elif node.value is None:
            if  not self.canAssign(self.NONE_TYPE, self.expReturnType):
                self.addError(
                    node, F"Expected {self.expReturnType}, got {self.NONE_TYPE}")
        elif not self.canAssign(node.value.inferredType, self.expReturnType):
            self.addError(
                node, F"Expected {self.expReturnType}, got {node.value.inferredType}")
        return

    def Identifier(self, node: Identifier):
        varType = None
        if self.expReturnType is None and self.currentClass is None:
            varType = self.getGlobal(node.name)
        else:
            varType = self.getType(node.name)
        if varType is not None and isinstance(varType, ValueType):
            node.inferredType = varType
        else:
            self.addError(node, F"Unknown identifier: {node.name}")
            node.inferredType = self.OBJECT_TYPE
        return node.inferredType

    def MemberExpr(self, node: MemberExpr):
        static_types = {self.INT_TYPE, self.BOOL_TYPE, self.STR_TYPE}
        if node.object.inferredType in static_types or not isinstance(node.object.inferredType, ClassValueType): 
            self.addError(node, F"Expected object, got {node.object.inferredType}")
        else:
            class_name, member_name = node.object.inferredType.className, node.member.name
            if self.getAttr(class_name, member_name) is None:
                self.addError(node, F"Attribute {member_name} doesn't exist for class {class_name}")
                node.inferredType = self.OBJECT_TYPE
                return self.OBJECT_TYPE
            else:
                node.inferredType = self.getAttr(class_name, member_name)
        return node.inferredType 

    def IfExpr(self, node: IfExpr):
        if node.condition.inferredType != self.BOOL_TYPE:
            self.addError(F"Expected boolean, got {node.condition.inferredType}")
        node.inferredType = self.join(node.thenExpr.inferredType, node.elseExpr.inferredType)
        return node.inferredType

    def MethodCallExpr(self, node: MethodCallExpr):
        method_member = node.method
        self.visit(method_member.object)
        t = None # method signature
        static_types = {self.INT_TYPE, self.BOOL_TYPE, self.STR_TYPE}
        if method_member.object.inferredType in static_types or not isinstance(method_member.object.inferredType, ClassValueType): 
            self.addError(method_member, F"Expected object, got {method_member.object.inferredType}")
            node.inferredType = self.OBJECT_TYPE
            return node.inferredType
        else:
            class_name, member_name = method_member.object.inferredType.className, method_member.member.name
            if self.getMethod(class_name, member_name) is None:
                self.addError(node, F"Method {member_name} doesn't exist for class {class_name}")
                node.inferredType = self.OBJECT_TYPE
                return node.inferredType
            else:
                t = self.getMethod(class_name, member_name) 
        # self arguments
        if len(t.parameters) != len(node.args) + 1:
            self.addError(node, F"Expected {len(t.parameters) - 1} args, got {len(node.args)}")
        else:
            for i in range(len(t.parameters) - 1):
                if not self.canAssign(node.args[i].inferredType, t.parameters[i + 1]):
                    self.addError(node, F"Expected {t.parameters[i + 1]}, got {node.args[i].inferredType}")
                    continue
        node.method.inferredType = t
        node.inferredType = t.returnType
        return node.inferredType

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
        return self.visit(node.type)

    def ListType(self, node: ListType):
        return ListValueType(self.visit(node.elementType))

    def ClassType(self, node: ClassType):
        if node.className not in {"<None>", "<Empty>"} and not self.classExists(node.className):
            self.addError(node, F"Unknown class: {node.className}")
            return self.OBJECT_TYPE
        else:
            return ClassValueType(node.className)
