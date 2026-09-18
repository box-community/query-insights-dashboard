#!/usr/bin/env python3
"""Print a console contract analytics report from Query Insights."""

from __future__ import annotations

import os
import sys

from box_sdk_gen import BoxAPIError
from dotenv import load_dotenv

from box_client import get_box_client
from reports import contract_value_stats, count_contracts, top_contract_types

load_dotenv()

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
            "Copy .env.example to .env, fill in CCG credentials, then run "
            "python setup_test_data.py and paste the printed folder and "
            "template values.",
            file=sys.stderr,
        )
        sys.exit(1)


def print_contract_dashboard(
    template_ref: str,
    type_field: str,
    value_field: str,
) -> None:
    client = get_box_client()
    folder_id = os.environ["FOLDER_ID"]

    total = count_contracts(client, template_ref, folder_id)
    stats = contract_value_stats(
        client,
        template_ref,
        folder_id,
        value_field,
        "2020-01-01T00:00:00Z",
        "2030-01-01T00:00:00Z",
    )
    groups = top_contract_types(
        client, template_ref, folder_id, type_field, value_field
    )

    print(f"Total contracts: {total}")
    print(
        "Value range: "
        f"avg={stats['avgContractValue']}, "
        f"min={stats['minContractValue']}, "
        f"max={stats['maxContractValue']}"
    )
    # Buckets arrive ordered by document count, so print them as returned.
    print("Top contract types:")
    for row in groups:
        print(f"  {row}")


def main() -> None:
    require_env()
    try:
        print_contract_dashboard(
            template_ref=os.environ["TEMPLATE_REF"],
            type_field=os.environ["FIELD_CONTRACT_TYPE"],
            value_field=os.environ["FIELD_CONTRACT_VALUE"],
        )
    except BoxAPIError as exc:
        status = getattr(exc.response_info, "status_code", "?")
        message = str(getattr(exc.response_info, "message", "") or exc)
        if status == 400 and "Invalid query request" in message:
            print(
                "Box API error (400): Invalid query request.\n"
                "Query Insights group_by requires an enum field. If your "
                "sales.contractType is a string, run python setup_test_data.py "
                "again and copy the printed FIELD_CONTRACT_TYPE (it may be "
                "contractTypeEnum) into .env.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Box API error ({status}): {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
