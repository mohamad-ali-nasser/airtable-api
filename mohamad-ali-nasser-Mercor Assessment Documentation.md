# Mercor Assessment – Documentation/Implementation Guide

**Author:** Mohamad Ali Nasser  
**Repo:** `mohamad-ali-nasser/airtable-api`  
**Public API (Render):** `https://airtable-api-1w4v.onrender.com/`

> ## Caveats (Airtable Free tier / trial), Hosting and feautres
> - **Airtable scripting disabled on Free trial** → automation logic lives in a **FastAPI** service; per-record actions are triggered from Airtable via **Field Agent** buttons that call the API (compress / shortlist / evaluate, or decompress).
> - **Single-record (per-cell) calls**: Field Agent invokes one API call per button press.
> - **Duplicate-run protection:** a lightweight **async lock** ensures only one call with the same parameters is processed at a time (prevents concurrent double-clicks).
> - **No native multi-step prefilled forms** on Free → applicants re-enter **Applicant ID** in each form. otherwise send email or redirect with prefilled link.
> - **USD assumption for rates** in shortlisting (for this assessment). Extension: add **FX normalization** before checks.
> - **Tests** assume a dev table; no heavy seeded/mocked datasets throughout.
> - **Hosting (Render, Free plan):** service sleeps after ~15 minutes idle; **cold start ~50s** on the first request.
> - **OpenAI caching:** we rely on OpenAI’s built-in prompt/response caching; practically this reduces cost/latency when requests repeat (observed ~10–15 min when idle, up to ~1 hour when active).

---
> ## What this delivers
> - Airtable base (normalized schema) + FastAPI service for **compression**, **decompression**, **shortlisting**, and **LLM evaluation**.  
> - **Manual per-record triggers** (Field Agent buttons).  
> - **Bulk “run all” endpoints** wired as interface buttons:  
>   - Bulk compressor + shortlist + evaluate: `https://airtable-api-1w4v.onrender.com/run_compressor_all`  
>   - Bulk decompressor: `https://airtable-api-1w4v.onrender.com/run_decompressor_all`

## Operational Run-book

1) Candidate submits three forms with the same **Applicant ID**.  
2) Click **Run Compression** via Field Agent per row, (or call `/run_compressor_all` via button in the Airtable Interface, or by simply calling the API).  
3) **Shortlist** runs. If **Shortlisted** and JSON is **new/changed**, **LLM** runs and writes to **Applicants** + **Shortlisted Leads**.  
4) If a candidate becomes **Not Shortlisted**, any **existing shortlist row is deleted**.  
5) (Optional) **Run Decompression** to mirror JSON into child tables, Applicants, Personal Details, Salary Preferences records are updated, Work Experience records are deleted and created anew.
6) Airtable Automations create new records in Applicants, and track number of submitted forms.

---

## 1) Setup Steps & Field Definitions

### 1.1 Local setup

```bash
# 1) Clone the repo
git clone https://github.com/mohamad-ali-nasser/airtable-api
cd airtable-api

# 2) Install deps (Poetry)
poetry install

# 3) Configure environment
cp .env.example .env  # if present; otherwise create .env with AIRTABLE_TOKEN and OPENAI_API_KEY

# 4) Run the API locally
poetry run uvicorn app:app --reload
```

**`.env` required variables**
```env
AIRTABLE_TOKEN=your_airtable_api_token
OPENAI_API_KEY=your_openai_api_key
```

### 1.2 Project structure (high level)

```
app.py
dictionaries/constants.py          # FIELD_NAMES_TO_IDS, FIELD_MAP, SHORTLIST_RULES
services/
  compressor.py                    # build & write Compressed JSON
  decompression.py                 # upsert child tables from JSON, hard-reset work-experience
  shortlist.py                     # meets_criteria + shortlist CRUD + LLM field writes
  llm_evaluator.py                 # OpenAI call w/ retries & normalization
tests/
  test_app.py
  test_llm_evaluator.py
```

### 1.3 Airtable schema & key fields

**Applicants** (primary): `Applicant ID`, `Compressed JSON`, `Shortlist Status`, `LLM Summary`, `LLM Score`, `LLM Follow-Ups`, `number_forms`, buttons (`Compress To JSON`, `Decompress JSON`). helper fields: `Last Modified Date of Compressed JSON`, `record_id`.  
**Personal Details** (1–1): `Full Name`, `Email`, `Location`, `LinkedIn`.  
**Work Experience** (1–many): `Company`, `Title`, `Start`, `End`, `Technologies`.  
**Salary Preferences** (1–1): `Preferred Rate`, `Minimum Rate`, `Currency`, `Availability (hrs/wk)`.  
**Shortlisted Leads**: `Applicant ID`, `Compressed JSON`, `Score Reason`, timestamps.

> All writes/readbacks use field IDs from `dictionaries/constants.py` (`FIELD_NAMES_TO_IDS`, `FIELD_MAP`) so column renames don’t break the code.

---

## 2) How Each Automation Works (with real code)

There are **two kinds of triggers**.

### 2.1 Per-record triggers (Field Agent buttons)

#### A) Run Compressor → Shortlist → (LLM when needed)

**Compression** builds an applicant JSON snapshot and writes it to **Applicants → Compressed JSON** using **field IDs**:

```python
# services/compressor.py
def compress_one(applicant_id: str, rec_id: str):
    j = build_json(applicant_id)
    tbl_app.update(
        rec_id,
        {FIELD_NAMES_TO_IDS["Applicants"]["Compressed JSON"]: json.dumps(j, ensure_ascii=False)}
    )
    return json.dumps(j, ensure_ascii=False)
```

**Shortlisting** evaluates hard rules, then:
- **If shortlisted**  
  - **Existing row & JSON changed** → **update** Shortlisted Leads’ `Compressed JSON`, then run LLM and **write LLM fields** (see §3).
  - **No existing row** → **create** Shortlisted Leads row, then run LLM and **write LLM fields**.
- **If NOT shortlisted**  
  - Update **Applicants → Shortlist Status = "Not Shortlisted"**, and **if a shortlist row exists, delete it** (i.e., *newly not-shortlisted candidates are removed from the shortlist table*).

```python
# services/shortlist.py (core flow)
if meets_criteria(data):
    _update_applicant_status(applicant_id, "Shortlisted")
    if existing:
        if current_cjson != compressed_json:
            tbl_shortlist.update(existing["id"], {SL["Compressed JSON"]: compressed_json}, typecast=True)
            llm_info = _apply_llm_outputs_to_records(app_rec, existing["id"], data)
            return {"status": "Shortlisted", "message": ...}
        else:
            return {"status": "Shortlisted", "message": ...}
    else:
        created = tbl_shortlist.create({SL["Applicant ID"]: applicant_id, SL["Compressed JSON"]: compressed_json}, typecast=True)
        llm_info = _apply_llm_outputs_to_records(app_rec, created["id"], data)
        return {"status": "Shortlisted", "message": ...}
else:
    _update_applicant_status(applicant_id, "Not Shortlisted")
    if existing:
        tbl_shortlist.delete(existing["id"])  # ← delete newly not-shortlisted
    return {"status": "Not Shortlisted", "message": ...}
```

> **LLM field writes** happen inside `_apply_llm_outputs_to_records(...)` and are detailed in §3.

#### B) Run Decompressor (reflect JSON back into the child tables)

- Reads **Applicants → Compressed JSON**, then:
  - **Upserts** 1–1 tables (**Personal**, **Salary**) using field IDs from `FIELD_MAP`
  - **Hard-resets** Work Experience (delete all then recreate from JSON) to keep a 1–many table perfectly in sync.

```python
# services/decompression.py (excerpts)
_upsert_single(tbl=tbl_pers, table_key="Personal Details", applicant_id=applicant_id, fields=data.get("personal", {}))
_upsert_single(tbl=tbl_sal,  table_key="Salary Preferences", applicant_id=applicant_id, fields=data.get("salary", {}))
_sync_work_experience(tbl=tbl_work, applicant_id=applicant_id, experiences=data.get("experience", []))
```

### 2.2 Bulk operations (buttons → API)

- **Compression & Shortlist (all):** `GET /run_compressor_all`  
- **Decompression (all):** `POST /run_decompressor_all`  
- **Shortlist only (all):** `GET /run_shortlist_all`

---

## 3) LLM Integration - Configuration, Security & **Field Updates**

**Trigger timing**  
- Only when a shortlist row is **created** or the applicant’s `Compressed JSON` is **changed**. This keeps costs low and makes results cache-friendly.

**Writes to Airtable**  
`_apply_llm_outputs_to_records(...)` populates:
- **Applicants**: `LLM Summary`, `LLM Score`, `LLM Follow-Ups`
- **Shortlisted Leads**: `Score Reason` (from the LLM “issues” string)

```python
# services/shortlist.py (LLM field writes)
AP = FIELD_NAMES_TO_IDS["Applicants"]
SL = FIELD_NAMES_TO_IDS["Shortlisted Leads"]

tbl_app.update(app_rec["id"], {
    AP["LLM Summary"]:   llm.get("summary", ""),
    AP["LLM Score"]:     llm.get("score", 0),
    AP["LLM Follow-Ups"]: llm.get("follow_ups", ""),
}, typecast=True)

tbl_shortlist.update(shortlist_rec_id, {SL["Score Reason"]: llm.get("issues", "None")}, typecast=True)
```

**Model & reliability**  
- Model: **chatgpt-5-nano** (speed/cost)  
- Reliability: **3× retries** with **exponential backoff** around the OpenAI call; minimal JSON normalization/guardrails.  
- Caching: relies on OpenAI’s built-in caching; repeated requests with identical inputs are typically served faster/cheaper.

**Security**  
- `OPENAI_API_KEY` and `AIRTABLE_TOKEN` loaded from `.env` (server-side only) and added to Render Environment.  
- All Airtable columns referenced via **field IDs** in `dictionaries/constants.py`.

---

## 4) Shortlist Criteria - How to Extend/Customize

- **Rules live in** `SHORTLIST_RULES` (experience / rate & availability / allowed countries) in `dictionaries/constants.py`.
- **Application logic** lives in `meets_criteria(...)` (and helpers like `calculate_experience_years(...)`, `worked_at_tier1(...)`) in `services/shortlist.py`.

Common extensions:
- Add **FX normalization** before rate checks.
- Add **timezone** / **tech stack** filters.
- Tune thresholds (e.g., min years, rate cap, availability).

---


## 5) Testing & Handoff

- Tests in `tests/` validate routes and the LLM response contract.  
- On base duplication/move: reconnect credentials, enable automations, then smoke-test: compress one → shortlist one → confirm **LLM fields** and shortlist row behavior (create/update/delete).

---

## 6) Links

- **GitHub:** `mohamad-ali-nasser/airtable-api`  
- **Render API:** `https://airtable-api-1w4v.onrender.com/`  
- **Airtable invite:** (add your link)

---

## Appendix - API Endpoint Cheat-Sheet (incl. GET with parameters)

**Compression (single):**  
- `POST /run_compressor` (body: `{"app_id":"APP-...","rec":"rec..."}`)  
- `GET /run_compressor?app_id=APP-...&rec=rec...`  
*(Both call `compress_one(...)` then `generate_shortlist_one(...)`.)*

**Compression (all):**  
- `GET /run_compressor_all`

**Decompression (single):**  
- `POST /run_decompressor` (supports body or query params)  
- `GET /run_decompressor?app_id=APP-...&rec=rec...`  
*(Both call `decompress_one(...)`.)*

**Decompression (all):**  
- `POST /run_decompressor_all` (serialized via a global lock)

**Shortlist (single):**  
- `GET /run_shortlist?app_id=APP-...&rec=rec...` → `generate_shortlist_one(...)`

**Shortlist (all):**  
- `GET /run_shortlist_all` → `generate_shortlist(...)`
