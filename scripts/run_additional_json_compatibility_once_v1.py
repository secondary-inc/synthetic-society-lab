#!/usr/bin/env python3
"""One-shot exact-packet launcher candidate; no packet or allowance is created."""
import argparse
import json
from pathlib import Path
import sys

from civiclab.additional_compatibility_terminal_v1 import run_once
from civiclab.production_compatibility_v4_2_1 import _SafeExecutionFailure,_safe_error_kind


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet-sha256',required=True)
    parser.add_argument('--accept-prior-unknown-charge-one-additional-request',action='store_true')
    parser.add_argument('--confirm-rotated-dedicated-key',action='store_true')
    parser.add_argument('--confirm-prefunded-no-purchase',action='store_true')
    args=parser.parse_args(argv)
    try:
        result=run_once(Path(__file__).resolve().parents[1]/'configs/json_compatibility_additional_v1_terminal_packet.json',
            args.packet_sha256,
            accept_prior_unknown=args.accept_prior_unknown_charge_one_additional_request,
            confirm_rotated_dedicated_key=args.confirm_rotated_dedicated_key,
            confirm_prefunded_no_purchase=args.confirm_prefunded_no_purchase)
        print(json.dumps(result['summary'],sort_keys=True))
        return 0 if result['summary']['status']=='COMPATIBLE' else 2
    except BaseException as error:
        # Never print exception strings, credentials, raw response bodies or
        # arbitrary class names. The private fixed-run evidence remains intact.
        output={'status':'STOPPED_NO_RETRY','error_type':_safe_error_kind(error),'automatic_retry':False}
        if type(error) is _SafeExecutionFailure:output['diagnostic']=error.diagnostic
        print(json.dumps(output,sort_keys=True))
        return 2


if __name__=='__main__':sys.exit(main())
