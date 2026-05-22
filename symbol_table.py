

class Symbol:
    def __init__(self, name, type_, scope, line_number=0, value=None):
        self.name = name
        self.type = type_
        self.scope = scope            # scope name (e.g., "global", "main", "block1")
        self.line_number = line_number
        self.value = value

    def __repr__(self):
        return (
            f"Symbol(name='{self.name}', type='{self.type}', "
            f"scope='{self.scope}', line={self.line_number}, value={self.value})"
        )


class SymbolTable:
    def __init__(self):
        self.symbols = []               # flat list (for report)
        self.scope_stack = ['global']   # scope chain
        self.current_scope = 'global'
        self.scope_counter = 0          # for naming block scopes uniquely

    # ------------------------------
    # Scope Management
    # ------------------------------
    def enter_scope(self, name=None):
        """Enter a new scope. If name=None, auto-create one."""
        if name is None:
            self.scope_counter += 1
            name = f"block_{self.scope_counter}"
        self.scope_stack.append(name)
        self.current_scope = name

    def exit_scope(self):
        """Exit scope but never exit global."""
        if len(self.scope_stack) > 1:
            self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]

   
    def add_symbol(self, name, type_, line_number=0, value=None):
        """Add symbol to current scope."""
        sym = Symbol(name, type_, self.current_scope, line_number, value)
        self.symbols.append(sym)
        return sym

    def find(self, name):
        """Lookup with scope chain resolution."""
        # search backwards so latest defined symbol is found first
        for s in reversed(self.symbols):
            if s.name == name:
                return s
        return None

    def find_in_scope(self, name, scope_name):
        """Lookup only inside a specific scope."""
        for s in reversed(self.symbols):
            if s.name == name and s.scope == scope_name:
                return s
        return None

    def get_all(self):
        return list(self.symbols)

    def clear(self):
        """Reset the whole table."""
        self.symbols.clear()
        self.scope_stack = ['global']
        self.current_scope = 'global'
        self.scope_counter = 0
