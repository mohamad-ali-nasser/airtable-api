from pyairtable import Api
import json
import os
from dotenv import load_dotenv
from dictionaries.constants import FIELD_NAMES_TO_IDS, SHORTLIST_RULES, BASE_ID, TABLE_APPLICANTS_ID, TABLE_SHORTLIST_ID
from datetime import datetime
from services.llm_evaluator import llm_evaluate_applicant

load_dotenv()
API = os.getenv("AIRTABLE_TOKEN")

api = Api(API)
tbl_app = api.table(BASE_ID, TABLE_APPLICANTS_ID)
tbl_shortlist = api.table(BASE_ID, TABLE_SHORTLIST_ID)


def calculate_experience_years(experiences):
    """
    Calculate total years of experience from experiences list.

    Args:
        experiences (list): List of dicts with "start" and "end" keys in "YYYY-MM-DD" or "YYYY" format.
        round_method (str): "floor", "ceil", or "round" to control rounding method.

    Returns:
        int or float: Total years of experience (rounded if specified).
    """
    total_days = 0
    today = datetime.today().date()

    for exp in experiences:
        start = exp.get("start", "")
        end = exp.get("end", "") or today.isoformat()  # Current job → today

        try:
            # Parse start date
            start_date = (
                datetime.strptime(start, "%Y-%m-%d").date() if "-" in start else datetime(int(start), 1, 1).date()
            )
            # Parse end date
            end_date = datetime.strptime(end, "%Y-%m-%d").date() if "-" in end else datetime(int(end), 1, 1).date()

            # Ignore negative durations
            if end_date >= start_date:
                total_days += (end_date - start_date).days
        except Exception:
            continue  # Skip invalid formats

    # Convert days to years
    total_years = total_days / 365.25

    return round(total_years, 1)  # Keep one decimal place


def worked_at_tier1(experiences):
    """Check if applicant has worked at any Tier-1 company."""
    tier_1_companies = SHORTLIST_RULES["experience"]["tier_1_companies"]
    for exp in experiences:
        company = exp.get("company", "").strip()
        if company in tier_1_companies:
            return True
    return False


def meets_criteria(data):
    """
    Check if applicant meets all shortlisting criteria.

    1. Experience: ≥4 years OR worked at a Tier-1 company
    2. Compensation: preferred rate ≤$100/hr AND availability ≥20 hrs/week
    3. Location: Country in allowed list
    """
    # Extract relevant data
    experiences = data.get("experience", [])
    personal = data.get("personal", {})
    salary = data.get("salary", {})

    # Get location data and check country
    location = personal.get("location", "")
    location_country = None

    # Common location formats: "City, Country" or just "Country"
    if "," in location:
        parts = location.split(",")
        location_country = parts[-1].strip()
    else:
        location_country = location.strip()

    allowed_countries = SHORTLIST_RULES["location"]["allowed_countries"]
    if not location_country or location_country not in allowed_countries:
        return False

    # Check compensation criteria
    max_rate = SHORTLIST_RULES["salary"]["max_rate"]
    min_availability = SHORTLIST_RULES["salary"]["min_availability"]

    try:
        preferred_rate = float(salary.get("preferred_rate", "0"))
        availability = float(salary.get("availability", "0"))

        if preferred_rate > max_rate or availability < min_availability:
            return False
    except (ValueError, TypeError):
        # Missing or invalid compensation data
        return False

    # Check experience criteria (≥4 years OR worked at Tier-1)
    min_years = SHORTLIST_RULES["experience"]["min_years"]
    experience_years = calculate_experience_years(experiences)
    tier1_experience = worked_at_tier1(experiences)

    if experience_years < min_years and not tier1_experience:
        return False

    # All criteria met
    return True


def _get_shortlist_row_for(app_id: str):
    """Return existing shortlist row (or None) for a given Applicant ID."""
    SL = FIELD_NAMES_TO_IDS["Shortlisted Leads"]
    # formula using field-ID (rename-proof)
    formula = f"{{{SL['Applicant ID']}}}='{app_id}'"
    rows = tbl_shortlist.all(formula=formula, max_records=1)
    return rows[0] if rows else None


def _update_applicant_status(applicant_id: str, status: str):
    """Update the Shortlist Status field in the Applicants table."""
    AP = FIELD_NAMES_TO_IDS["Applicants"]
    formula = f"{{{AP['Applicant ID']}}}='{applicant_id}'"
    rows = tbl_app.all(formula=formula, max_records=1)
    if rows:
        tbl_app.update(rows[0]["id"], {AP["Shortlist Status"]: status}, typecast=True)


def _apply_llm_outputs_to_records(app_rec: dict, shortlist_rec_id: str, applicant_json: dict):
    """
    Run LLM and write results:
      Applicants: LLM Summary, LLM Score, LLM Follow-Ups
      Shortlisted Leads: Score Reason (from issues)
    """
    AP = FIELD_NAMES_TO_IDS["Applicants"]
    SL = FIELD_NAMES_TO_IDS["Shortlisted Leads"]

    try:
        llm = llm_evaluate_applicant(applicant_json)
    except Exception as e:
        # Don't block shortlist writes if LLM fails
        return {"llm_status": "error", "llm_message": f"LLM error: {e}"}

    # Update Applicants row
    app_update = {
        AP["LLM Summary"]: llm.get("summary", ""),
        AP["LLM Score"]: llm.get("score", 0),
        AP["LLM Follow-Ups"]: llm.get("follow_ups", ""),
    }
    try:
        tbl_app.update(app_rec["id"], app_update, typecast=True)
    except Exception as e:
        return {"llm_status": "partial", "llm_message": f"Applicants update failed: {e}"}

    # Update Shortlisted Leads row (Score Reason from issues)
    try:
        tbl_shortlist.update(shortlist_rec_id, {SL["Score Reason"]: llm.get("issues", "None")}, typecast=True)
    except Exception as e:
        return {"llm_status": "partial", "llm_message": f"Shortlist update failed: {e}"}

    return {"llm_status": "ok"}


def generate_shortlist_one(applicant_id: str, rec_id: str | None = None, compressed_json: str | None = None) -> dict:
    if not applicant_id or not str(applicant_id).strip():
        return {"status": "error", "message": "applicant_id is required"}

    if not compressed_json:
        if not rec_id:
            return {"status": "error", "message": "Either rec_id or compressed_json must be provided"}
        try:
            app_rec = tbl_app.get(rec_id)
            compressed_json = app_rec.get("fields", {}).get("Compressed JSON")
            if not compressed_json:
                return {"status": "error", "message": f"No Compressed JSON for applicant {applicant_id}"}
        except Exception as e:
            return {"status": "error", "message": f"Error fetching Applicants record: {e}"}
    else:
        # If compressed_json was passed, we still need the app_rec
        try:
            app_rec = tbl_app.get(rec_id) if rec_id else None
            if app_rec is None:
                # find by Applicant ID
                AP = FIELD_NAMES_TO_IDS["Applicants"]
                formula = f"{{{AP['Applicant ID']}}}='{applicant_id}'"
                rows = tbl_app.all(formula=formula, max_records=1)
                if not rows:
                    return {"status": "error", "message": f"Applicant {applicant_id} not found"}
                app_rec = rows[0]
        except Exception as e:
            return {"status": "error", "message": f"Error fetching Applicants record: {e}"}

    try:
        data = json.loads(compressed_json)
    except (TypeError, json.JSONDecodeError) as e:
        return {"status": "error", "message": f"Invalid Compressed JSON for {applicant_id}: {e}"}

    SL = FIELD_NAMES_TO_IDS["Shortlisted Leads"]
    existing = _get_shortlist_row_for(applicant_id)

    if meets_criteria(data):
        _update_applicant_status(applicant_id, "Shortlisted")
        if existing:
            current_cjson = existing.get("fields", {}).get(SL["Compressed JSON"])
            if current_cjson != compressed_json:
                tbl_shortlist.update(existing["id"], {SL["Compressed JSON"]: compressed_json}, typecast=True)
                # LLM on update
                llm_info = _apply_llm_outputs_to_records(app_rec, existing["id"], data)
                return {"status": "Shortlisted", "message": f"Shortlist updated for {applicant_id}"}
            else:
                return {"status": "Shortlisted", "message": f"Shortlist already up-to-date for {applicant_id}"}
        else:
            created = tbl_shortlist.create(
                {SL["Applicant ID"]: applicant_id, SL["Compressed JSON"]: compressed_json},
                typecast=True,
            )
            # LLM on create
            llm_info = _apply_llm_outputs_to_records(app_rec, created["id"], data)
            return {"status": "Shortlisted", "message": f"Shortlist created for {applicant_id}"}
    else:
        _update_applicant_status(applicant_id, "Not Shortlisted")
        if existing:
            tbl_shortlist.delete(existing["id"])
            return {"status": "Not Shortlisted", "message": f"Shortlist removed for {applicant_id}"}
        else:
            return {"status": "Not Shortlisted", "message": f"Not shortlisted; no existing record for {applicant_id}"}


def generate_shortlist():
    SL = FIELD_NAMES_TO_IDS["Shortlisted Leads"]
    created = updated = deleted = skipped = 0
    llm_ok = llm_errors = 0

    for app_rec in tbl_app.all():
        fields = app_rec.get("fields", {})
        app_id = fields.get("Applicant ID")
        cjson = fields.get("Compressed JSON")

        if not app_id or not str(app_id).strip() or not cjson:
            skipped += 1
            continue

        try:
            data = json.loads(cjson)
        except (TypeError, json.JSONDecodeError):
            skipped += 1
            continue

        existing = _get_shortlist_row_for(app_id)

        if meets_criteria(data):
            _update_applicant_status(app_id, "Shortlisted")
            if existing:
                if existing.get("fields", {}).get(SL["Compressed JSON"]) != cjson:
                    tbl_shortlist.update(existing["id"], {SL["Compressed JSON"]: cjson}, typecast=True)
                    updated += 1
                    # LLM on update
                    llm_info = _apply_llm_outputs_to_records(app_rec, existing["id"], data)
                    llm_ok += 1 if llm_info.get("llm_status") == "ok" else 0
                    llm_errors += 1 if llm_info.get("llm_status") != "ok" else 0
                else:
                    skipped += 1
            else:
                created_row = tbl_shortlist.create(
                    {SL["Applicant ID"]: app_id, SL["Compressed JSON"]: cjson}, typecast=True
                )
                created += 1
                # LLM on create
                llm_info = _apply_llm_outputs_to_records(app_rec, created_row["id"], data)
                llm_ok += 1 if llm_info.get("llm_status") == "ok" else 0
                llm_errors += 1 if llm_info.get("llm_status") != "ok" else 0
        else:
            _update_applicant_status(app_id, "Not Shortlisted")
            if existing:
                tbl_shortlist.delete(existing["id"])
                deleted += 1
            else:
                skipped += 1

    return {
        "status": "ok",
        "message": {
            "created": created,
            "updated": updated,
            "deleted": deleted,
            "skipped": skipped,
            "llm_ok": llm_ok,
            "llm_errors": llm_errors,
        },
    }
