#!/usr/bin/env python3
"""Create a sales metadata template, folder, and tagged sample contracts."""

from __future__ import annotations

import io
import os
import sys

from box_sdk_gen import (
    BoxAPIError,
    BoxClient,
    CreateFileMetadataByIdScope,
    CreateFolderParent,
    CreateMetadataTemplateFields,
    CreateMetadataTemplateFieldsOptionsField,
    CreateMetadataTemplateFieldsTypeField,
    GetFileMetadataByIdScope,
    GetMetadataTemplateScope,
    UpdateFileMetadataByIdRequestBody,
    UpdateFileMetadataByIdRequestBodyOpField,
    UpdateFileMetadataByIdScope,
    UpdateMetadataTemplateRequestBody,
    UpdateMetadataTemplateRequestBodyOpField,
    UpdateMetadataTemplateScope,
    UploadFileAttributes,
    UploadFileAttributesParentField,
)
from dotenv import load_dotenv

from box_client import get_box_client

load_dotenv()

TEMPLATE_KEY = os.environ.get("TEMPLATE_KEY") or "sales"
ENUM_FIELD_KEY = "contractType"
ENUM_FALLBACK_KEY = "contractTypeEnum"
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


def _field_type(field) -> str:
    return str(getattr(field.type, "value", field.type))


def _template_fields(template) -> dict:
    return {field.key: field for field in (template.fields or [])}


def _enum_field_key(template) -> str | None:
    fields = _template_fields(template)
    preferred = fields.get(ENUM_FIELD_KEY)
    if preferred and _field_type(preferred) == "enum":
        return ENUM_FIELD_KEY
    fallback = fields.get(ENUM_FALLBACK_KEY)
    if fallback and _field_type(fallback) == "enum":
        return ENUM_FALLBACK_KEY
    return None


def _add_enum_field(client: BoxClient, template_key: str) -> None:
    client.metadata_templates.update_metadata_template(
        UpdateMetadataTemplateScope.ENTERPRISE,
        template_key,
        [
            UpdateMetadataTemplateRequestBody(
                op=UpdateMetadataTemplateRequestBodyOpField.ADDFIELD,
                data={
                    "type": "enum",
                    "key": ENUM_FALLBACK_KEY,
                    "displayName": "Contract type",
                    "options": [{"key": "Sales"}, {"key": "Renewal"}],
                },
            )
        ],
    )


def ensure_template(client: BoxClient) -> str:
    try:
        client.metadata_templates.create_metadata_template(
            scope="enterprise",
            display_name="Sales Contracts",
            template_key=TEMPLATE_KEY,
            fields=[
                CreateMetadataTemplateFields(
                    type=CreateMetadataTemplateFieldsTypeField.ENUM,
                    key=ENUM_FIELD_KEY,
                    display_name="Contract type",
                    options=[
                        CreateMetadataTemplateFieldsOptionsField(key="Sales"),
                        CreateMetadataTemplateFieldsOptionsField(key="Renewal"),
                    ],
                ),
                CreateMetadataTemplateFields(
                    type=CreateMetadataTemplateFieldsTypeField.FLOAT,
                    key="contractValue",
                    display_name="Contract value",
                ),
            ],
        )
        print(f"Created metadata template '{TEMPLATE_KEY}'.")
        return ENUM_FIELD_KEY
    except Exception:
        template = client.metadata_templates.get_metadata_template(
            GetMetadataTemplateScope.ENTERPRISE, TEMPLATE_KEY
        )
        type_field = _enum_field_key(template)
        if type_field:
            if type_field != ENUM_FIELD_KEY:
                print(
                    f"Metadata template '{TEMPLATE_KEY}' already exists with "
                    f"string {ENUM_FIELD_KEY}; grouping on enum {type_field}."
                )
            else:
                print(f"Metadata template '{TEMPLATE_KEY}' already exists; reusing it.")
            return type_field
        _add_enum_field(client, TEMPLATE_KEY)
        print(
            f"Metadata template '{TEMPLATE_KEY}' already exists with string "
            f"{ENUM_FIELD_KEY}; added enum field {ENUM_FALLBACK_KEY}."
        )
        return ENUM_FALLBACK_KEY


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


def existing_files(client: BoxClient, folder_id: str) -> dict[str, str]:
    files: dict[str, str] = {}
    offset = 0
    limit = 1000
    while True:
        items = client.folders.get_folder_items(
            folder_id, limit=limit, offset=offset
        )
        entries = items.entries or []
        for item in entries:
            if item.type == "file":
                files[item.name] = item.id
        if len(entries) < limit:
            break
        offset += limit
    return files


def _metadata_payload(contract: dict, type_field: str) -> dict:
    payload = {
        type_field: contract["contractType"],
        "contractValue": contract["contractValue"],
    }
    if type_field != ENUM_FIELD_KEY:
        payload[ENUM_FIELD_KEY] = contract["contractType"]
    return payload


def _current_metadata(client: BoxClient, file_id: str) -> dict:
    current = client.file_metadata.get_file_metadata_by_id(
        file_id, GetFileMetadataByIdScope.ENTERPRISE, TEMPLATE_KEY
    )
    data = current.to_dict()
    extra = data.pop("extra_data", None) or {}
    merged = {**extra, **data}
    return {key: value for key, value in merged.items() if not key.startswith("$")}


def apply_metadata(client: BoxClient, file_id: str, payload: dict) -> None:
    try:
        client.file_metadata.create_file_metadata_by_id(
            file_id,
            CreateFileMetadataByIdScope.ENTERPRISE,
            TEMPLATE_KEY,
            payload,
        )
        return
    except BoxAPIError:
        current = _current_metadata(client, file_id)
        ops = []
        for key, value in payload.items():
            op = (
                UpdateFileMetadataByIdRequestBodyOpField.REPLACE
                if key in current
                else UpdateFileMetadataByIdRequestBodyOpField.ADD
            )
            ops.append(
                UpdateFileMetadataByIdRequestBody(
                    op=op, path=f"/{key}", value=value
                )
            )
        if ops:
            client.file_metadata.update_file_metadata_by_id(
                file_id,
                UpdateFileMetadataByIdScope.ENTERPRISE,
                TEMPLATE_KEY,
                ops,
            )


def upload_contracts(client: BoxClient, folder_id: str, type_field: str) -> None:
    existing = existing_files(client, folder_id)
    for contract in SAMPLE_CONTRACTS:
        filename = f"{contract['name']}.txt"
        payload = _metadata_payload(contract, type_field)
        if filename in existing:
            apply_metadata(client, existing[filename], payload)
            print(f"Updated metadata on {filename}.")
            continue
        uploaded = client.uploads.upload_file(
            attributes=UploadFileAttributes(
                name=filename,
                parent=UploadFileAttributesParentField(id=folder_id),
            ),
            file=io.BytesIO(b"Sample contract for Box Query Insights API."),
        )
        apply_metadata(client, uploaded.entries[0].id, payload)
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
        type_field = ensure_template(client)
        folder_id = ensure_folder(client)
        upload_contracts(client, folder_id, type_field)

        template_ref = f"enterprise_{enterprise_id}:{TEMPLATE_KEY}"
        print()
        print("Add these values to your .env file:")
        print(f"FOLDER_ID={folder_id}")
        print(f"TEMPLATE_KEY={TEMPLATE_KEY}")
        print(f"TEMPLATE_REF={template_ref}")
        print(f"FIELD_CONTRACT_TYPE={template_ref}:{type_field}")
        print(f"FIELD_CONTRACT_VALUE={template_ref}:contractValue")
        print()
        print(
            "If Query Insights returns 0 right away, wait about a minute "
            "for the metadata index to update, then run: python dashboard.py"
        )
    except BoxAPIError as exc:
        status = getattr(exc.response_info, "status_code", "?")
        print(f"Box API error ({status}): {exc}", file=sys.stderr)
        sys.exit(1)
