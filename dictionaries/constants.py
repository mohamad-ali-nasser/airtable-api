FIELD_NAMES_TO_IDS = {
    "Work Experience": {
        "Work Experience ID": "fldz3fW9p8njCs7zj",
        "Company": "fldkTYhz6tDod6zeX",
        "Title": "fldQmVBZl4ZOz7nRc",
        "Start": "fld0S2WeNmYa2XXhM",
        "End": "fldXSlyVJtbaAmi4V",
        "Technologies": "fldGQYpn5effVBLHo",
        "Current Job?": "fldlGsXnCITkLYfCt",
        "Applicant ID": "fldjAiwBB2zuvWQKI",
    },
    "Applicants": {
        "Compressed JSON": "fldDyJ6jT54YE99bs",
        "Shortlist Status": "fldrIxLofvTyqLcfX",
        "LLM Summary": "fld8vUBWqkmQZV1f6",
        "LLM Score": "fldLux2quyDtYgCId",
        "LLM Follow-Ups": "fldJ2m1lnk2XGjFeF",
        "Personal Details Form URL": "fldov0FkUF0ulwcma",
        "Work Experience Form URL": "fldnmg6ZHhCLOAsSp",
        "Salary Preferences Form URL": "fldQI9MnOD7LmmWmC",
        "Forms Completed?": "fldR2m2TQZVIxi6sP",
        "PersonalFilled": "fldZI8czfHaK6IWgX",
        "WorkFilled": "fldQoZUUVetcRAJxt",
        "SalaryFilled": "flddBLoguuqTRAg3l",
        "AI assist": "fldG6XK4RULiHwmH5",
        "record_id": "fld0UCrgQUqlYNHmA",
    },
    "Salary Preferences": {
        "Preferred Rate": "fld78iIAtgk9OqQ6B",
        "Minimum Rate": "fldN7kEdbRAmaVfUh",
        "Currency": "fldmt0c55Sd9KQsDE",
        "Availability (hrs/wk)": "fldZK6OMMWkAR6MMC",
        "Applicant ID": "fldiaw7BpD6Yt5kWn",
    },
    "Personal Details": {
        "Full Name": "fldQAuEiw05IwfJbb",
        "Email Address": "fldLFg3MWjAxoNXxp",
        "Location": "fldbwGfpaxC5KbyFJ",
        "LinkedIn Profile": "fldkqoBOtlo26cglB",
        "email_clean": "fldUw3GodLz6kNdQu",
        "Created": "fldgyTaWrdXN0l4gY",
        "auto_number (personal_details)": "fld0ZBeASiQSJOu9h",
        "Applicant ID": "fldy0CgoqUy0zShMY",
    },
}

FIELD_MAP = {
    "Personal Details": {
        "json_section": "personal",
        "id_field": "fldy0CgoqUy0zShMY",  # Applicant ID column ID
        "columns": {
            "name": "fldQAuEiw05IwfJbb",
            "email": "fldLFg3MWjAxoNXxp",
            "location": "fldbwGfpaxC5KbyFJ",
            "linkedin": "fldkqoBOtlo26cglB",
        },
    },
    "Salary Preferences": {
        "json_section": "salary",
        "id_field": "fldiaw7BpD6Yt5kWn",
        "columns": {
            "preferred_rate": "fld78iIAtgk9OqQ6B",
            "min_rate": "fldN7kEdbRAmaVfUh",
            "currency": "fldmt0c55Sd9KQsDE",
            "availability": "fldZK6OMMWkAR6MMC",
        },
    },
    "Work Experience": {
        "json_section": "experience",
        "id_field": "fldjAiwBB2zuvWQKI",
        "columns": {
            "company": "fldkTYhz6tDod6zeX",
            "title": "fldQmVBZl4ZOz7nRc",
            "start": "fld0S2WeNmYa2XXhM",
            "end": "fldXSlyVJtbaAmi4V",
            "tech": "fldGQYpn5effVBLHo",
        },
        "key_fields": ("company", "title", "start", "end", "tech"),
    },
}
