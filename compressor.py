from pyairtable import Table
import json, os
from dotenv import load_dotenv
from pyairtable import Api

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
    work = [r["fields"] for r in we]

    # 3. fetch Salary Preferences (should be 1)
    sp = tbl_sal.all(formula=f"{{Applicant ID}}='{applicant_id}'")
    salary = sp[0]["fields"] if sp else {}

    # 4. assemble
    return {
        "personal": {
            "name": personal.get("Full Name"),
            "email": personal.get("Email Address"),
            "location": personal.get("Location"),
            "linkedin": personal.get("LinkedIn"),
        },
        "experience": [
            {
                "company": w.get("Company"),
                "title": w.get("Title"),
                "start": w.get("Start"),
                "end": w.get("End"),
                "tech": w.get("Technologies"),
            }
            for w in work
        ],
        "salary": {
            "preferred_rate": salary.get("Preferred Rate"),
            "min_rate": salary.get("Minimum Rate"),
            "currency": salary.get("Currency"),
            "availability": salary.get("Availability (hrs/wk)"),
        },
    }


def compress_one(applicant_id: str, rec_id: str):
    j = build_json(applicant_id)
    tbl_app.update(rec_id, {"Compressed JSON": json.dumps(j, ensure_ascii=False)})
