from symbol_table import SymbolTable


def test_symbols_record_their_scope():
    st = SymbolTable()
    st.add_symbol("g", "int")
    st.enter_scope("main")
    st.add_symbol("x", "int", line_number=3)
    assert st.find("x").scope == "main"
    assert st.find("g").scope == "global"


def test_shadowing_finds_innermost_latest_definition():
    st = SymbolTable()
    st.add_symbol("x", "int")
    st.enter_scope()
    st.add_symbol("x", "float")
    assert st.find("x").type == "float"
    assert st.find_in_scope("x", "global").type == "int"


def test_block_scopes_get_unique_names_and_global_is_never_exited():
    st = SymbolTable()
    st.enter_scope(); st.exit_scope(); st.enter_scope()
    assert st.current_scope == "block_2"
    st.exit_scope(); st.exit_scope(); st.exit_scope()
    assert st.current_scope == "global"


def test_clear_resets_everything():
    st = SymbolTable()
    st.enter_scope("main"); st.add_symbol("x", "int")
    st.clear()
    assert st.get_all() == [] and st.current_scope == "global"
