#!/usr/bin/env python3
"""Contract analytics dashboard powered by the Box Query Insights API."""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://api.box.com/oauth2/token"
INSIGHTS_URL = "https://api.box.com/2.0/query/insights"

REQUIRED_ENV = (
    "BOX_CLIENT_ID",
    "BOX_CLIENT_SECRET",
    "BOX_ENTERPRISE_ID",
    "FOLDER_ID",
    "TEMPLATE_REF",
    "FIELD_CONTRACT_TYPE",
    "FIELD_CONTRACT_VALUE",
)


def require_env() -> None:
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        names = ", ".join(missing)
        print(
            f"Missing required environment variables: {names}\n"
            "Copy .env.example to .env and fill in your Box credentials.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_access_token() -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["BOX_CLIENT_ID"],
            "client_secret": os.environ["BOX_CLIENT_SECRET"],
            "box_subject_type": "enterprise",
            "box_subject_id": os.environ["BOX_ENTERPRISE_ID"],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def post_insights(access_token: str, body: dict) -> dict:
    response = requests.post(
        INSIGHTS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def count_contracts(access_token: str, template_ref: str, folder_id: str) -> int:
    """Return totalResultCount for items matching the template in folder_id."""
    payload = {
        "query": {
            "predicate": "EXISTS(:templateArg)",
            "params": {"templateArg": template_ref},
            "ancestors": [{"id": folder_id, "type": "folder"}],
        },
        "metrics": {},
    }
    result = post_insights(access_token, payload)
    overall = next(entry for entry in result["insights"] if entry["type"] == "overall")
    return overall["metrics"]["totalResultCount"]["values"]["count"]


def contract_value_stats(
    access_token: str,
    template_ref: str,
    folder_id: str,
    value_field: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Return avg / min / max contract value for a created_at date range."""
    payload = {
        "query": {
            "predicate": (
                "EXISTS(:templateArg) AND "
                "box:item:created_at >= :startDate AND "
                "box:item:created_at < :endDate"
            ),
            "params": {
                "templateArg": template_ref,
                "startDate": start_date,
                "endDate": end_date,
            },
            "ancestors": [{"id": folder_id, "type": "folder"}],
        },
        "metrics": {
            "avgContractValue": {"type": "avg", "field": value_field},
            "minContractValue": {"type": "min", "field": value_field},
            "maxContractValue": {"type": "max", "field": value_field},
        },
    }
    result = post_insights(access_token, payload)
    overall = next(entry for entry in result["insights"] if entry["type"] == "overall")
    return {
        alias: metric["values"][metric["type"]]
        for alias, metric in overall["metrics"].items()
    }


def top_contract_types(
    access_token: str,
    template_ref: str,
    folder_id: str,
    type_field: str,
    value_field: str,
    bucket_limit: int = 5,
) -> list[dict]:
    """Return top contract-type buckets with sum and count metrics."""
    payload = {
        "query": {
            "predicate": "EXISTS(:templateArg)",
            "params": {"templateArg": template_ref},
            "ancestors": [{"id": folder_id, "type": "folder"}],
            "group_by": [{"field": type_field, "bucket_limit": bucket_limit}],
        },
        "metrics": {
            "totalContractValue": {"type": "sum", "field": value_field},
            "countByType": {"type": "count", "field": type_field},
        },
    }
    result = post_insights(access_token, payload)

    groups: list[dict] = []
    for entry in result["insights"]:
        if entry["type"] == "group":
            groups.append(
                {
                    "contract_type": entry["key"][0],
                    "total_value": entry["metrics"]["totalContractValue"]["values"]["sum"],
                    "count": entry["metrics"]["countByType"]["values"]["count"],
                }
            )
        elif entry["type"] == "other":
            groups.append(
                {
                    "contract_type": "Other",
                    "count": entry["metrics"]["totalCountBeyondTopGroups"]["values"][
                        "count"
                    ],
                }
            )
    return groups


def print_contract_dashboard() -> None:
    access_token = get_access_token()
    folder_id = os.environ["FOLDER_ID"]
    template_ref = os.environ["TEMPLATE_REF"]
    type_field = os.environ["FIELD_CONTRACT_TYPE"]
    value_field = os.environ["FIELD_CONTRACT_VALUE"]

    total = count_contracts(access_token, template_ref, folder_id)
    stats = contract_value_stats(
        access_token,
        template_ref,
        folder_id,
        value_field,
        "2020-01-01T00:00:00Z",
        "2030-01-01T00:00:00Z",
    )
    groups = top_contract_types(
        access_token, template_ref, folder_id, type_field, value_field
    )

    print("Contract analytics dashboard")
    print("=" * 40)
    print(f"Total contracts: {total}")
    print(
        "Value range: "
        f"avg={stats['avgContractValue']}, "
        f"min={stats['minContractValue']}, "
        f"max={stats['maxContractValue']}"
    )
    print("Top contract types by value:")
    for row in groups:
        print(f"  {row}")


def main() -> None:
    require_env()
    try:
        print_contract_dashboard()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        body = exc.response.text if exc.response is not None else str(exc)
        print(f"Box API error ({status}): {body}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
