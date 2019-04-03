from typing import List, Dict, Any, Optional, Union

import attr

AtomicType = str
Type = Union[AtomicType, 'ListType', 'SetType', 'MapType', 'ReferenceType']


@attr.s(auto_attribs=True)
class ListType:
    valueType: Type


@attr.s(auto_attribs=True)
class SetType:
    valueType: Type


@attr.s(auto_attribs=True)
class MapType:
    keyType: Type
    valueType: Type


@attr.s(auto_attribs=True)
class ReferenceType:
    module: str
    name: str


@attr.s(auto_attribs=True)
class Namespace:
    name: str
    language: str


@attr.s(auto_attribs=True)
class EnumMember:
    name: str
    value: int
    doc: str = ''


@attr.s(auto_attribs=True)
class Enum:
    name: str
    members: List[EnumMember]
    doc: str = ''


@attr.s(auto_attribs=True)
class Typedef:
    name: str
    type_: Type
    doc: str = ''


@attr.s(auto_attribs=True)
class Field:
    key: int
    name: str
    type_: Type
    required: str = 'required'
    doc: str = ''
    default: Optional[Any] = None
    type: Optional[Any] = None


@attr.s(auto_attribs=True)
class Struct:
    name: str
    isException: bool
    isUnion: bool
    fields: List[Field]
    doc: str = ''


@attr.s(auto_attribs=True)
class Constant:
    name: str
    type_: Type
    value: Any
    doc: str = ''


@attr.s(auto_attribs=True)
class Function:
    name: str
    oneway: bool
    returnType: Type
    arguments: List[Field]
    exceptions: List[Field]
    doc: str = ''


@attr.s(auto_attribs=True)
class Service:
    name: str
    functions: List[Function]
    doc: str = ''


@attr.s(auto_attribs=True)
class Module:
    name: str
    namespaces: List[Namespace]
    enums: List[Enum]
    typedefs: List[Typedef]
    structs: List[Struct]
    constants: List[Constant]
    services: List[Service]
    doc: str = ''
