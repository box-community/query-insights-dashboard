#!/usr/bin/env python3
"""Authenticate with Client Credentials Grant."""

from __future__ import annotations

import os
import sys

from box_sdk_gen import BoxCCGAuth, BoxClient, CCGConfig
from dotenv import load_dotenv

load_dotenv()


def _require_numeric_enterprise_id() -> str:
    enterprise_id = os.environ["BOX_ENTERPRISE_ID"].strip()
    if not enterprise_id.isdigit():
        print(
            "BOX_ENTERPRISE_ID must be the numeric Enterprise ID from "
            "Developer Console → Configuration → App Details → Properties (for example 123456789).\n"
            "A client ID or client secret in that variable causes "
            "invalid_grant / Grant credentials are invalid.",
            file=sys.stderr,
        )
        sys.exit(1)
    return enterprise_id


def get_box_client() -> BoxClient:
    auth = BoxCCGAuth(
        config=CCGConfig(
            client_id=os.environ["BOX_CLIENT_ID"],
            client_secret=os.environ["BOX_CLIENT_SECRET"],
            enterprise_id=_require_numeric_enterprise_id(),
        )
    )
    return BoxClient(auth=auth)
