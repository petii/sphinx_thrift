from typing import List, Dict, Any, Optional

from dataclasses import dataclass
import json


@dataclass
class Namespace:
    name: str
    language: str


@dataclass
class Enum:
    name: str
    doc: str
    members: Dict[str, int]


@dataclass
class Typedef:
    name: str
    typeId: str
    doc: str


@dataclass
class Field:
    key: int
    name: str
    typeId: str
    required: str
    doc: str = ''
    default: Optional[Any] = None
    type: Optional[Any] = None


@dataclass
class Struct:
    name: str
    doc: str
    isException: bool
    isUnion: bool
    fields: List[Field]


@dataclass
class Constant:
    name: str
    typeId: str
    value: Any
    doc: str = ''
    type: Optional[dict] = None


@dataclass
class Function:
    name: str
    doc: str
    oneway: bool
    returnTypeId: str
    arguments: List[Field]


@dataclass
class Service:
    name: str
    doc: str
    functions: List[Function]


@dataclass
class Module:
    name: str
    doc: str
    namespaces: List[Namespace]
    enums: List[Enum]
    typedefs: List[Typedef]
    structs: List[Struct]
    constants: List[Constant]
    services: List[Service]


def parse_cls(cls, j):  # type: ignore
    return cls(**j)


def parse_enum(j: dict) -> Enum:
    return Enum(
        name=j['name'],
        doc=j['doc'],
        members={m['name']: m['value']
                 for m in j['members']})


def parse_struct(j: dict) -> Struct:
    fields = [parse_cls(Field, n) for n in j['fields']]
    return Struct(
        name=j['name'],
        doc=j['doc'],
        isException=j['isException'],
        isUnion=j['isUnion'],
        fields=fields)


def parse_function(j: dict) -> Function:
    return Function(
        name=j['name'],
        doc=j.get('doc', ''),
        oneway=j['oneway'],
        returnTypeId=j['returnTypeId'],
        arguments=[parse_cls(Field, n) for n in j['arguments']])


def parse_service(j: dict) -> Service:
    return Service(
        name=j['name'],
        doc=j.get('doc', ''),
        functions=[parse_function(n) for n in j['functions']])


def load_module(filename: str) -> Module:
    with open(filename, 'r') as f:
        j = json.load(f)
    name = j['name']
    doc = j['doc']
    namespaces = []
    for lang, name in j['namespaces'].items():
        namespaces.append(Namespace(name, lang))
    typedefs = [parse_cls(Typedef, n) for n in j['typedefs']]
    enums = [parse_enum(n) for n in j['enums']]
    structs: List[Struct] = [parse_struct(n) for n in j['structs']]
    constants = [parse_cls(Constant, n) for n in j['constants']]
    services: List[Service] = [parse_service(n) for n in j['services']]
    return Module(name, doc, namespaces, enums, typedefs, structs, constants,
                  services)
