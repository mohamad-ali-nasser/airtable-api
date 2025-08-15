from pyairtable import Api
import json
import os
from dotenv import load_dotenv
from dictionaries.constants import (
    FIELD_MAP,
    BASE_ID,
    TABLE_APPLICANTS_ID,
    TABLE_PERSONAL_ID,
    TABLE_WORK_ID,
    TABLE_SALARY_ID,
)

load_dotenv()
API = os.getenv("AIRTABLE_TOKEN")

api = Api(API)
tbl_app = api.table(BASE_ID, TABLE_APPLICANTS_ID)
tbl_pers = api.table(BASE_ID, TABLE_PERSONAL_ID)
tbl_work = api.table(BASE_ID, TABLE_WORK_ID)
tbl_sal = api.table(BASE_ID, TABLE_SALARY_ID)


def decompress_one(applicant_id: str, rec_id: str, dry_run: bool = False) -> dict:
    """
    Read the Compressed JSON on the given Applicant row,
    upsert child-table rows so they exactly match the JSON,
    return the parsed JSON object for logging.
    """
    try:
        # 1. Read compressed JSON from Applicants table
        app_record = tbl_app.get(rec_id)
        compressed_json_str = app_record["fields"].get("Compressed JSON", "{}")
        data = json.loads(compressed_json_str)
    except Exception as e:
        raise RuntimeError(f"Failed to read compressed JSON for Applicant {applicant_id}: {e}")

    # 2. Upsert Personal Details
    _upsert_single(
        tbl=tbl_pers,
        table_key="Personal Details",
        applicant_id=applicant_id,
        fields=data.get("personal", {}),
        dry_run=dry_run,
    )

    # 3. Upsert Salary Preferences
    _upsert_single(
        tbl=tbl_sal,
        table_key="Salary Preferences",
        applicant_id=applicant_id,
        fields=data.get("salary", {}),
        dry_run=dry_run,
    )

    # 4. Sync Work Experience (many rows)
    _sync_work_experience(
        tbl=tbl_work,
        applicant_id=applicant_id,
        experiences=data.get("experience", []),
        dry_run=dry_run,
    )


def _is_blank(v) -> bool:
    """True for None, '', whitespace-only, empty list/dict; numbers are NOT blank."""
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, tuple, set)):
        # empty or all-blank elements
        return len(v) == 0 or all(_is_blank(x) for x in v)
    if isinstance(v, dict):
        return len(v) == 0 or all(_is_blank(x) for x in v.values())
    return False  # numbers, booleans, etc. count as non-blank


def _upsert_single(tbl, table_key, applicant_id, fields, dry_run=False):
    # Find row by Applicant ID
    try:
        field_map = FIELD_MAP[table_key]
        id_field = field_map["id_field"]  # formula column → READ-only
        col_ids = field_map["columns"]

        # ---------- build payload (skip the formula column) ----------
        upsert_fields = {}
        for jk, fid in col_ids.items():
            upsert_fields[fid] = fields.get(jk, "")

        # ---------- find existing row(s) ----------
        records = tbl.all(formula=f"{{{id_field}}}='{applicant_id}'")

        if records:
            if not dry_run:
                tbl.update(records[0]["id"], upsert_fields, typecast=True)
        else:
            all_empty = all(_is_blank(fields.get(jk, "")) for jk in col_ids.keys())
            if all_empty:
                return {"skipped": True, "reason": "all_values_empty"}
            create_payload = {id_field: applicant_id, **upsert_fields}
            if not dry_run:
                tbl.create(create_payload, typecast=True)
    except Exception as e:
        raise RuntimeError(f"Upsert failed for {table_key} ({applicant_id}): {e}")


def _sync_work_experience(tbl, applicant_id, experiences, dry_run=False):
    try:

        """
        Hard-reset strategy:
        1. Delete all Work-Experience rows for this applicant.
        2. Re-create rows from `experiences`, each with Applicant ID set.
        """
        cfg = FIELD_MAP["Work Experience"]
        id_field = cfg["id_field"]  # plain-text Applicant ID column
        col_ids = cfg["columns"]  # JSON key → field-ID map

        # ---------- 1. Delete all existing rows ----------
        formula = f"{{{id_field}}}='{applicant_id}'"
        current = tbl.all(formula=formula)

        # ---------- 2. Create fresh rows ----------
        for exp in experiences:
            payload = {id_field: applicant_id}  # attach applicant
            for json_key, field_id in col_ids.items():
                payload[field_id] = exp.get(json_key, "")
            if not dry_run:
                tbl.create(payload, typecast=True)

        if not dry_run:
            for row in current:
                tbl.delete(row["id"])

    except Exception as e:
        raise RuntimeError(f"Sync failed for Work Experience ({applicant_id}): {e}")


def decompress_all():
    """
    Loop over all records in the Applicants table and apply decompress_one
    to each record using its Applicant ID and record ID.
    """
    records = tbl_app.all()
    for rec in records:
        rec_id = rec.get("id")
        applicant_id = rec.get("fields", {}).get("Applicant ID")
        if rec_id and applicant_id:
            decompress_one(applicant_id, rec_id)
    return f"Decompressed {len(records)} applicants."
