import typing

import sphinx_thrift.thrift_ast as ast
from sphinx_thrift import parser

import xml.etree.ElementTree as ET

import pytest

basic_types = [
    "bool", "byte", "i8", "i16", "i32", "i64", "double", "string", "binary"
]


def make_basic_test_data(type_: str) -> typing.Tuple[str, ast.Type]:
    return f'<constant type="{type_}" />', type_


basic_parser_data = list(map(make_basic_test_data, basic_types))


@pytest.mark.parametrize('input,expected', basic_parser_data)
def test_basic_parser(input: str, expected: str) -> None:
    tree = ET.fromstring(input)
    t = parser.parse_type(tree)
    assert (t == expected)


def make_list_test_data(valueType: str) -> typing.Tuple[str, ast.Type]:
    return (
        f'<constant type="list"><valueType type="{valueType}" /> </constant>',
        ast.ListType(valueType))


list_parser_data = list(map(make_list_test_data, basic_types))


@pytest.mark.parametrize('input,expected', list_parser_data)
def test_list_parser(input: str, expected: ast.ListType) -> None:
    tree = ET.fromstring(input)
    t = parser.parse_list_type(tree)
    assert (t == expected)


def make_set_test_data(valueType: str) -> typing.Tuple[str, ast.Type]:
    return (
        f'<constant type="set"><valueType type="{valueType}" /> </constant>',
        ast.SetType(valueType))


set_parser_data = list(map(make_set_test_data, basic_types))


@pytest.mark.parametrize('input,expected', set_parser_data)
def test_set_parser(input: str, expected: ast.SetType) -> None:
    tree = ET.fromstring(input)
    t = parser.parse_set_type(tree)
    assert (t == expected)


def make_map_test_data(keyType: str,
                       valueType: str) -> typing.Tuple[str, ast.Type]:
    return ('<constant type="map">' + f'<keyType type="{keyType}" />' +
            f'<valueType type="{valueType}" />' + '</constant>',
            ast.MapType(keyType=keyType, valueType=valueType))


map_parser_data = [
    make_map_test_data(k, v) for k in basic_types for v in basic_types
]


@pytest.mark.parametrize('input,expected', map_parser_data)
def test_map_parser(input: str, expected: ast.MapType) -> None:
    tree = ET.fromstring(input)
    t = parser.parse_map_type(tree)
    assert (t == expected)


@pytest.mark.parametrize(
    'input,expected',
    basic_parser_data + list_parser_data + set_parser_data + map_parser_data)
def test_type_parser(input: str, expected: ast.Type) -> None:
    tree = ET.fromstring(input)
    t = parser.parse_type(tree)
    assert (t == expected)


def test_nested_list_parser() -> None:
    tree = ET.fromstring('''
    <constant type="list">
        <valueType type="list">
            <valueType type="double" />
        </valueType>
    </constant>
    ''')
    t = parser.parse_type(tree)
    assert (t == ast.ListType(ast.ListType('double')))


constant_parser_data = [
    ('<const name="Variable" type="string" doc="documentation"><string>value</string></const>',
     ast.Constant(
         name='Variable', type_='string', doc='documentation', value=None)),
    ('<const name="Variable" type="list" doc="documentation"><valueType type="double" /><list /></const>',
     ast.Constant(
         name='Variable',
         type_=ast.ListType('double'),
         doc='documentation',
         value=None))
]


@pytest.mark.parametrize('input,expected', constant_parser_data)
def test_constant_parser(input: str, expected: ast.Constant) -> None:
    tree = ET.fromstring(input)
    c = parser.parse_constant(tree)
    assert (c == expected)


def test_namespace_parser() -> None:
    tree = ET.fromstring('<namespace name="cl" value="tutorial" />')
    n = parser.parse_namespace(tree)
    assert (n == ast.Namespace(name='tutorial', language='cl'))


def test_typedef_parser() -> None:
    tree = ET.fromstring(
        '<typedef name="MyInteger"'
        ' doc="Thrift lets you do typedefs to get pretty names for your types. Standard C style here."'
        ' type="i32" />')
    td = parser.parse_typedef(tree)
    expected = ast.Typedef(
        name='MyInteger',
        type_='i32',
        doc=
        'Thrift lets you do typedefs to get pretty names for your types. Standard C style here.'
    )
    assert (td == expected)


def test_enum_parser() -> None:
    tree = ET.fromstring('''
    <enum name="Operation" doc="You can define enums, which are just 32 bit integers. Values are optional and start at 1 if not supplied, C style again.">
      <member name="ADD" value="1" />
      <member name="SUBTRACT" value="2" doc="doc of SUBTRACT" />
      <member name="MULTIPLY" value="3" />
      <member name="DIVIDE" value="4" />
    </enum>
    ''')
    expected = ast.Enum(
        name='Operation',
        doc=(
            'You can define enums, which are just 32 bit integers. ' +
            'Values are optional and start at 1 if not supplied, C style again.'
        ),
        members=[
            ast.EnumMember(name='ADD', value=1),
            ast.EnumMember(name='SUBTRACT', value=2, doc='doc of SUBTRACT'),
            ast.EnumMember(name='MULTIPLY', value=3),
            ast.EnumMember(name='DIVIDE', value=4)
        ])
    e = parser.parse_enum(tree)
    assert (e.name == expected.name)
    assert (e.doc == expected.doc)
    for m, em in zip(e.members, expected.members):
        assert (m == em)


def test_field_parser() -> None:
    tree = ET.fromstring(
        '<field name="op" field-id="3" type="id" type-module="Example" type-id="Operation" />'
    )
    expected = ast.Field(
        name='op',
        key=3,
        type_=ast.ReferenceType(module='Example', name='Operation'))
    assert (parser.parse_field(tree) == expected)


def test_arg_parser() -> None:
    tree = ET.fromstring(
        '<arg name="num1" field-id="1" type="i32" doc="document" required="optional" />'
    )
    expected = ast.Field(
        name='num1', key=1, required='optional', doc='document', type_='i32')
    assert (parser.parse_arg(tree) == expected)


def test_method_parser() -> None:
    tree = ET.fromstring('''
    <method name="zip" oneway="true" doc="oneway doc">
        <arg name="logid" field-id="1" type="i32" />
        <returns type="void" />
        <throws name="ouch" field-id="1" type="id" type-module="Example" type-id="InvalidOperation" />
    </method>
    ''')
    expected = ast.Function(
        name='zip',
        oneway=True,
        doc='oneway doc',
        returnType='void',
        arguments=[ast.Field(name='logid', key=1, type_='i32')])
    assert (parser.parse_method(tree) == expected)
