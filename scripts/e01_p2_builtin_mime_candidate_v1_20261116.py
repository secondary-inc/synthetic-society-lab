"""Unreleased Darwin-only public stdlib MIME configuration proposal.

Not wired into an installer. Call once on a fresh stdlib mimetypes module,
under the existing guest guards and before importing/running pip.
"""
import sys


def initialize_builtin_mime_types(module):
    if sys.platform != 'darwin':
        raise ValueError('MIME_PLATFORM')
    if module.inited is not False:
        raise ValueError('MIME_ALREADY_INITIALIZED')
    if type(module.knownfiles) is not list:
        raise ValueError('MIME_KNOWNFILES_SCHEMA')
    # Python 3.12 init(files=[]) still prepends knownfiles on the first call.
    # Both are documented public controls; no private database mutation.
    module.knownfiles = []
    module.init(files=[])
    if module.inited is not True or module.knownfiles != []:
        raise ValueError('MIME_INITIALIZATION_STATE')
    if module.guess_type('file:///MOCK/index.html', strict=False) != ('text/html', None):
        raise ValueError('MIME_BUILTIN_HTML')
    return {'mode': 'STDLIB_BUILTIN_TYPES_ONLY_DARWIN',
            'knownfiles': [], 'explicit_files': [], 'initialized': True}
