*** Settings ***
Suite Setup       Literals to objects
Test Template     Should Be Equal

*** Variables ***
${LIST}           [['item'], [1, 2, (3, [4]), 5], 'third']
${DICT}           {'key': {'key': 'value'}, 1: {2: 3}, 'x': {'y': {'z': ''}}}
${MIXED}          {'x': [(1, {'y': {'z': ['foo', 'bar', {'': [42]}]}})]}
${STRING}         Robot42

*** Test Cases ***
Nested list access
    ${LIST}[0][0]                       item
    ${LIST}[1][-1]                      ${5}
    ${LIST}[1][2][0]                    ${3}
    ${LIST}[1][2][-1][0]                ${4}

Nested dict access
    ${DICT}[key][key]                   value
    ${DICT}[${1}][${2}]                 ${3}
    ${DICT}[x][y][z]                    ${EMPTY}

Nested mixed access
    ${MIXED}[x][0][0]                   ${1}
    ${MIXED}[x][0][1][y][z][-1][][0]    ${42}

Nested access with slicing
    ${LIST}[1:][:-1]                    ${LIST[1:-1]}
    ${LIST}[1:-1][-1][-2:1:-2][0][0]    ${3}

Non-existing nested list item
    [Documentation]    FAIL Tuple '\${LIST}[1][2]' has no item in index 666.
    ${LIST}[1][2][666]                  whatever

Non-existing nested dict item
    [Documentation]    FAIL Dictionary '\${DICT}[x][y]' has no item 'nonex'.
    ${DICT}[x][y][nonex]                whatever

Invalid nested list access
    [Documentation]    FAIL
    ...    Tuple '\${LIST}[1][2]' used with invalid index 'inv'. To use \
    ...    '[inv]' as a literal value, it needs to be escaped like '\\[inv]'.
    ${LIST}[1][2][inv]                  whatever

Invalid nested dict access
    [Documentation]    FAIL Accessing item \
    ...    '{'key': {'key': 'value'}, 1: {2: 3}, 'x': {'y': {'z': ''}}}' from \
    ...    dictionary '\${DICT}[key]' failed: unhashable type: 'dict'
    ${DICT}[key][${DICT}]               whatever

Invalid nested string access
    [Documentation]    FAIL Tuple '\${STRING}[1]' used with invalid index 'inv'.
    ${LIST}[1][inv]                  whatever

Nested access with non-subscriptable
    [Documentation]    FAIL
    ...    Variable '\${DICT}[\${1}][\${2}]' is integer, which is not \
    ...    subscriptable, and thus accessing item '0' from it is not possible. \
    ...    To use '[0]' as a literal value, it needs to be escaped like '\\[0]'.
    ${DICT}[${1}][${2}][0]                     whatever

Escape nested
    ${LIST}[-1]\[0]                     third[0]
    ${DICT}[key][key]\[key]             value[key]
    ${DICT}[key]\[key][key]             {'key': 'value'}[key][key]
    ${STRING}[0]\[-1]                   R[-1]

Nested access doesn't support old `@` and `&` syntax
    @{LIST}[0][0]                       ['item'][0]
    &{DICT}[key][key]                   {'key': 'value'}[key]
    &{MIXED}[x][0][0]                   ${MIXED}[x]\[0][0]

*** Keywords ***
Literals to objects
    ${LIST} =     Evaluate    ${LIST}
    ${DICT} =     Evaluate    ${DICT}
    ${MIXED} =    Evaluate    ${MIXED}
    Set Suite Variable    ${LIST}
    Set Suite Variable    ${DICT}
    Set Suite Variable    ${MIXED}
