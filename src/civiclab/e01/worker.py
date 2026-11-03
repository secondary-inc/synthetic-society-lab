"""Prediction child process: stdin contains allowlisted historical features only.

Not a filesystem/network sandbox. No outcome file arguments or file reads.
"""
import json
import sys

from .pipeline import predict
from .isolation import deny_external_io


def main():
    method='S0'
    if sys.argv[1:]:
        if len(sys.argv)!=3 or sys.argv[1]!='--method' or sys.argv[2] not in {'S0','S_ZERO'}:
            raise ValueError('only frozen S0 and zero-margin worker methods allowed')
        method=sys.argv[2]
    deny_external_io()
    features = json.load(sys.stdin)
    if not isinstance(features, list) or not features:
        raise ValueError('nonempty feature list required')
    predictions=[predict(f) for f in features]
    if method=='S_ZERO':
        predictions=[{**p,'predicted_margin_pp':0.0} for p in predictions]
    json.dump(predictions, sys.stdout, allow_nan=False, sort_keys=True)


if __name__ == '__main__':
    main()
