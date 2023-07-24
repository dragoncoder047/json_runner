import itertools
import random

__all__ = "parse Signal Done Next Abort Return BareEngine Engine".split()


def parse(
        string,
        delimiters,
        *,
        singletons=[],
        openers="[{(\"'",
        closers="]})\"'",
        include_delims=False,
        split_at_parens=True):
    # Adapted from https://stackoverflow.com/a/64211769
    current_string = ''
    stack = []
    otc = dict(zip(openers, closers))
    delimiters = sorted(delimiters, key=len, reverse=True)
    singletons = sorted(singletons, key=len, reverse=True)
    while string:
        c = string[0]
        if c in openers:
            if stack and otc[c] == stack[-1] == c:
                stack.pop()
                if split_at_parens:
                    yield current_string + c
                    current_string = ""
                    string = string[1:]
                    continue
            else:
                if split_at_parens and not stack and current_string:
                    if current_string:
                        yield current_string
                    current_string = ""
                stack.append(c)
        elif c in closers:
            if not stack:
                raise SyntaxError("unopened %s" % c)
            if otc[b := stack.pop()] != c:
                raise SyntaxError(
                    f"closing paren '{c}' does not match opening paren '{b}'")
            if split_at_parens and not stack and current_string:
                yield current_string + c
                current_string = c = ""
        at_split = False
        if not stack:
            for d in delimiters:
                if string.startswith(d):
                    if current_string:
                        yield current_string
                    if include_delims:
                        yield d
                    current_string = ""
                    string = string.removeprefix(d)
                    at_split = True
                    break
        if not at_split:
            for s in singletons:
                if stack:
                    continue
                if string.startswith(s):
                    yield from (current_string, s)
                    current_string = ""
                    string = string.removeprefix(s)
                    break
            else:
                current_string += c
                string = string[1:]
    if stack:
        raise SyntaxError(f"unmatched '{stack[-1]}'")
    yield current_string


PYTHONIZE_MAP = {
    ".": "DOT",
    "^": "CARET",
    "*": "STAR",
    "/": "SLASH",
    "%": "PERCENT",
    "+": "PLUS",
    "-": "DASH",
    "=": "EQ",
    "!": "BANG",
    "<": "LT",
    ">": "GT",
    "@": "AT",
    "&": "AND",
    "|": "PIPE",
    ":": "COLON",
    "#": "HASH",
    "~": "TILDE",
    "`": "BACKTICK",
    "'": "APOS",
    '"': "QUO",
    "$": "DOLLAR",
}


class Signal(Exception):
    pass


class Done(Signal):
    pass


class Next(Signal):
    pass


class Return(Signal):
    pass


class Abort(Signal):
    pass


class BareEngine:
    def __init__(self):
        self.scope_stack = [{}]

    @property
    def sorted_ops(self):
        names = [x for x in dir(self) if x.startswith("op_")]
        nPk = [(int((s := n.removeprefix("op_").split("_", 1))[0]), s[1], n)
               for n in names]
        sPk = sorted(nPk, key=lambda x: x[0])
        return [x[1:] for x in sPk]

    def eval(self, code):
        match code:
            case str():
                code = code.strip()
                if not code:
                    return None
                if ";" in code:
                    return self.eval(list(parse(code, [";"],
                                                split_at_parens=False)))
                return self.call_function(code)
            case list() | tuple():
                self.scope_stack[-1]["result"] = None
                for item in code:
                    self.set("result", self.eval(item))
                return self.get("result")
            case dict():
                k = code.keys()
                # try all permutations if they wrote it in a different order
                for p in itertools.permutations(k):
                    n = "block_" + "_".join(p)
                    if hasattr(self, n):
                        return getattr(self, n)(code)
                raise ValueError(
                    f"no block {'_'.join(p)} in {type(self).__name__}")
            case _:
                return code

    def expr(self, string):
        string = string.strip()
        ############
        text_ops = [x[0].replace("_", " ") for x in self.sorted_ops]
        for i, o in enumerate(text_ops):
            for punc, py in PYTHONIZE_MAP.items():
                o = o.replace(py, punc)
            text_ops[i] = o
        py_name_ops = [x[1] for x in self.sorted_ops]
        ###############
        tokens = list(
            filter(bool, parse(
                string, " ", singletons=text_ops, split_at_parens=True)))
        for i, t in enumerate(tokens):
            if not isinstance(t, str):
                continue
            if t[0] == "(":
                val = self.expr(t[1:-1])
                tokens[i:i+1] = val
            elif t[0] == "[":
                tokens[i] = self.eval(t[1:-1])
            elif t[0] in "{'\"":
                tokens[i] = t[1:-1]
            if isinstance(tokens[i], str):
                try:
                    tokens[i] = int(tokens[i], base=0)
                except ValueError:
                    try:
                        tokens[i] = float(tokens[i])
                    except ValueError:
                        pass
        while True:
            for text_op, op_func_name in zip(text_ops, py_name_ops):
                tokens.insert(0, None)
                tokens.append(None)
                try:
                    i = tokens.index(text_op)
                    val = getattr(self, op_func_name)(tokens[i-1], tokens[i+1])
                    tokens[i-1:i+2] = val if isinstance(val, list) else [val]
                    break
                except ValueError:
                    continue
                finally:
                    assert tokens.pop(
                        0) is None, "postfix operator not allowed at beginning"
                    assert tokens.pop(
                    ) is None, "prefix operator not allowed at end"
            else:
                break
        return tokens

    def call_function(self, code):
        try:
            name, arg = code.split(None, 1)
        except ValueError:
            name, arg = code, ""
        if hasattr(self, "func_" + name):
            return getattr(self, "func_" + name)(arg.strip())
        args = self.expr(arg)
        return self.call_user_function_or(name, args, code)

    @staticmethod
    def _test_function(func):
        return (isinstance(func, dict)
                and sorted(func.keys()) == ['body', 'closure', 'params'])

    def call_user_function_or(self, name, args, code):
        if self._test_function(name):
            func = name
        else:
            try:
                func = self.get(name)
                if not self._test_function(func):
                    return code
            except UnboundLocalError:
                return code
        orig_len = len(self.scope_stack)
        self.scope_stack.append(None)
        self.scope_stack.extend(func['closure'])
        self.scope_stack.append(
            {"args": args} | dict(zip(func['params'], args)))
        try:
            return self.eval(func['body'])
        except Return as r:
            return r.args[0]
        finally:
            del self.scope_stack[orig_len:]

    def get(self, var):
        for scope in reversed(self.scope_stack):
            if scope is None:
                break
            try:
                return scope[var]
            except KeyError:
                continue
        raise UnboundLocalError("no var $%s" % var)

    def set(self, var, value):
        for scope in reversed(self.scope_stack):
            if scope is None:
                break
            if var in scope:
                scope[var] = value
                return
        self.scope_stack[-1][var] = value

    def make_lambda(self, params, body):
        if None in self.scope_stack:
            first_none = self.scope_stack.index(None)
            last_none = (len(self.scope_stack) -
                         list(reversed(self.scope_stack)).index(None))
            closed_scopes = (self.scope_stack[:first_none] +
                             self.scope_stack[last_none+1:])
        else:
            closed_scopes = self.scope_stack.copy()
        lambda_ = {
            "closure": closed_scopes,
            "params": params,
            "body": body
        }
        return lambda_


class Engine(BareEngine):
    def __init__(self):
        super().__init__()
        self.silenced = False
        self.rng = random.Random()

    def print(self, *a, **k):
        if self.silenced:
            return
        print(*a, **k)

    def interpolate(self, line):
        it = parse(line, [], split_at_parens=True)
        it = map(lambda x: self.expr(x[1:-1]) if x and x[0] == "(" else x, it)
        return "".join(map(str, itertools.chain.from_iterable(it)))

    def _outputcmd(self, line, **kwargs):
        self.print(self.interpolate(line), **kwargs)

    def func_say(self, line): self._outputcmd(line)
    def func_puts(self, line): self._outputcmd(line, end="")

    def func_set(self, line):
        values = self.expr(line)
        val = None
        while len(values) >= 2:
            var = values[0]
            val = values[1]
            self.set(var, val)
            values = values[2:]
        if values:
            val = self.get(values[0])
        return val

    def func_silently(self, line):
        self.silenced = True
        try:
            rv = self.eval(line)
        finally:
            self.silenced = False
        return rv

    def func_list(self, line):
        items = filter(bool, map(str.strip, parse(
            line, [","], split_at_parens=False)))
        items = itertools.chain.from_iterable(map(self.expr, items))
        return list(items)

    def func_setsub(self, line):
        container, key, val = self.expr(line)
        container[key] = val
        return val

    def func_done(self, _): raise Done
    def func_next(self, _): raise Next

    def func_abort(self, line):
        msg, = self.expr(line)
        raise Abort(msg)

    def func_return(self, line):
        val, = self.expr(line)
        raise Return(val)

    def func_eval(self, line):
        item, = self.expr(line)
        return self.eval(item)

    def func_dict(self, line):
        return dict(self.expr(line))

    def func_quote(self, line):
        return self.interpolate(line)

    def func_ask(self, line):
        return input(self.interpolate(line) + " ")

    def func_confirm(self, line):
        yes = ["y", "yes"]
        no = ["n", "no"]
        while True:
            ans = input(self.interpolate(line) + " (y/n) ").lower()
            if ans in yes:
                return True
            if ans in no:
                return False

    def func_call(self, line):
        func, *args = self.expr(line)
        return self.call_user_function_or(func, args, line)

    def block_if_then_else(self, block):
        cond, = self.expr(block['if'])
        if cond:
            return self.eval(block['then'])
        return self.eval(block['else'])

    def block_while_do(self, block):
        result = None
        cond, = self.expr(block['while'])
        while cond:
            try:
                result = self.eval(block['do'])
            except Next:
                continue
            except Done:
                break
            cond, = self.expr(block['while'])
        return result

    def block_foreach_in_do(self, block):
        l, = self.expr(block['in'])
        result = None
        for i in l:
            self.set(block['foreach'], i)
            try:
                result = self.eval(block['do'])
            except Next:
                continue
            except Done:
                break
        return result

    def block_function_params_do(self, block):
        lambda_ = self.make_lambda(block['params'], block['do'])
        self.set(block['function'], lambda_)
        return lambda_

    def block_lambda_do(self, block):
        return self.make_lambda(block['lambda'], block['do'])

    def recursive_interpolate(self, val, depth=1):
        match val:
            case str() if depth == 0:
                return self.interpolate(val)
            case str() if depth > 0:
                return val
            case list() | tuple() if depth == 0:
                return self.eval(val)
            case list() | tuple() if depth > 0:
                return [self.recursive_interpolate(i, depth) for i in val]
            case dict():
                if len(val) == 1:
                    key = list(val.keys())[0]
                    if key == "template":
                        depth += 1
                    if key == "insert":
                        depth -= 1
                if depth == 0:
                    return self.eval(val[key])
                out = {}
                for k, v in val.items():
                    kk = self.recursive_interpolate(k, depth)
                    vv = self.recursive_interpolate(v, depth)
                    out[kk] = vv
                return out
            case _:
                return val

    def block_template(self, block):
        return self.recursive_interpolate(block['template'])

    def op_0_DOLLAR(self, left, right): return [left, self.get(right)]

    def op_1_DOT(self, left, right):
        return [getattr(left, right)
                if isinstance(right, str) and hasattr(left, right)
                else left[right]]

    def op_100_not(self, left, right): return [left, not right]
    op_100_BANG = op_100_not

    def op_100_AT(self, left, right):
        try:
            return [left] + list(right)
        except TypeError:
            return [left, right]

    def op_100_HASH(self, left, right): return [left, len(right)]
    def op_200_DOTDOT(self, left, right): return [range(left, right)]
    op_200_to = op_200_DOTDOT
    def op_300_CARET(self, left, right): return [pow(left, right)]
    def op_400_STAR(self, left, right): return [left * right]
    def op_400_SLASH(self, left, right): return [left / right]
    def op_400_PERCENT(self, left, right): return [left % right]
    def op_500_PLUS(self, left, right): return [left + right]
    def op_500_DASH(self, left, right): return [left - right]
    def op_600_EQEQ(self, left, right): return [left == right]
    def op_600_BANGEQ(self, left, right): return [left != right]
    def op_700_LTEQ(self, left, right): return [left <= right]
    def op_700_GTEQ(self, left, right): return [left >= right]
    def op_700_LT(self, left, right): return [left < right]
    def op_700_GT(self, left, right): return [left > right]
    def op_801_in(self, left, right): return [left in right]
    op_800_is_in = op_801_in
    def op_801_not_in(self, left, right): return [left not in right]
    op_800_is_not_in = op_801_not_in
    def op_800_contains(self, left, right): return [right in left]
    op_800_has = op_800_contains
    def op_800_doesnAPOSt_contain(self, left, right): return [
        right not in left]
    op_800_doesnAPOSt_have = op_800_doesnAPOSt_contain
    op_800_does_not_have = op_800_does_not_contain = op_800_doesnAPOSt_contain
    def op_900_ANDAND(self, left, right): return [left and right]
    op_900_and = op_900_ANDAND
    def op_900_PIPEPIPE(self, left, right): return [left or right]
    op_900_or = op_900_PIPEPIPE
    def op_1000_if(self, left, right): return [[left] if right else None]

    def op_1001_else(self, left, right): return [
        right if left is None else left[0]]
