# JSON is Turing-complete!

## Did you know that?

Most programmers, when they are asked what is JSON (or any other format that is equivalent, such as YAML or TOML), respond that it is a data-exchange format. JSON holds structured data, but it is static and cannot do anything by itself.

This project aims to show that JSON is **not** static and is, in fact, capable of just about everything that major programming languages can do, and with just a little more configuration, it becomes a powerful scripting language perfect for embedding in other programs.

## Example

```json
[
    {
        "function": "fizzbuzz",
        "params": ["num"],
        "do": [
            {
                "if": "$num % 15 == 0",
                "then": "say fizzbuzz",
                "else": {
                    "if": "$num % 5 == 0",
                    "then": "say fizz",
                    "else": {
                        "if": "$num % 3 == 0",
                        "then": "say buzz",
                        "else": "say ($num)"
                    }
                }
            }
        ]
    },
    {
        "foreach": "i",
        "in": "1 to 100",
        "do": "fizzbuzz $i"
    }
]
```

## How it works

Conceptually, there are 4 major things in JSON: strings, numbers, objects (Python dicts), and lists. A different thing happens when each is evaluated:

* Numbers: they just evaluate to themselves.
* Lists: each element of the list is (recursively) evaluated in order. Additionally, the result of evaluating the previous item is stored in the "result" variable.
* Objects: the key strings are used to look up a block handler function, which does what it wants with the contents of the object.
* Strings: Depending on where, a string can mean three different things:
    * A variable name, such as the "foreach" and "function" keys above.
    * An expression, such as the "if" and "in" keys, which contains operators, variables, numbers, and possibly subexpressions.
    * A function call, such as the "then" and "do" keys, where the first word of non-whitespace is taken to be the function name, and the rest of the line is up to the function to determine how to use.

## Available functions, blocks, and operators

### Terminology

* `<line>`: Represents a valid function call syntax, by default all strings are interpreted as these. The string is split at the first whitespace, and the first value is used to look up the function, and the remainder is passed to the function to do as it pleases.
* `<expression>`: means a string containing values and operators. A value can be a number composed of digits, or a string, which can be enclosed in single or double quotes, or no quotes if it doesn't contain spaces. You can also use parenthesis to insert a sub-expression or square brackets to insert a function call (they mean the same thing as in Tcl).
* `<interpolate-string>`: represents a string that is mostly to be taken literally but has values interpolated into it, which are enclosed in parenthesis. For example, the `say` command below takes an `<interpolate-string>`, and prints it. If you write `say Today is a $dayofweek`, it would simply print `Today is a $dayofweek`. To actually get the `dayofweek` variable to be interpolated, you would have to write `say Today is a ($dayofweek)`, and it would print `Today is a Monday`.
* `<varname>`: represents a parameter that is nothing but a variable name - no expression expansions are performed.
* `<code>`: represents any valid JSON value that can be executed, it can be a string, a list, or an object.

### Functions

`say <interpolate-string>` or `puts <interpolate-string>`
:   Prints the result of interpolating the values in the `<interpolate-string>`, `puts` without a newline, `say` with.

`set <var> <value> [<var> <value>...]`
:   Mostly identical to the Tcl set command -- used to set the value of variables. However, note that the values are allowed to be expressed as an inline expression due to operators, so if you write `set a 1 + 2` it won't set a to 1 and + to 2, it will first evaluate the expression, wind up with `a 3`, and set a to 3.

`silently <line>`
:   Suppresses printing output while the `<line>` is running. Useful if you are calling some action that produces output, but you don't want that output shown to the user.

`list <expression>`
:   Evaluates the expressions, and concatenates all of the result lists together and returns it.

`setsub <container> <key> <value>` (all 3 are expressions)
:   Sets the key value of the container to the value and then returns the value.

`done`, `next`
:   Equivalent to `break` and `continue` in loops.

`abort <expression>`
:   Raises an error with the message.

`return <expression>`
:   Causes the enclosing function to return early, with the value specified, instead of returning the last value evaluated.

`eval <expression>`
:   The expression produces a string, and it is interpreted as a `<line>` and evaluated again.

`dict <expression>`
:   The expression must be a list of pairs, and a new Python dictionary (JSON object) is created using the key and value of each pair.

`quote <interpolate-string>`
:   Evaluates the interpolations in the string, and returns the interpolated string.

`ask <interpolate-string>`, `confirm <interpolate-string>`
: Ask prints the interpolate-string like `puts`, followed by a space, and then returns the next line of user input. Confirm is similar, it also asks the user for input, but it repeatedly re-evaluates the prompt and asks again until the user enters yes or no, and then it returns true or false when they do.

`call <function> <arguments>`
:   Calls the function with the provided arguments, both are expressions. Functionally identical to writing the name of the function followed by the arguments, but 1. the arguments are evaluated regardless of whether the function actually would have if it had been called in the normal fashion, and 2. the function doesn't have to just be a name, it can be an expression that does some work and then *returns* a function value. Useful if you're doing a lot with closures and don't want to store them in temporary variables in order to be able to refer to them by name.

### Blocks

`{"if": "<expression>", "then": <code>, "else": <code>}`
:   Implements the if-statement. The expression is evaluated, and then the *then* or *else* branches are evaluated depending on whether the expression was truthy or falsy. Note that you **must** include both a *then* and an *else* branch, the *else* branch can simply be `null` if there's nothing to do.

`{"while" "<expression>", "do": <code>}`
:   Implements a while-loop. The expression is evaluated before each loop iteration, and the loop only continues while the expression is truthy.

`{"foreach": "<varname>", "in": "<expression>", "do": <code>}`
:   Implements a Python-style iteration-over-a-container loop. The varname is set to the sequential items of the container for each iteration.

`{"lambda": ["<varname>", "<varname>", ...], "do": <code>}`,
`{"function": "<varname>", "params": ["<varname>", "<varname>", ...], "do": <code>}`
:   Creates anonymous and named functions. The list of varnames is the parameters, and additionally the entire arguments list is available as `$args`. The named form is equivalent to setting the value returned by the lambda form (`$result`) to the named variable. The functions are closures, with Python-style local->global->builtin scoping rules.

`{"template": ...}`
:   This one was designed to act a lot like Scheme quasiquotes. In fact, they are basically identical:

```python
>>> json_runner.Engine().eval([
...     "set bar 33",
...     {"template": {"numbers": [1, 2, 1, {"template": [{"insert": "foo"}, {"insert": {"insert": "set bar"}}]}]}}
... ])
{'numbers': [1, 2, 1, {'template': [{'insert': 'foo'}, {'insert': 33}]}]}
```
```scheme
(define bar 33)
(display `(numbers 1 2 1 `(,foo ,,bar)))
;; prints: (numbers 1 2 1 (quasiquote ((unquote foo) (unquote 33))))
```

The objects with the sole "template" key act as `quasiquote`, and ones with the sole key of "insert" function as `unquote`.

### Operators

`$`*string*
:   Looks up the variable named by the string using the current scoping rules, and returns it, or throws an error if it was not set.

*container*`.`*key*
:   Gets the *key* property on the container, or indexes the container using the key. (Equivalent to Python `getattr(container, key)` or `container[key]`.)

`!`*value*, `not`*value*
:   Returns the boolean NOT of the value.

`@`*container*
:   The splat operator: Unpacks the container into the expression. If it is not iterable, nothing happens.

`#`*container*
:   Returns the length of the container, or throws an error if the object doesn't have a length.

*low*`to`*high*, *low*`..`*high*
:   Returns `range(low, high)`.

*a*`^`*b*, *a*`*`*b*, *a*`/`*b*, *a*`%`*b*, *a*`+`*b*, *a*`-`*b*, *a*`==`*b*, *a*`!=`*b*, *a*`<=`*b*, *a*`>=`*b*, *a*`<`*b*, *a*`>`*b*
:   Standard math and comparison operations: exponent, multiply, divide, modulo, add, subtract, equal, not equal, less than or equal to, greather than or equal to, less than, greather than.

*item*`in`*container*, *item*`is in`*container*, *item*`not in`*container*, *item*`is not in`*container*, *container*`contains`*item*, *container*`has`*item*, *container*`doesn't contain`*item*, *container*`does not contain`*item*, *container*`doesn't have`*item*, *container*`does not have`*item*
:   Tests to see if *container* includes *item* in it. They all reduce to the Python `in` or `not in` tests.

*value*`&&`*value*, *value*`and`*value*, *value*`||`*value*, *value*`or`*value*
:   Boolean conjunction and disjunction. They return the same values as their Python counterparts. Note that unlike the Python versions, these operators **do not** short circuit; both operands are evaluated regardless of the resultant value.

*value1*`if`*test*`else`*value2*
:   If *test* is truthy, returns *value1*, else returns *value2*.

## Python implementation

The parsing and evaluation is handled by the low-level `BareEngine` class in json_runner.py. The `eval()` method takes the parsed JSON value, and switches on the type. If it is a list, the items are each passed to `eval()` recursively; if it's a dictionary the keys are used to look up the block handler function; if it's a string, it is split at the first whitespace and the function name is looked up and called; otherwise the value is returned as is.

Block, function, and operator handers are named much like the Python standard `cmd` module does it; functions are named `func_` plus the function name (e.g. `func_say` for the `say` function); blocks are named `block_` plus the keys for that block joined by underscores (e.g. the if-then-else handler function is called `block_if_then_else`); and operators are named `op_` plus the precedence plus the operator text with special characters replaced by capitalized name counterparts (e.g. `op_800_doesnAPOSt_have` for the `doesn't have` operator) -- search for `PYTHONIZE_MAP` in json_runner.py to find the names of the special characters.

The `expr()` function handles the expression functionality and its operation is a little more complex:

1. `expr()` starts by calling the `parse()` helper function, which splits the string into tokens, being careful not to split inside strings or groups of parenthesis.
2. Each token is then pre-processed: sub-expression tokens enclosed in parenthesis are recursively passed to `expr()` and the result spliced back in, function-call expressions enclosed in square brackets are passed to `eval()`, strings enclosed in curly brackets or quotes are stripped of their quotes, and strings representing numbers are converted to actual numbers.
3. The token list is padded with `None` on both ends to allow unary operators to be emulated with binary operators that return the unused argument unchanged.
4. The highest precedence operator is found in the list, and the corresponding function is called to compute it. The function returns a list, and the result is spliced (not inserted) back into the tokens array.
5. The `None`-padding is removed and checked to make sure it is still `None` (if it isn't, there was a syntax error).
6. If there are more operators, the loop continues from step 3.
7. If there are no more operators, the tokens list is returned.

The only difference between `BareEngine` and `Engine` is that `BareEngine` has absolutely no functions, operators, or blocks implemented on it; while `Engine` has all of the above items implemented.

### Performance

Abysmal at best. The implementation is highly recursive: every bracket, every nested data object, every function call, all put at least 2 call frames (and often more) on Python's stack. I advise calling `sys.setrecursionlimit(2**31-1)` (the maximum value) before calling any recursive JSON-code. This implementation was not designed for speed or memory but as just something that works.
