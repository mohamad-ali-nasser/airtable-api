#!/bin/bash
echo "Starting Airtable API server..."
poetry run uvicorn app:app --reload --host 0.0.0.0 --port 8000
