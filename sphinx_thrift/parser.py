from typing import Dict, Callable, List

from enum import Enum

import xml.etree.ElementTree as ET

import sphinx_thrift.thrift_ast as ast


class Tag(Enum):
    NAMESPACE = 'namespace'
    CONSTANT = 'const'
    TYPEDEF = 'typedef'
    ENUM = 'enum'
    FIELD = 'field'
    ARG = 'arg'
    STRUCT = 'struct'
    EXCEPTION = 'exception'
    SERVICE = 'service'
    METHOD = 'method'
    THROWS = 'throws'


def parse_list_type(root: ET.Element) -> ast.ListType:
    value_node = root.find('elemType')
    assert (value_node is not None)
    return ast.ListType(valueType=parse_type(value_node))


def parse_set_type(root: ET.Element) -> ast.SetType:
    value_node = root.find('elemType')
    assert (value_node is not None)
    return ast.SetType(valueType=parse_type(value_node))


def parse_map_type(root: ET.Element) -> ast.MapType:
    key_node = root.find('keyType')
    value_node = root.find('valueType')
    assert (key_node is not None)
    assert (value_node is not None)
    return ast.MapType(
        keyType=parse_type(key_node), valueType=parse_type(value_node))


def parse_reference_type(root: ET.Element) -> ast.ReferenceType:
    return ast.ReferenceType(
        module=root.attrib['type-module'], name=root.attrib['type-id'])


def parse_type(root: ET.Element) -> ast.Type:
    type_funcs: Dict[str, Callable[[ET.Element], ast.Type]] = {
        'list': parse_list_type,
        'set': parse_set_type,
        'map': parse_map_type,
        'id': parse_reference_type
    }
    t = root.attrib['type']
    return type_funcs.get(t, lambda _: t)(root)


def parse_namespace(root: ET.Element) -> ast.Namespace:
    assert (root.tag == Tag.NAMESPACE.value)
    return ast.Namespace(
        name=root.attrib['value'], language=root.attrib['name'])


def parse_constant(root: ET.Element) -> ast.Constant:
    assert (root.tag == Tag.CONSTANT.value)
    return ast.Constant(
        name=root.attrib['name'],
        doc=root.attrib.get('doc', ''),
        type_=parse_type(root),
        value=None)


def parse_typedef(root: ET.Element) -> ast.Typedef:
    assert (root.tag == Tag.TYPEDEF.value)
    return ast.Typedef(
        name=root.attrib['name'],
        doc=root.get('doc', ''),
        type_=parse_type(root))


def parse_enum(root: ET.Element) -> ast.Enum:
    def parse_members() -> List[ast.EnumMember]:
        return [
            ast.EnumMember(
                name=n.attrib['name'],
                doc=n.attrib.get('doc', ''),
                value=int(n.attrib['value'])) for n in root
        ]

    assert (root.tag == Tag.ENUM.value)
    return ast.Enum(
        name=root.attrib['name'],
        doc=root.attrib.get('doc', ''),
        members=parse_members())


def _parse_field_with_tag(tag: str, root: ET.Element) -> ast.Field:
    assert (root.tag == tag)
    return ast.Field(
        name=root.attrib['name'],
        key=int(root.attrib['field-id']),
        doc=root.get('doc', ''),
        required=root.get('required', 'required'),
        type_=parse_type(root))


def parse_field(root: ET.Element) -> ast.Field:
    return _parse_field_with_tag(Tag.FIELD.value, root)


def parse_arg(root: ET.Element) -> ast.Field:
    return _parse_field_with_tag(Tag.ARG.value, root)


def parse_throws(root: ET.Element) -> ast.Field:
    return _parse_field_with_tag(Tag.THROWS.value, root)


def parse_struct(root: ET.Element) -> ast.Struct:
    assert (root.tag == Tag.STRUCT.value)
    return ast.Struct(
        name=root.attrib['name'],
        doc=root.get('doc', ''),
        isException=False,
        isUnion=False,
        fields=[parse_field(f) for f in root if f.tag == Tag.FIELD.value])


def parse_exception(root: ET.Element) -> ast.Struct:
    assert (root.tag == Tag.EXCEPTION.value)
    return ast.Struct(
        name=root.attrib['name'],
        doc=root.get('doc', ''),
        isException=True,
        isUnion=False,
        fields=[parse_field(f) for f in root if f.tag == Tag.FIELD.value])


def parse_method(root: ET.Element) -> ast.Function:
    assert (root.tag == Tag.METHOD.value)
    returns = root.find('returns')
    assert (returns is not None)
    return ast.Function(
        name=root.attrib['name'],
        doc=root.get('doc', ''),
        oneway=root.get('oneway', 'false') == 'true',
        returnType=parse_type(returns),
        arguments=list(map(parse_arg, root.findall(Tag.ARG.value))),
        exceptions=list(map(parse_throws, root.findall(Tag.THROWS.value))))


def parse_service(root: ET.Element) -> ast.Service:
    assert (root.tag == Tag.SERVICE.value)
    return ast.Service(
        name=root.attrib['name'],
        doc=root.attrib.get('doc', ''),
        functions=[parse_method(m) for m in root])

def parse_module(root: ET.Element) -> ast.Module:
    assert(root.tag == 'document')
    return ast.Module(
        name=root.attrib['name'],
        doc=root.attrib.get('doc', ''),
        namespaces=[
            parse_namespace(ns) for ns in root.findall(Tag.NAMESPACE.value)
        ],
        typedefs=[
            parse_typedef(td) for td in root.findall(Tag.TYPEDEF.value)
        ],
        constants=[
            parse_constant(const) for const in root.findall(Tag.CONSTANT.value)
        ],
        enums=[parse_enum(enum) for enum in root.findall(Tag.ENUM.value)],
        structs=[
            parse_struct(struct) for struct in root.findall(Tag.STRUCT.value)
        ] + [
            parse_exception(exc) for exc in root.findall(Tag.EXCEPTION.value)
        ],
        services=[
            parse_service(service) for service in root.findall(Tag.SERVICE.value)
        ]
    )

def load_module(filename: str) -> ast.Module:
    et = ET.iterparse(filename)
    for _, el in et:
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]  # strip all namespaces
        for at in el.attrib.keys(): # strip namespaces of attributes too
            if '}' in at:
                newat = at.split('}', 1)[1]
                el.attrib[newat] = el.attrib[at]
                del el.attrib[at]
    root = et.root  # type: ignore
    docu = root.find('document')
    assert(docu is not None)
    return parse_module(docu)
