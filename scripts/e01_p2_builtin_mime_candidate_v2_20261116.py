"""Unreleased Darwin-only public stdlib MIME configuration proposal v2.

Clear public knownfiles and rebuild through public init(files=None), so the
result is independent of previous initialized database state. No pip execution.
"""
import sys


def initialize_builtin_mime_types(module):
    if sys.platform != 'darwin':
        raise ValueError('MIME_PLATFORM')
    if type(module.inited) is not bool or type(module.knownfiles) is not list:
        raise ValueError('MIME_STATE_SCHEMA')
    module.knownfiles = []
    # files=None forces reconstruction on both fresh and initialized modules;
    # an empty explicit list alone can retain an already populated database.
    module.init(files=None)
    if module.inited is not True or module.knownfiles != []:
        raise ValueError('MIME_INITIALIZATION_STATE')
    if module.guess_type('file:///MOCK/index.html', strict=False) != ('text/html', None):
        raise ValueError('MIME_BUILTIN_HTML')
    return {'mode': 'STDLIB_BUILTIN_TYPES_ONLY_DARWIN',
            'knownfiles': [], 'init_files': None, 'initialized': True}
