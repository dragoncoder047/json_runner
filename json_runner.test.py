import yaml
import json_runner
import sys


sys.setrecursionlimit(2**31 - 1)

x = json_runner.Engine()
x.eval(yaml.full_load("""
- set x 1
- if: $x == 1
  then: say foo bar
  else: say bar baz
- set x 0
- if: $x == 1
  then: say hello
  else: say goodbye
- say (not 1)
- say ([list (not 1) @(1..10), nil])
- foreach: i
  in: 1 to 10
  do: say hello ($i)
- set x [list 1 2 3]
- set y foo if 6 is in $x else bar
- say ($y)
- say (foo if yes else bar)
- set foobarbaz {hello world}
- template:
    foo:
      bar:
        template:
          bar:
            insert: set y
- set x $result
- template:
    foo:
      bar:
        baz:
          - insert: set x
          - insert: set foobarbaz
- set foo $result
- say ($foo)
- set bar [subscr $foo foo bar baz 0 foo bar]
- set baz [eval $bar]
- say ($baz)
- function: foo
  params: [bar, baz]
  do:
    - say ($bar) and ($baz)
    - return [list 1 2 3]
- say ($foo)
- say ([foo yay nay])
- function: make-counter
  params: [val]
  do:
    - lambda: [plus]
      do:
        - set val $val + $plus
        - return $val
    - return $result
- set x [make-counter 5]
- set y [make-counter 50]
- say ([x 100])
- say ([x 100])
- say ([x 100])
- say ([y 100])
- say ([y 100])
- say ([y 100])
- set times 100
- say Starting fib of ($times)
- function: fib
  params: [num]
  do:
    - if: $num < 2
      then: return $num
      else: return [fib $num - 1] + [fib $num - 2]
- function: memoize
  params: [func]
  do:
    - set cache [dict]
    - lambda: []
      do:
        - set key [quote ($args)]
        - if: $cache has $key
          then: return [subscr $cache $key]
          else: return [setsub $cache $key [call $func @($args)]]
- set fib [memoize $fib]
- say ([fib $times])
- say ($fib)
"""))
