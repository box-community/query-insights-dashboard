#!/usr/bin/env python3
"""Generate four small sample contract PDFs for Box Query Insights testing."""

from __future__ import annotations

from pathlib import Path

# Sample set matches the tutorial: four contracts with type + value metadata.
# Varied contractType values so group_by dashboards have multiple buckets.
SAMPLES = [
    {
        "filename": "sample-contract-1-msa.pdf",
        "title": "Master Service Agreement",
        "contract_type": "MSA",
        "contract_value": 100_000,
        "party": "Acme Corp",
    },
    {
        "filename": "sample-contract-2-nda.pdf",
        "title": "Non-Disclosure Agreement",
        "contract_type": "NDA",
        "contract_value": 45_000,
        "party": "Beta Industries",
    },
    {
        "filename": "sample-contract-3-sow.pdf",
        "title": "Statement of Work",
        "contract_type": "SOW",
        "contract_value": 150_000,
        "party": "Gamma Partners",
    },
    {
        "filename": "sample-contract-4-sales.pdf",
        "title": "Sales Agreement",
        "contract_type": "Sales",
        "contract_value": 200_000,
        "party": "Delta LLC",
    },
]


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(lines: list[str]) -> bytes:
    """Build a minimal one-page PDF 1.4 document (stdlib only)."""
    content_lines = ["BT", "/F1 12 Tf", "50 750 Td", "16 TL"]
    for i, line in enumerate(lines):
        if i == 0:
            content_lines.append(f"({_escape(line)}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({_escape(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("latin-1"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(out)


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    for sample in SAMPLES:
        lines = [
            sample["title"],
            "",
            f"Contract type: {sample['contract_type']}",
            f"Contract value: ${sample['contract_value']:,}",
            f"Counterparty: {sample['party']}",
            "",
            "Sample document for Box Query Insights dashboard testing.",
            "Upload to Box and apply the sales metadata template.",
        ]
        path = out_dir / sample["filename"]
        path.write_bytes(build_pdf(lines))
        print(f"Wrote {path.name}")


if __name__ == "__main__":
    main()
