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

## Python implementation


