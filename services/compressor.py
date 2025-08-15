from pyairtable import Table
import json, os
from dotenv import load_dotenv
from pyairtable import Api
from dictionaries.constants import (
    FIELD_NAMES_TO_IDS,
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
