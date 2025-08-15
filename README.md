# Airtable API Integration

This project provides a FastAPI-based service for managing applicant data in Airtable, including compression, decompression, and shortlisting of applicants based on predefined criteria and finaly using LLM to evaluate.

## Features

- **Data Compression**: Combines data from multiple Airtable tables into a single JSON field
- **Data Decompression**: Extracts compressed JSON and populates child tables
- **Shortlisting**: Evaluates applicants against configurable criteria
- **LLM Evaluation**: Uses OpenAI to analyze and score applicant profiles
- **RESTful API**: FastAPI endpoints for all operations

## Prerequisites

- Python 3.10+
- Poetry for dependency management
- Airtable account with API access
- OpenAI API key

## Setup

1. Clone the repository

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

3. Create a `.env` file with the following variables:
   ```
   AIRTABLE_TOKEN=your_airtable_api_token
   OPENAI_API_KEY=your_openai_api_key
   ```

4. Run the API server:
   ```
   poetry run uvicorn app:app --reload
   ```

## Project Structure

```
├── app.py                  # FastAPI application
├── dictionaries/
│   └── constants.py        # Airtable field mappings and configuration
├── services/
│   ├── compressor.py       # JSON compression functionality
│   ├── decompression.py    # JSON decompression functionality
│   ├── llm_evaluator.py    # OpenAI integration for applicant evaluation
│   └── shortlist.py        # Applicant shortlisting based on criteria
└── tests/
    ├── test_app.py         # API endpoint tests
    └── test_llm_evaluator.py # Tests for LLM evaluation
```

## API Endpoints

### Compression

- `POST /run_compressor` - Compress data for a single applicant
  - Body: `{"app_id": "APP-000123", "rec": "recA1B2C3D4E5"}`

- `GET /run_compressor` - Compress data for a single applicant
  - Query parameters: `app_id`, `rec`

- `GET /run_compressor_all` - Compress data for all applicants

### Decompression

- `POST /run_decompressor` - Decompress data for a single applicant
  - Body: `{"app_id": "APP-000123", "rec": "recA1B2C3D4E5"}`

- `GET /run_decompressor` - Decompress data for a single applicant
  - Query parameters: `app_id`, `rec`

- `POST /run_decompressor_all` - Decompress data for all applicants

### Shortlisting

- `GET /run_shortlist` - Shortlist a single applicant
  - Query parameters: `app_id`, `rec`

- `GET /run_shortlist_all` - Shortlist all applicants

## Data Flow

1. **Compression Flow**:
   - Retrieves data from Personal Details, Work Experience, and Salary Preferences tables
   - Combines data into a single JSON structure
   - Stores the compressed JSON in the Applicants table

2. **Decompression Flow**:
   - Reads compressed JSON from Applicants table
   - Populates/updates records in child tables (Personal Details, Work Experience, Salary Preferences)

3. **Shortlisting Flow**:
   - Evaluates applicants against criteria defined in `SHORTLIST_RULES`
   - Creates records in the Shortlisted Leads table for matching candidates
   - Updates shortlist status in the Applicants table

4. **LLM Evaluation Flow**:
   - Processes applicant data using OpenAI
   - Generates summary, score, issues, and follow-up questions
   - Updates relevant fields in the Applicants and Shortlisted Leads tables

## Shortlisting Criteria

Applicants are shortlisted based on the following criteria:

1. **Experience**: 
   - ≥4 years total experience OR
   - Worked at a Tier-1 company (Google, Meta, OpenAI, Microsoft, Amazon, Apple, Netflix)

2. **Compensation**:
   - Preferred rate ≤$100/hr AND
   - Availability ≥20 hrs/week

3. **Location**:
   - Country in allowed list (US, Canada, UK, Germany, India)

These criteria are configurable in `dictionaries/constants.py`.

## Development

### Running Tests

```
poetry run pytest
```

### Modifying Airtable Field Mappings

Airtable field mappings are stored in `dictionaries/constants.py`. If your Airtable schema changes, update the field IDs in this file.