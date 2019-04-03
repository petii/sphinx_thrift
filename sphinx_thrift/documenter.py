from typing import Any, Tuple, List, Callable, Dict, Union

from subprocess import check_call

from sphinx.ext.autodoc import Documenter, ModuleDocumenter

import sphinx_thrift.thrift_ast as ast
from sphinx_thrift.thrift_ast import (Constant, Typedef, Enum, Struct, Service,
                                      Function)


def typeId(type_: ast.Type) -> str:
    dispatch = {
        ast.ListType:
        lambda p: 'list<{}>'.format(typeId(p.valueType)),
        ast.SetType:
        lambda p: 'set<{}>'.format(typeId(p.valueType)),
        ast.MapType:
        lambda p: 'map<{},{}>'.format(typeId(p.keyType), typeId(p.valueType)),
        ast.ReferenceType:
        lambda r: (r.module + '.' if r.module else '') + r.name,
        str:
        lambda s: s.strip()
    }
    return dispatch[type_.__class__](type_)


class _DirectiveGenerator:
    def __init__(self,
                 add_line: Callable[[str], None],
                 directive: str,
                 indent: int = 0) -> None:
        self._add_line = add_line
        self.directive = directive
        self.indent = indent * ' '

    def add_line(self, content: str) -> None:
        self._add_line(self.indent + content)

    def add_header(self, name: str, attributes: Dict[str, str]) -> None:
        self.add_line('.. thrift:{}:: {}'.format(self.directive, name))
        for item in attributes.items():
            self.add_line('   :{}: {}'.format(*item))
        self.add_line('')

    def add_fields(self, fields: List[Tuple[str, Union[str, Tuple[str, str]]]]
                   ) -> None:
        for name, value in fields:
            if isinstance(value, str):
                self.add_line('   :{}: {}'.format(name, value))
            else:
                self.add_line('   :{} {}: {}'.format(name, *value))
        self.add_line('')

    def add_doc(self, doc: str) -> None:
        self.add_line('   ' + doc)
        self.add_line('')

    def generate(self,
                 name: str,
                 doc: str,
                 attributes: Dict[str, str] = {},
                 fields: List[Tuple[str, Union[str, Tuple[str, str]]]] = []
                 ) -> None:
        self.add_header(name, attributes)
        self.add_fields(fields)
        self.add_doc(doc)


class ThriftDocumenter(Documenter):
    objtype = 'object'
    titles_allowed = True


class ThriftModuleDocumenter(ThriftDocumenter):
    objtype = 'thrift_module'
    module: ast.Module

    def __init__(self, directive: str, name: str, indent: str = '') -> None:
        super().__init__(directive, name, indent)
        self.filename = self.name + '.thrift'
        self.module_generator = self._create_generator('module')
        self.service_generator = self._create_generator('service')
        self.method_generator = self._create_generator(
            'service_method', indent=3)
        self.enum_generator = self._create_generator('enum')
        self.enum_field_generator = self._create_generator(
            'enum_field', indent=3)
        self.struct_generator = self._create_generator('struct')
        self.struct_field_generator = self._create_generator(
            'struct_field', indent=3)
        self.constant_generator = self._create_generator('constant')
        self.typedef_generator = self._create_generator('typedef')

    def _create_generator(self, name: str,
                          indent: int = 0) -> _DirectiveGenerator:
        return _DirectiveGenerator(self._add_line, name, indent)

    @classmethod
    def can_document_member(cls, member: Any, membername: str, isattr: bool,
                            parent: Any) -> bool:
        """Called to see if a member can be documented by this documenter."""
        return False

    def get_sourcename(self) -> str:
        return f'{self.filename}:docstring of {self.name}'

    def _add_line(self, content: str) -> None:
        self.add_line(content, self.get_sourcename())

    def generate(self,
                 more_content: Any = None,
                 real_modname: str = None,
                 check_module: bool = False,
                 all_members: bool = False) -> None:
        from sphinx_thrift.parser import load_module
        import os.path

        self.env.note_dependency(self.filename)
        base_name = os.path.basename(self.name)
        check_call([
            'thrift', '--gen', 'xml', '--out', self.env.doctreedir,
            self.filename
        ])
        self.module = load_module(f'{self.env.doctreedir}/{base_name}.xml')
        self.module_generator.generate(
            self.module.name,
            self.module.doc,
            fields=[(ns.language, ':code:`' + ns.name + '`')
                    for ns in self.module.namespaces])
        self._generate_constants()
        self._generate_typedefs()
        self._generate_enums()
        self._generate_structs()
        self._generate_services()

    def _generate_constants(self) -> None:
        if not self.module.constants:
            return
        self._add_line('Constants')
        self._add_line('---------')
        for cons in self.module.constants:
            self.constant_generator.generate(cons.name, cons.doc, {
                'module': self.module.name,
                'type': typeId(cons.type_)
            })

    def _generate_typedefs(self) -> None:
        if not self.module.typedefs:
            return
        self._add_line('Type aliases')
        self._add_line('------------')
        for td in self.module.typedefs:
            self.typedef_generator.generate(td.name, td.doc, {
                'module': self.module.name,
                'target': typeId(td.type_)
            })

    def _generate_enum(self, enum: Enum) -> None:
        self.enum_generator.generate(
            enum.name, enum.doc, attributes={'module': self.module.name})
        for member in enum.members:
            self.enum_field_generator.generate(
                member.name,
                member.doc,
                attributes={
                    'module': self.module.name,
                    'enum': enum.name,
                    'value': str(member.value)
                })

    def _generate_enums(self) -> None:
        if not self.module.enums:
            return
        self._add_line('Enumerations')
        self._add_line('------------')
        for enum in self.module.enums:
            self._generate_enum(enum)

    def _generate_struct(self, struct: Struct) -> None:
        attributes = {'module': self.module.name}
        if struct.isException:
            attributes['exception'] = ''
        self.struct_generator.generate(
            struct.name, struct.doc, attributes=attributes)
        for m in struct.fields:
            member_attrs = {
                'module': self.module.name,
                'struct': struct.name,
                'type': typeId(m.type_)
            }
            fields = {}
            if m.default is not None:
                fields['default'] = m.default
            self.struct_field_generator.generate(
                m.name, m.doc, attributes=member_attrs, fields=fields)

    def _generate_structs(self) -> None:
        if not self.module.structs:
            return
        self._add_line('Structs')
        self._add_line('-------')
        for struct in self.module.structs:
            self._generate_struct(struct)

    def _generate_method(self, service: Service, method: Function) -> None:
        params = ' '.join(
            f'{p.name};{typeId(p.type_)}' for p in method.arguments)
        attributes = {
            'module': self.module.name,
            'service': service.name,
            'return_type': typeId(method.returnType),
            'parameters': params
        }
        if method.oneway:
            attributes['oneway'] = ''
        fields = []
        for p in method.arguments:
            fields.append(('param', (p.name, p.doc)))
        self.method_generator.generate(
            method.name, method.doc, attributes=attributes, fields=fields)

    def _generate_service(self, service: Service) -> None:
        self.service_generator.generate(
            service.name, service.doc, attributes={'module': self.module.name})
        for method in service.functions:
            self._generate_method(service, method)

    def _generate_services(self) -> None:
        if not self.module.services:
            return
        self._add_line('Services')
        self._add_line('--------')
        for service in self.module.services:
            self._generate_service(service)
