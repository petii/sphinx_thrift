from typing import Dict, Any

from sphinx.application import Sphinx
from sphinx.domains.std import StandardDomain

__version__ = '0.1.0'


def setup(app: Sphinx) -> Dict[str, Any]:
    from sphinx_thrift.documenter import ThriftModuleDocumenter
    from sphinx_thrift.domain import ThriftDomain

    app.add_autodocumenter(ThriftModuleDocumenter)
    app.add_domain(ThriftDomain)
    StandardDomain.initial_data['labels']['thrift-modindex'] = (
        'thrift-modindex', '', 'Thrift Index')
    StandardDomain.initial_data['anonlabels']['thrift-modindex'] = (
        'thrift-modindex', '')
    return {'version': __version__}
