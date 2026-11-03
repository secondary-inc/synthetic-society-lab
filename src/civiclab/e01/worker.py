"""Prediction child process: stdin contains allowlisted historical features only.

Not a filesystem/network sandbox. No outcome file arguments or file reads.
"""
import json
import sys

from .pipeline import predict
from .isolation import deny_external_io


def main():
    deny_external_io()
    features = json.load(sys.stdin)
    if not isinstance(features, list) or not features:
        raise ValueError('nonempty feature list required')
    json.dump([predict(f) for f in features], sys.stdout, allow_nan=False, sort_keys=True)


if __name__ == '__main__':
    main()
