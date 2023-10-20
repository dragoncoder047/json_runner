

from pyparsing import (Forward, ParserElement, Regex, Word, identbodychars,
                       identchars, common, nested_expr, one_of, original_text_for, quoted_string)
ParserElement.enable_left_recursion()


def test(pattern, source):
    print(source)
    print(list(pattern.scan_string(source)))


tokens = quoted_string | Regex()


test(tokens, "setk $self foo [item \"door\\n]\"]; say {Foo!{Bar!}}")
