from typing import Any, Tuple, List

from subprocess import check_call

from sphinx.ext.autodoc import Documenter, ModuleDocumenter

from sphinx_thrift.thrift_ast import (load_module, Constant, Typedef, Enum,
                                      Struct, Service, Function)


def document_constant(documenter: Documenter, cons: Constant) -> None:
    source_name = documenter.get_sourcename()
    documenter.add_line(f'.. thrift:constant:: {cons.name}', source_name)
    documenter.add_line(f'   :module: {documenter.module.name}', source_name)
    documenter.add_line(f'   :type: {cons.typeId}', source_name)
    documenter.add_line('', source_name)
    documenter.add_line(f'   {cons.doc}', source_name)


def document_typedef(documenter: Documenter, td: Typedef) -> None:
    source_name = documenter.get_sourcename()
    documenter.add_line(f'.. thrift:typedef:: {td.name}', source_name)
    documenter.add_line(f'   :module: {documenter.module.name}', source_name)
    documenter.add_line(f'   :target: {td.typeId}', source_name)
    documenter.add_line('', source_name)
    documenter.add_line(f'   {td.doc}', source_name)


class ThriftDocumenter(Documenter):
    objtype = 'object'
    titles_allowed = True


class ThriftModuleDocumenter(ThriftDocumenter):
    objtype = 'thrift_module'

    def __init__(self, directive: str, name: str, indent: str = '') -> None:
        super().__init__(directive, name, indent)
        self.filename = self.name + '.thrift'

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
        self.env.note_dependency(self.filename)
        check_call(['thrift', '--gen', 'json', '--out', self.env.doctreedir, self.filename])
        self.module = load_module(f'{self.env.doctreedir}/{self.name}.json')
        self._add_line(f'.. thrift:module:: {self.module.name}')
        self._add_line('')
        self._add_line(f'   {self.module.doc}')
        self._add_line('')
        self._generate_namespaces()
        self._generate_constants()
        self._generate_typedefs()
        self._generate_enums()
        self._generate_structs()
        self._generate_services()

    def _generate_namespaces(self) -> None:
        if not self.module.namespaces:
            return
        self._add_line('Language mapping')
        self._add_line('----------------')
        for ns in self.module.namespaces:
            self._add_line(f'* {ns.language}: :code:`{ns.name}`')
        self._add_line('')

    def _generate_constants(self) -> None:
        if not self.module.constants:
            return
        self._add_line('Constants')
        self._add_line('---------')
        for cons in self.module.constants:
            document_constant(self, cons)
        self._add_line('')

    def _generate_typedefs(self) -> None:
        if not self.module.typedefs:
            return
        self._add_line('Type aliases')
        self._add_line('------------')
        for td in self.module.typedefs:
            document_typedef(self, td)
        self._add_line('')

    def _generate_enum(self, enum: Enum) -> None:
        self._add_line(f'.. thrift:enum:: {enum.name}')
        self._add_line(f'   :module: {self.module.name}')
        self._add_line('')
        for name, value in enum.members.items():
            self._add_line(f'   .. thrift:enum_field:: {name}')
            self._add_line(f'      :module: {self.module.name}')
            self._add_line(f'      :enum: {enum.name}')
        self._add_line('')

    def _generate_enums(self) -> None:
        if not self.module.enums:
            return
        self._add_line('Enumerations')
        self._add_line('------------')
        for enum in self.module.enums:
            self._generate_enum(enum)
        self._add_line('')

    def _generate_struct(self, struct: Struct) -> None:
        self._add_line(f'.. thrift:struct:: {struct.name}')
        self._add_line(f'   :module: {self.module.name}')
        if struct.isException:
            self._add_line('   :exception:')
        self._add_line('')
        self._add_line(f'   {struct.doc}')
        self._add_line('')
        for m in struct.fields:
            self._add_line(f'   :{m.name}: {m.doc}')
        self._add_line('')
        for m in struct.fields:
            self._add_line(f'   .. thrift:struct_field:: {m.name}')
            self._add_line(f'      :module: {self.module.name}')
            self._add_line(f'      :struct: {struct.name}')
            self._add_line(f'      :type: {m.typeId}')
            self._add_line('')
            if m.default is not None:
                self._add_line(f'      :default: {m.default}')
                self._add_line('')
            self._add_line(f'      {m.doc}')
            self._add_line('')
        self._add_line('')

    def _generate_structs(self) -> None:
        if not self.module.structs:
            return
        self._add_line('Structs')
        self._add_line('-------')
        for struct in self.module.structs:
            self._generate_struct(struct)
        self._add_line('')

    def _generate_method(self, service: Service, method: Function) -> None:
        self._add_line(f'   .. thrift:service_method:: {method.name}')
        self._add_line(f'      :module: {self.module.name}')
        self._add_line(f'      :service: {service.name}')
        self._add_line('')
        doc = method.doc.replace('\n', ' ')
        self._add_line(f'      {doc}')
        self._add_line('')

    def _generate_service(self, service: Service) -> None:
        self._add_line(f'.. thrift:service:: {service.name}')
        self._add_line(f'   :module: {self.module.name}')
        self._add_line('')
        doc = service.doc.replace('\n', ' ')
        self._add_line(f'   {doc}')
        self._add_line('')
        for method in service.functions:
            self._generate_method(service, method)
        self._add_line('')

    def _generate_services(self) -> None:
        if not self.module.services:
            return
        self._add_line('Services')
        self._add_line('--------')
        for service in self.module.services:
            self._generate_service(service)
        self._add_line('')
