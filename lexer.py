
import re

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line}, col={self.column})"

class Lexer:
    def __init__(self):
        # C-like keywords (expandable)
        self.keywords = {
            'int','float','char','double','void','if','else','for','while','return',
            'break','continue','struct','union','enum','typedef','switch','case','default',
            'sizeof'
        }

        # Ordered rules: longer/complex patterns first
        self.rules = [
            ('COMMENT',       r'//[^\n]*|/\*[\s\S]*?\*/'),
            ('PREPROCESSOR',  r'\#[^\n]*'),
            # string (allow escaped quotes and escapes)
            ('STRING',        r'"(\\.|[^"\\])*"'),
            ('CHAR',          r"'(\\.|[^'\\])'"),
            # hex, float, integer
            ('NUMBER',        r'0[xX][0-9A-Fa-f]+|\d+\.\d+|\d+\.\d*|\.\d+|\d+'),
            ('IDENTIFIER',    r'[A-Za-z_][A-Za-z0-9_]*'),
            # multi-char operators first
            ('OPERATOR',      r'>>=|<<=|==|!=|<=|>=|\+\+|--|\+=|-=|\*=|/=|%=|->|&&|\|\||<<|>>'),
            # single-char operators
            ('OPERATOR',      r'[+\-*/%=<>!&|^~?:]'),
            ('DELIMITER',     r'[()\[\]{};,.:]'),
            ('WHITESPACE',    r'\s+'),
            ('MISMATCH',      r'.'),
        ]

        # precompile regex patterns for speed
        self.compiled = [(name, re.compile(p)) for name, p in self.rules]

    def tokenize(self, code):
        tokens = []
        pos = 0
        line = 1
        line_start = 0
        n = len(code)

        while pos < n:
            matched = False
            for tname, cre in self.compiled:
                m = cre.match(code, pos)
                if not m:
                    continue
                matched = True
                s = m.group(0)
                col = pos - line_start + 1

                if tname == 'WHITESPACE':
                    # update line and line_start
                    line += s.count('\n')
                    if '\n' in s:
                        line_start = pos + s.rfind('\n') + 1

                elif tname == 'COMMENT':
                    # comments may contain newlines
                    line += s.count('\n')
                    if '\n' in s:
                        line_start = pos + s.rfind('\n') + 1
                    # store comment tokens too (optional) — keep them, user can filter
                    tokens.append(Token('COMMENT', s, line, col))

                elif tname == 'MISMATCH':
                    # unknown character — record as UNKNOWN token
                    tokens.append(Token('UNKNOWN', s, line, col))

                else:
                    t = tname
                    # map IDENTIFIER -> KEYWORD if needed
                    if tname == 'IDENTIFIER' and s in self.keywords:
                        t = 'KEYWORD'
                    tokens.append(Token(t, s, line, col))

                pos = m.end()
                break

            if not matched:
                # should not happen, but advance to avoid infinite loop
                pos += 1

        return tokens

    def debug(self, code):
        toks = self.tokenize(code)
        for t in toks:
            print(t)
        return toks

# quick local test when run directly
if __name__ == "__main__":
    sample = '''
    #include <stdio.h>
    // comment line
    int main() {
        int x = 10;
        float y = 3.14;
        char c = 'A';
        printf("Hello %d\\n", x);
        /* multi
           line comment */
        return 0;
    }
    '''
    lx = Lexer()
    for tok in lx.debug(sample):
        pass
