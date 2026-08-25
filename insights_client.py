#!/usr/bin/env python3
"""Authenticate with CCG and call the Box Query Insights API."""

from __future__ import annotations

import os

from box_sdk_gen import BoxCCGAuth, BoxClient, CCGConfig, FetchOptions
from dotenv import load_dotenv

load_dotenv()

INSIGHTS_URL = "https://api.box.com/2.0/query/insights"


def get_box_client() -> BoxClient:
    auth = BoxCCGAuth(
        config=CCGConfig(
            client_id=os.environ["BOX_CLIENT_ID"],
            client_secret=os.environ["BOX_CLIENT_SECRET"],
            enterprise_id=os.environ["BOX_ENTERPRISE_ID"],
        )
    )
    return BoxClient(auth=auth)


def post_insights(client: BoxClient, body: dict) -> dict:
    response = client.make_request(
        FetchOptions(url=INSIGHTS_URL, method="POST", data=body)
    )
    return response.data
