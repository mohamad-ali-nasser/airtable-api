from pyairtable import Table
import json, os
from dotenv import load_dotenv
from pyairtable import Api
from dictionaries.constants import FIELD_NAMES_TO_IDS, FIELD_MAP

load_dotenv()
API = os.getenv("AIRTABLE_TOKEN")
BASE = os.getenv("BASE_ID")
T_APP_ID = os.getenv("TABLE_APPLICANTS_ID")
T_PERS_ID = os.getenv("TABLE_PERSONAL_ID")
T_WORK_ID = os.getenv("TABLE_WORK_ID")
T_SAL_ID = os.getenv("TABLE_SALARY_ID")

api = Api(API)
tbl_app = api.table(BASE, T_APP_ID)
tbl_pers = api.table(BASE, T_PERS_ID)
tbl_work = api.table(BASE, T_WORK_ID)
tbl_sal = api.table(BASE, T_SAL_ID)


def build_json(applicant_id: str) -> dict:
    # 1. fetch linked Personal Details (should be 1)
    pd = tbl_pers.all(formula=f"{{Applicant ID}}='{applicant_id}'")
    personal = pd[0]["fields"] if pd else {}

    # 2. fetch Work Experience rows (many)
    we = tbl_work.all(formula=f"{{Applicant ID}}='{applicant_id}'")
    work = [r["fields"] for r in we] if we else []

    # 3. fetch Salary Preferences (should be 1)
    sp = tbl_sal.all(formula=f"{{Applicant ID}}='{applicant_id}'")
    salary = sp[0]["fields"] if sp else {}

    # 4. assemble, always include all fields
    return {
        "personal": {
            "name": personal.get("Full Name", ""),
            "email": personal.get("Email Address", ""),
            "location": personal.get("Location", ""),
            "linkedin": personal.get("LinkedIn Profile", ""),
        },
        "experience": [
            {
                "company": w.get("Company", ""),
                "title": w.get("Title", ""),
                "start": w.get("Start", ""),
                "end": w.get("End", ""),
                "tech": w.get("Technologies", ""),
            }
            for w in work
        ],
        "salary": {
            "preferred_rate": salary.get("Preferred Rate", ""),
            "min_rate": salary.get("Minimum Rate", ""),
            "currency": salary.get("Currency", ""),
            "availability": salary.get("Availability (hrs/wk)", ""),
        },
    }


def compress_one(applicant_id: str, rec_id: str):
    j = build_json(applicant_id)
    tbl_app.update(rec_id, {FIELD_NAMES_TO_IDS["Applicants"]["Compressed JSON"]: json.dumps(j, ensure_ascii=False)})
    return json.dumps(j, ensure_ascii=False)


def compress_all_applicants():
    records = tbl_app.all()
    for rec in records:
        rec_id = rec.get("id")
        applicant_id = rec.get("fields", {}).get("Applicant ID")
        if rec_id and applicant_id:
            compress_one(applicant_id, rec_id)
    return f"Compressed {len(records)} applicants."


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
            if not dry_run:
                tbl.create(upsert_fields, typecast=True)
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
