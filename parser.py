
from collections import namedtuple

class ASTNode:
    def __init__(self, type_, value=None, children=None, line=0):
        self.type = type_
        self.value = value
        self.children = children or []
        self.line = line

    def add_child(self, node):
        if node is not None:
            self.children.append(node)
        return self

    def __repr__(self):
        if self.value is not None:
            return f"{self.type}({self.value})"
        return f"{self.type}"

class ParseError(Exception):
    def __init__(self, msg, token=None):
        super().__init__(msg)
        self.token = token

class Parser:
    # binary operator precedence (higher number = binds tighter). Unary
    # operators live in their own table: '&', '*', '+' and '-' are both, and
    # one shared dict let the unary entries overwrite the binary ones (so
    # `a + b * c` parsed as `(a + b) * c`).
    ASSIGN_OPS = ('=', '+=', '-=', '*=', '/=', '%=', '<<=', '>>=')
    PRECEDENCE = {
        **{op: 1 for op in ASSIGN_OPS},     # right-associative, lowest
        '||': 2,
        '&&': 3,
        '|': 4,
        '^': 5,
        '&': 6,
        '==': 7, '!=': 7,
        '<': 8, '>': 8, '<=': 8, '>=': 8,
        '<<': 9, '>>': 9,
        '+': 10, '-': 10,
        '*': 11, '/': 11, '%': 11,
        '++': 13, '--': 13,                 # postfix, see led()
    }
    UNARY_PRECEDENCE = 12

    def __init__(self, tokens):
        self.tokens = tokens or []
        self.pos = 0
        self.current = self.tokens[0] if self.tokens else None

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current = self.tokens[self.pos]
        else:
            self.current = None

    def peek(self, offset=1):
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return None

    def match(self, ttype, value=None):
        if not self.current:
            return False
        if self.current.type != ttype:
            return False
        if value is not None and self.current.value != value:
            return False
        return True

    def consume(self, ttype=None, value=None):
        cur = self.current
        if not cur:
            return None
        if ttype and (cur.type != ttype or (value is not None and cur.value != value)):
            return None
        self.advance()
        return cur

    def parse(self):
        try:
            return self.parse_program()
        except ParseError as e:
            # return a Program node with an Error child to visualize
            root = ASTNode('Program')
            root.add_child(ASTNode('ParseError', value=str(e)))
            return root

    def parse_program(self):
        root = ASTNode('Program')
        while self.current:
            node = self.parse_external()
            if node:
                root.add_child(node)
            else:
                self.advance()
        return root

    def parse_external(self):
        # handle function or global declaration
        if self.match('KEYWORD') and self.current.value in ('int','float','char','double','void','struct','union'):
            self._decl_line = self.current.line
            ttype = self.current.value
            self.advance()
            # pointer types support
            star_count = 0
            while self.match('OPERATOR','*'):
                self.advance(); star_count += 1
            if self.match('IDENTIFIER'):
                name = self.current.value
                self.advance()
                if self.match('DELIMITER','('):
                    return self.parse_function(ttype + ('*'*star_count), name)
                else:
                    return self.parse_declaration_rest(ttype + ('*'*star_count), name)
            else:
                # anonymous declarations like 'int ;' -> skip
                while self.current and not self.match('DELIMITER',';'):
                    self.advance()
                if self.match('DELIMITER',';'):
                    self.advance()
                return None
        elif self.match('PREPROCESSOR'):
            cur = self.current
            self.advance()
            return ASTNode('Preprocessor', value=cur.value, line=cur.line)
        elif self.match('IDENTIFIER'):
            return self.parse_statement()
        elif self.match('KEYWORD','if'):
            return self.parse_if()
        elif self.match('KEYWORD','for'):
            return self.parse_for()
        elif self.match('KEYWORD','while'):
            return self.parse_while()
        else:
            # skip unknown
            self.advance()
            return None

    def _skip_array_suffix(self):
        """Consume `[...]` after a declarator; return the size text ('' for `[]`)."""
        size = []
        self.advance()  # '['
        while self.current and not self.match('DELIMITER', ']'):
            size.append(self.current.value)
            self.advance()
        if self.match('DELIMITER', ']'):
            self.advance()
        return ''.join(size)

    def parse_declaration_rest(self, type_, first_ident):
        line = getattr(self, '_decl_line', 0)
        node = ASTNode('Declaration', value=type_, line=line)
        ident = ASTNode('Identifier', value=first_ident, line=line)
        if self.match('DELIMITER', '['):
            # arrays: `char msg[] = "..."`, `int a[10];`
            node.value = f"{type_}[{self._skip_array_suffix()}]"
        node.add_child(ident)
        if self.match('OPERATOR','='):
            self.advance()
            node.add_child(ASTNode('Initializer').add_child(self.parse_expression()))
        while self.match('DELIMITER',','):
            self.advance()
            if self.match('IDENTIFIER'):
                node.add_child(ASTNode('Identifier', value=self.current.value)); self.advance()
        if self.match('DELIMITER',';'):
            self.advance()
        return node

    def parse_function(self, ret_type, name):
        node = ASTNode('Function', value=f"{ret_type} {name}", line=getattr(self, '_decl_line', 0))
        # consume '('
        if self.match('DELIMITER','('):
            self.advance()
            params = ASTNode('Params')
            while not self.match('DELIMITER',')') and self.current:
                if self.match('KEYWORD') and self.current.value in ('int','float','char','double','void'):
                    ptype = self.current.value; self.advance()
                    pname = None
                    if self.match('IDENTIFIER'):
                        pname = self.current.value; self.advance()
                    params.add_child(ASTNode('Param', value=f"{ptype} {pname}" if pname else ptype))
                elif self.match('DELIMITER',','):
                    self.advance()
                else:
                    # skip tokens in param list
                    self.advance()
            if self.match('DELIMITER',')'):
                self.advance()
            node.add_child(params)
        # body
        if self.match('DELIMITER','{'):
            body = self.parse_block()
            node.add_child(body)
        else:
            # prototype
            while self.current and not self.match('DELIMITER',';'):
                self.advance()
            if self.match('DELIMITER',';'):
                self.advance()
        return node

    def parse_block(self):
        block = ASTNode('Block')
        if self.match('DELIMITER','{'):
            self.advance()
        while self.current and not self.match('DELIMITER','}'):
            stmt = self.parse_statement()
            if stmt:
                block.add_child(stmt)
            else:
                self.advance()
        if self.match('DELIMITER','}'):
            self.advance()
        return block

    def parse_statement(self):
        if not self.current:
            return None
        if self.match('KEYWORD') and self.current.value in ('int','float','char','double','void'):
            self._decl_line = self.current.line
            t = self.current.value; self.advance()
            if self.match('IDENTIFIER'):
                name = self.current.value; self.advance()
                return self.parse_declaration_rest(t, name)
            else:
                while self.current and not self.match('DELIMITER',';'):
                    self.advance()
                if self.match('DELIMITER',';'):
                    self.advance()
                return None
        if self.match('DELIMITER','{'):
            return self.parse_block()
        if self.match('KEYWORD','if'):
            return self.parse_if()
        if self.match('KEYWORD','for'):
            return self.parse_for()
        if self.match('KEYWORD','while'):
            return self.parse_while()
        if self.match('KEYWORD','return'):
            return self.parse_return()
        # expression / assignment
        expr = self.parse_expression()
        if self.match('DELIMITER',';'):
            self.advance()
        return expr

    def parse_if(self):
        node = ASTNode('If', line=self.current.line)
        self.advance()
        if self.match('DELIMITER','('):
            self.advance()
            cond = self.parse_expression()
            node.add_child(ASTNode('Condition').add_child(cond))
            if self.match('DELIMITER',')'):
                self.advance()
        node.add_child(ASTNode('Then').add_child(self.parse_statement()))
        if self.match('KEYWORD','else'):
            self.advance()
            node.add_child(ASTNode('Else').add_child(self.parse_statement()))
        return node

    def parse_while(self):
        node = ASTNode('While', line=self.current.line)
        self.advance()
        if self.match('DELIMITER','('):
            self.advance()
            node.add_child(ASTNode('Condition').add_child(self.parse_expression()))
            if self.match('DELIMITER',')'):
                self.advance()
        node.add_child(ASTNode('Body').add_child(self.parse_statement()))
        return node

    def parse_for(self):
        node = ASTNode('For', line=self.current.line)
        self.advance()
        if self.match('DELIMITER','('):
            self.advance()
            # init
            if not self.match('DELIMITER',';'):
                init = self.parse_statement(); node.add_child(ASTNode('Init').add_child(init if init else ASTNode('Empty')))
            else:
                node.add_child(ASTNode('Init'))
            # condition
            if not self.match('DELIMITER',';'):
                cond = self.parse_expression(); node.add_child(ASTNode('Condition').add_child(cond))
            else:
                node.add_child(ASTNode('Condition'))
            if self.match('DELIMITER',';'):
                self.advance()
            # inc
            if not self.match('DELIMITER',')'):
                inc = self.parse_expression(); node.add_child(ASTNode('Inc').add_child(inc if inc else ASTNode('Empty')))
            if self.match('DELIMITER',')'):
                self.advance()
        node.add_child(ASTNode('Body').add_child(self.parse_statement()))
        return node

    def parse_return(self):
        node = ASTNode('Return', line=self.current.line)
        self.advance()
        if not self.match('DELIMITER',';'):
            node.add_child(self.parse_expression())
        if self.match('DELIMITER',';'):
            self.advance()
        return node

    # Pratt expression parser
    def parse_expression(self, rbp=0):
        t = self.current
        if not t:
            return None
        self.advance()
        left = self.nud(t)
        while self.current and self.current.type == 'OPERATOR' and self.PRECEDENCE.get(self.current.value, 0) > rbp:
            t = self.current
            self.advance()
            left = self.led(t, left)
        return left

    def nud(self, token):
        if token.type == 'IDENTIFIER':
            # function call or identifier
            if self.current and self.current.type == 'DELIMITER' and self.current.value == '(':
                self.advance()  # consume '('
                call = ASTNode('Call', value=token.value, line=token.line)
                while self.current and not (self.current.type == 'DELIMITER' and self.current.value == ')'):
                    arg = self.parse_expression()
                    if arg:
                        call.add_child(ASTNode('Arg').add_child(arg))
                    if self.current and self.current.type == 'DELIMITER' and self.current.value == ',':
                        self.advance()
                if self.current and self.current.type == 'DELIMITER' and self.current.value == ')':
                    self.advance()
                return call
            else:
                return ASTNode('Identifier', value=token.value, line=token.line)
        if token.type == 'NUMBER':
            return ASTNode('Number', value=token.value, line=token.line)
        if token.type == 'STRING':
            return ASTNode('String', value=token.value, line=token.line)
        if token.type == 'CHAR':
            return ASTNode('Char', value=token.value, line=token.line)
        if token.type == 'OPERATOR' and token.value in ('++', '--'):
            un = ASTNode('PrefixOp', value=token.value, line=token.line)
            un.add_child(self.parse_expression(self.UNARY_PRECEDENCE))
            return un
        if token.type == 'OPERATOR' and token.value in ('+','-','!','~','&','*'):
            # unary operators (address-of, dereference, etc.)
            # Check if this is truly unary by looking at context
            # For '&' and '*', they're unary when preceding an identifier or expression
            right = self.parse_expression(self.UNARY_PRECEDENCE)
            un = ASTNode('UnaryOp', value=token.value, line=token.line)
            un.add_child(right)
            return un
        if token.type == 'DELIMITER' and token.value == '(':
            expr = self.parse_expression()
            if self.current and self.current.type == 'DELIMITER' and self.current.value == ')':
                self.advance()
            return expr
        # fallback
        return ASTNode('Unknown', value=getattr(token,'value',None), line=getattr(token,'line',0))
    
    def led(self, token, left):
        # postfix ++ / -- take no right operand (`i++` used to swallow the
        # token after it, e.g. the `)` closing a for-loop header)
        if token.value in ('++', '--'):
            node = ASTNode('PostfixOp', value=token.value, line=token.line)
            node.add_child(left)
            return node
        prec = self.PRECEDENCE.get(token.value, 0)
        if token.value in self.ASSIGN_OPS:
            # assignment is right-associative: a = b = c is a = (b = c)
            right = self.parse_expression(prec - 1)
            node = ASTNode('Assign', value=token.value, line=token.line)
        else:
            right = self.parse_expression(prec)
            node = ASTNode('BinaryOp', value=token.value, line=token.line)
        node.add_child(left)
        node.add_child(right)
        return node
