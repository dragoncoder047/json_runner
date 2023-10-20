

from dataclasses import dataclass, field
from typing import Any
import regex


@dataclass
class Token:
    start: int = field(compare=False)
    value: Any
    source: str = field(compare=False)
    line: str = field(repr=False, compare=False)


@dataclass
class Expression:
    elements: list[Any]


@dataclass
class FunctionCall:
    name: str
    arg: str


class ParenList(list, Token):
    opener: Token | None
    closer: Token | None

    def __init__(self, *args):
        super().__init__(*args)
        self.opener = None
        self.closer = None

    def __repr__(self):
        return f"<{self.__class__.__name__} opener={self.opener!r} {super().__repr__()} closer={self.closer!r}>"


def raise_token_error(tokens, errormsg):
    tokens = sorted(tokens, key=lambda t: t.start)
    line = tokens[0].line
    pointers = list(" " * len(line))
    for token in tokens:
        src_len = len(token.source)
        pointers[token.start:token.start+src_len] = list("^" * src_len)
    raise SyntaxError(f"{errormsg}\n{line}\n{''.join(pointers)}")


def tokenslice(from_, to):
    return from_.line[from_.start:to.start+len(to.source)]


def get_end_token(it, which):
    while isinstance(it, ParenList):
        it = it.closer if which else it.opener
    return it


def _parse_secondpass(tree):
    if not isinstance(tree, ParenList):
        if isinstance(tree, Token):
            return tree.value
        return tree
    treeval = None
    match tree.opener.value:
        case "{":
            treeval = tokenslice(tree.opener, tree.closer)[
                1:-1] if tree else ""
        case "[":
            if tree:
                treeval = FunctionCall(tree[0].source, tokenslice(get_end_token(
                    tree[1], False), get_end_token(tree[-1], True)) if len(tree) > 1 else "")
        case "(" | _:
            treeval = Expression(list(map(_parse_secondpass, tree)))
    return treeval


def _interpolate_secondpass(top):
    out = []
    prev = top.opener
    for item in top:
        if isinstance(item, ParenList) and item.opener.value == "(" and item.closer.value == ")":
            if string := tokenslice(prev, item.opener).removesuffix("(").removeprefix(")"):
                out.append(string)
            out.append(_parse_secondpass(item))
            prev = item.closer
    if string := tokenslice(prev, top.closer).removesuffix("(").removeprefix(")"):
        out.append(string)
    return out


def _parse_firstpass(line, atoms, wrapped, mismatch_pred=lambda _: True, notclosed_pred=lambda _: True):
    # first pass: nesting stuff
    stack = []
    current_tokens = ParenList()
    # everything is wrapped in top level function call
    current_tokens.opener = Token(0, wrapped[0], wrapped[0], line)
    c2o = dict(zip(")]}", "([{"))
    for token in tokenize(line, atoms):
        if token.value in c2o.values():
            stack.append((current_tokens, token.value, token))
            current_tokens = ParenList()
            current_tokens.opener = token
        elif token.value in c2o.keys():
            closed_open = c2o[token.value]
            previous, expected_open, open_token = stack.pop()
            if expected_open != closed_open and mismatch_pred(stack):
                raise_token_error(
                    [token, open_token], f"mismatched parens: {expected_open} <-> {token.value}")
            previous.append(current_tokens)
            current_tokens.closer = token
            current_tokens = previous
        else:
            current_tokens.append(token)
    if stack and notclosed_pred(stack):
        raise_token_error([ctx[2] for ctx in stack],
                          "these parens were never closed:")
    elif stack:
        current_tokens = stack[0][0]
    current_tokens.closer = Token(len(line) - 1, wrapped[1], wrapped[1], line)
    return current_tokens


def parse2(line, atoms, wrapped):
    return _parse_secondpass(_parse_firstpass(line, atoms, wrapped))


def parse_interpolated(line, atoms):
    def has_open(stack): return stack and stack[0][0].opener == "("
    return _interpolate_secondpass(_parse_firstpass(line, atoms, "()", has_open, has_open))


def process_escapes(string):
    ESCAPES = dict(zip("nteoc", "\n\t\x1b{}"))
    return regex.sub(r"\\(.)", lambda match: ESCAPES.get(match.group(1), match.group(1)), string)


def process_token(token):
    if token[0] in "'\"":
        return process_escapes(token[1:-1])
    try:
        return int(token, base=0)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token


def escape_atom(a):
    if a[0].isalpha() and a[-1].isalpha():
        return fr"(?:\b{regex.escape(a)}\b)"
    return f"(?:{regex.escape(a)})"


def tokenize(string, atoms):
    ATOM_TOKEN = "|".join(map(escape_atom, sorted(atoms, reverse=True)))
    STRING_TOKEN = r"""(?<=\s|^)(?P<q>['"])(?:\\\S|(?!(?P=q))[\s\S])*?(?P=q)(?=\s|$)"""
    NUMBER_TOKEN = r"0x\d+|-?\d+(?:\.\d+(?:[eE][+-]\d+)?)?"
    PAREN_TOKEN = r"[\[\](){}]"
    NOT_ANYNAME_TOKEN = r"(?P<any>" + "|".join(map(lambda t: f"(?:{t})", filter(
        None, [PAREN_TOKEN, STRING_TOKEN, ATOM_TOKEN, NUMBER_TOKEN]))) + ")"
    ANYNAME_TOKEN = r"(?:(?!(?&any))\S)+"
    ALL_TOKENS = regex.compile(NOT_ANYNAME_TOKEN + "|" + ANYNAME_TOKEN)
    i = 0
    while i < len(string):
        match = ALL_TOKENS.search(string, i)
        if not match:
            return
        token = match.group(0)
        yield Token(match.start(), process_token(token), token, string)
        i = match.end()


if __name__ == '__main__':
    line, atoms = "It's a tomato! (Sub-expression) {]{]{] pa(\"'\\n\\n\") spooky! (the orange) And errors: {{{", [
        "$", "or", "and", "is in"]
    for t in tokenize(line, atoms):
        print(t.line)
        print(" " * t.start + "^" * len(t.source), repr(t.value))
    parsed = parse_interpolated(line, atoms)
    print("-" * 80)
    print(parsed)
