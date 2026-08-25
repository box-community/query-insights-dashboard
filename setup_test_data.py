#!/usr/bin/env python3
"""Create a sales metadata template, folder, and tagged sample contracts."""

from __future__ import annotations

import io
import os
import sys

from box_sdk_gen import (
    BoxAPIError,
    BoxClient,
    CreateFolderParent,
    UploadFileAttributes,
    UploadFileAttributesParentField,
)
from box_sdk_gen.managers.file_metadata import CreateFileMetadataByIdScope
from box_sdk_gen.managers.metadata_templates import (
    CreateMetadataTemplateFields,
    CreateMetadataTemplateFieldsTypeField,
)
from dotenv import load_dotenv

from insights_client import get_box_client

load_dotenv()

TEMPLATE_KEY = "sales"
FOLDER_NAME = "Sales Contracts"
SAMPLE_CONTRACTS = [
    {"name": "Contract 1", "contractType": "Sales", "contractValue": 100000},
    {"name": "Contract 2", "contractType": "Sales", "contractValue": 200000},
    {"name": "Contract 3", "contractType": "Renewal", "contractValue": 150000},
    {"name": "Contract 4", "contractType": "Renewal", "contractValue": 45000},
]

REQUIRED_ENV = (
    "BOX_CLIENT_ID",
    "BOX_CLIENT_SECRET",
    "BOX_ENTERPRISE_ID",
)


def require_env() -> None:
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        names = ", ".join(missing)
        print(
            f"Missing required environment variables: {names}\n"
            "Copy .env.example to .env and fill in BOX_CLIENT_ID, "
            "BOX_CLIENT_SECRET, and BOX_ENTERPRISE_ID from the Developer Console.",
            file=sys.stderr,
        )
        sys.exit(1)


def ensure_template(client: BoxClient) -> None:
    try:
        client.metadata_templates.create_metadata_template(
            scope="enterprise",
            display_name="Sales Contracts",
            template_key=TEMPLATE_KEY,
            fields=[
                CreateMetadataTemplateFields(
                    type=CreateMetadataTemplateFieldsTypeField.STRING,
                    key="contractType",
                    display_name="Contract type",
                ),
                CreateMetadataTemplateFields(
                    type=CreateMetadataTemplateFieldsTypeField.FLOAT,
                    key="contractValue",
                    display_name="Contract value",
                ),
            ],
        )
        print(f"Created metadata template '{TEMPLATE_KEY}'.")
    except Exception:
        print(f"Metadata template '{TEMPLATE_KEY}' already exists; reusing it.")


def ensure_folder(client: BoxClient) -> str:
    for item in client.folders.get_folder_items("0").entries:
        if item.type == "folder" and item.name == FOLDER_NAME:
            print(f"Reusing folder '{FOLDER_NAME}' (id={item.id}).")
            return item.id
    folder = client.folders.create_folder(
        name=FOLDER_NAME, parent=CreateFolderParent(id="0")
    )
    print(f"Created folder '{FOLDER_NAME}' (id={folder.id}).")
    return folder.id


def existing_file_names(client: BoxClient, folder_id: str) -> set[str]:
    names: set[str] = set()
    offset = 0
    limit = 1000
    while True:
        items = client.folders.get_folder_items(
            folder_id, limit=limit, offset=offset
        )
        entries = items.entries or []
        for item in entries:
            if item.type == "file":
                names.add(item.name)
        if len(entries) < limit:
            break
        offset += limit
    return names


def upload_contracts(client: BoxClient, folder_id: str) -> None:
    existing = existing_file_names(client, folder_id)
    for contract in SAMPLE_CONTRACTS:
        filename = f"{contract['name']}.txt"
        if filename in existing:
            print(f"Skipping {filename}; already in the folder.")
            continue
        uploaded = client.uploads.upload_file(
            attributes=UploadFileAttributes(
                name=filename,
                parent=UploadFileAttributesParentField(id=folder_id),
            ),
            file=io.BytesIO(b"Sample contract for query insights."),
        )
        client.file_metadata.create_file_metadata_by_id(
            uploaded.entries[0].id,
            CreateFileMetadataByIdScope.ENTERPRISE,
            TEMPLATE_KEY,
            {
                "contractType": contract["contractType"],
                "contractValue": contract["contractValue"],
            },
        )
        print(f"Uploaded and tagged {filename}.")


if __name__ == "__main__":
    require_env()
    try:
        client = get_box_client()
        me = client.users.get_user_me()
        print(
            "Authenticated as service account "
            f"{me.name} ({me.login}). Sample files are stored in this "
            "account's root, not your personal Box user."
        )

        enterprise_id = os.environ["BOX_ENTERPRISE_ID"]
        ensure_template(client)
        folder_id = ensure_folder(client)
        upload_contracts(client, folder_id)

        template_ref = f"enterprise_{enterprise_id}:{TEMPLATE_KEY}"
        print()
        print("Add these values to your .env file:")
        print(f"FOLDER_ID={folder_id}")
        print(f"TEMPLATE_KEY={TEMPLATE_KEY}")
        print(f"TEMPLATE_REF={template_ref}")
        print(f"FIELD_CONTRACT_TYPE={template_ref}:contractType")
        print(f"FIELD_CONTRACT_VALUE={template_ref}:contractValue")
        print()
        print(
            "If query insights returns 0 right away, wait about a minute "
            "for the metadata index to update, then run: python app.py"
        )
    except BoxAPIError as exc:
        status = getattr(exc.response_info, "status_code", "?")
        print(f"Box API error ({status}): {exc}", file=sys.stderr)
        sys.exit(1)
