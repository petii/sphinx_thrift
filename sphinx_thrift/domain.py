from typing import Any, Tuple, List, Union, Iterable, Dict, Optional, Callable

import re
from dataclasses import dataclass
from itertools import groupby

from sphinx.ext.autodoc import Documenter
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.domains import Domain, ObjType, Index
from sphinx.roles import XRefRole
from sphinx import addnodes
from sphinx.addnodes import desc_signature, desc_annotation, desc_name, desc_type, desc_addname, desc_content, pending_xref
from sphinx.util import docfields, logging
from sphinx.util.nodes import make_refnode

from docutils import nodes
from docutils.parsers.rst.directives import unchanged, unchanged_required, flag

list_re = re.compile(r'^(list|set)<(.*)>$')
map_re = re.compile(r'^map<(.*),(.*)>$')


def make_desc_type(content: str) -> desc_type:
    return desc_type(content, content)


def parse_type(typename: str,
               inner_node: Callable[[str], nodes.Node]) -> List[nodes.Node]:
    typename = typename.replace(' ', '')
    m = list_re.match(typename)
    if m:
        return [inner_node(m.group(1) + '<')] + parse_type(
            m.group(2), inner_node) + [inner_node('>')]
    m = map_re.match(typename)
    if m:
        return [inner_node('map<')] + parse_type(m.group(1), inner_node) + [
            inner_node(', ')
        ] + parse_type(m.group(2), inner_node) + [inner_node('>')]
    return [
        pending_xref(
            '',
            inner_node(typename),
            refdomain='thrift',
            refexplicit=False,
            reftarget=typename,
            reftype='field')
    ]


@dataclass(frozen=True, unsafe_hash=True)
class Signature:
    kind: str
    name: str
    module: Optional[str]

    def __str__(self) -> str:
        return f'{self.module}.{self.name}:{self.kind}'


class ThriftObject(ObjectDescription):
    def add_target_and_index(self, name: Signature, sig: str,
                             signode: desc_signature) -> None:
        if name not in self.state.document.ids:
            signode['names'].append(name)
            signode['ids'].append(name)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            self.env.domaindata['thrift']['objects'][name] = (self.env.docname,
                                                              self.objtype,
                                                              str(name))


class ThriftModule(ThriftObject):
    def handle_signature(self, sig: str, signode: Any) -> Signature:
        signode += desc_annotation('module ', 'module ')
        signode += desc_name(sig, sig)
        return Signature(self.objtype, sig, None)


class ThriftConstant(ThriftObject):
    required_arguments = 1
    option_spec = {'module': unchanged_required, 'type': unchanged_required}

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        signode += desc_annotation(self.objtype, self.objtype)
        module_name = self.options['module'] + '.'
        signode += desc_name(sig, sig)
        signode += desc_type(': ', ': ')
        signode.extend(parse_type(self.options['type'], make_desc_type))
        return Signature(self.objtype, sig, self.options['module'])


class ThriftTypedef(ThriftObject):
    required_arguments = 1
    option_spec = {'module': unchanged_required, 'target': unchanged_required}

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        signode += desc_annotation(self.objtype, self.objtype)
        module_name = self.options['module'] + '.'
        signode += desc_name(sig, sig)
        signode += desc_type(' = ', ' = ')
        signode.extend(parse_type(self.options['target'], make_desc_type))
        return Signature(self.objtype, sig, self.options['module'])


class ThriftEnum(ThriftObject):
    required_arguments = 1
    option_spec = {'module': unchanged_required}

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        signode += desc_annotation(self.objtype, self.objtype)
        module_name = self.options['module'] + '.'
        signode += desc_name(sig, sig)
        return Signature(self.objtype, sig, self.options['module'])


class ThriftEnumField(ThriftObject):
    option_spec = {
        'module': unchanged_required,
        'enum': unchanged_required,
        'value': unchanged_required
    }

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        enum_name = self.options['enum'] + '.'
        signode += desc_addname(enum_name, enum_name)
        signode += desc_name(sig, sig)
        signode += desc_annotation(' = ' + self.options['value'],
                                   ' = ' + self.options['value'])
        return Signature(self.objtype, enum_name + sig, self.options['module'])


class ThriftStruct(ThriftObject):
    required_arguments = 1
    option_spec = {'module': unchanged_required, 'exception': flag}

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        annotation = 'exception' if 'exception' in self.options else self.objtype
        signode += desc_annotation(annotation, annotation)
        module_name = self.options['module'] + '.'
        signode += desc_name(sig, sig)
        return Signature(self.objtype, sig, self.options['module'])


class ThriftStructField(ThriftObject):
    required_arguments = 1
    option_spec = {
        'module': unchanged_required,
        'struct': unchanged_required,
        'type': unchanged_required
    }

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        annotation = 'field'
        signode += desc_annotation(annotation, annotation)
        struct_name = self.options['struct'] + '.'
        signode += desc_name(sig, sig)
        signode += desc_type(': ', ': ')
        signode.extend(parse_type(self.options['type'], make_desc_type))
        return Signature(self.objtype, struct_name + sig,
                         self.options['module'])


class ThriftService(ThriftObject):
    required_arguments = 1
    option_spec = {'module': unchanged_required}

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        annotation = 'service'
        signode += desc_annotation(annotation, annotation)
        module_name = self.options['module'] + '.'
        # signode += desc_addname(module_name, module_name)
        signode += desc_name(sig, sig)
        return Signature(self.objtype, sig, self.options['module'])


def parameter_list(arg: str) -> List[Tuple[str, str]]:
    if arg is None:
        return []
    return [(p.split(';')[0], p.split(';')[1]) for p in arg.split()]


class ThriftServiceMethod(ThriftObject):
    required_arguments = 1
    option_spec = {
        'module': unchanged_required,
        'service': unchanged_required,
        'parameters': parameter_list,
        'exceptions': parameter_list,
        'return_type': unchanged_required,
        'oneway': flag
    }

    doc_field_types = [
        docfields.TypedField(
            'parameter',
            label='Parameters',
            names=('param', ),
            typenames=('type', ),
            typerolename='field',
            can_collapse=True),
        docfields.TypedField(
            'exception',
            label='Exceptions',
            names=('throws',),
            typenames=('type',),
            typerolename='field',
            can_collapse=True
        )
    ]

    def handle_signature(self, sig: str, signode: desc_signature) -> Signature:
        if 'oneway' in self.options:
            signode += desc_annotation('oneway', 'oneway')
        signode += desc_type(self.options['return_type'] + ' ',
                             self.options['return_type'] + ' ')
        service_name = self.options['service'] + '.'
        signode += desc_name(sig, sig)
        signode += desc_addname('(', '(')
        first = True
        for name, type_ in self.options['parameters']:
            if first:
                first = False
            else:
                signode += desc_addname(', ', ', ')
            signode.extend(parse_type(type_, make_desc_type))
            signode += make_desc_type(' ')
            signode += desc_addname(name, name)
        signode += desc_addname(')', ')')
        first = True
        if self.options['exceptions']:
            signode += desc_addname(' throws (', ' throws (')
        for name, type_ in self.options['exceptions']:
            if first:
                first = False
            else:
                signode += desc_addname(', ', ', ')
            signode.extend(parse_type(type_, make_desc_type))
            signode += make_desc_type(' ')
            signode += desc_addname(name, name)
        if self.options['exceptions']:
            signode += desc_addname(')', ')')
        return Signature(self.objtype, service_name + sig,
                         self.options['module'])


class ThriftXRefRole(XRefRole):
    @staticmethod
    def find_target(env, typ: str, target: str) -> Optional[Tuple[str, str]]:
        if typ == 'module':
            target = f'None.{target}'
        moduleless_results = []
        for sig, obj in env.domaindata['thrift']['objects'].items():
            if f'{sig.module}.{sig.name}' == target:
                return (obj[0], f'{sig.module}.{sig.name}:{sig.kind}')
            if sig.name == target:
                moduleless_results.append(
                    (obj[0], f'{sig.module}.{sig.name}:{sig.kind}'))
        if len(moduleless_results) == 1:
            return moduleless_results[0]
        elif len(moduleless_results) > 1:
            logger = logging.getLogger(__name__)
            logger.warning(f'{target} is ambiguous. Possible resolutions:')
            for tgt in moduleless_results:
                logger.warning(f'   {tgt[0]}: {tgt[1]}')
        return None

    def process_link(self, env, refnode, has_explicit_title: bool, title: str,
                     target: str) -> Tuple[str, str]:
        return title, target


class ThriftIndex(Index):
    name = 'modindex'
    localname = 'Thrift Index'
    shortname = 'Index'

    def generate(
            self, docnames: Iterable[str] = None
    ) -> Tuple[List[Tuple[str, List[List[Union[str, int]]]]], bool]:
        entries = []
        for name, (docname, objtype,
                   signature) in self.domain.data['objects'].items():
            entries.append([name.name, 0, docname, signature, objtype, '', ''])
        content: Dict[str, list] = {}
        for key, group in groupby(entries, key=lambda t: t[0][0].upper()):
            if key not in content:
                content[key] = []
            content[key].extend(group)
        return sorted(content.items(), key=lambda t: t[0]), False


class ThriftDomain(Domain):
    name = 'thrift'
    object_types = {
        'module': ObjType('module', 'module'),
        'namespace': ObjType('namespace', 'namespace'),
        'constant': ObjType('constant', 'constant'),
        'typedef': ObjType('typedef', 'typedef'),
        'enum': ObjType('enum', 'enum'),
        'enum_field': ObjType('enum_field', 'enum_field'),
        'struct': ObjType('struct', 'struct'),
        'struct_field': ObjType('struct_field', 'struct_field'),
        'exception': ObjType('struct', 'struct'),
        'exception_field': ObjType('struct_field', 'struct_field'),
        'service': ObjType('service', 'service'),
        'service_method': ObjType('service_method', 'service_method')
    }
    directives = {
        'module': ThriftModule,
        'constant': ThriftConstant,
        'typedef': ThriftTypedef,
        'enum': ThriftEnum,
        'enum_field': ThriftEnumField,
        'struct': ThriftStruct,
        'struct_field': ThriftStructField,
        'exception': ThriftStruct,
        'exception_field': ThriftStructField,
        'service': ThriftService,
        'service_method': ThriftServiceMethod
    }
    roles = {
        'module': ThriftXRefRole(),
        'constant': ThriftXRefRole(),
        'typedef': ThriftXRefRole(),
        'enum': ThriftXRefRole(),
        'enum_field': ThriftXRefRole(),
        'struct': ThriftXRefRole(),
        'struct_field': ThriftXRefRole(),
        'exception': ThriftXRefRole(),
        'exception_field': ThriftXRefRole(),
        'service': ThriftXRefRole(),
        'service_method': ThriftXRefRole()
    }
    indices = [ThriftIndex]
    initial_data: Dict[str, Any] = {'objects': {}}

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        targetdata = ThriftXRefRole.find_target(env, typ, target)
        if targetdata is not None:
            todoc, tgt = targetdata
            return make_refnode(builder, fromdocname, todoc, tgt, contnode)
        else:
            return None
