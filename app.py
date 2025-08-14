# app.py
import os, json
from fastapi import FastAPI, Request, HTTPException, Query
from compressor import compress_one  # your function from earlier

AIRTABLE_API = os.environ["AIRTABLE_TOKEN"]

app = FastAPI()


@app.post("/run_compressor")
async def run(req: Request):
    body = await req.json()

    try:
        applicant_id = body["app_id"]  # e.g. "APP-000123"
        rec_id = body["rec"]  # e.g. "recA1B2C3D4E5"
    except KeyError:
        raise HTTPException(status_code=400, detail="Missing app_id or rec")
    payload = compress_one(applicant_id=applicant_id, rec_id=rec_id)
    return {"status": "ok", "rec": rec_id, "payload": payload}


@app.get("/run_compressor")
def run_via_get(app_id: str = Query(..., alias="app_id"), rec: str = Query(..., alias="rec")):
    payload = compress_one(applicant_id=app_id, rec_id=rec)
    return {"status": "ok", "rec": rec, "payload": payload}
