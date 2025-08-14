# app.py
import os, json
from fastapi import FastAPI, Request, HTTPException, Query
from compressor import compress_one, compress_all_applicants, decompress_one, decompress_all  # import new function

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


@app.post("/run_compressor_all")
def run_compressor_all():
    result = compress_all_applicants()
    return {"status": "ok", "message": result}


app = FastAPI()


@app.post("/run_decompressor")
async def run_decompressor(
    request: Request, app_id: str | None = Query(None, alias="app_id"), rec: str | None = Query(None, alias="rec")
):
    # try JSON body first
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            app_id = body.get("app_id", app_id)
            rec = body.get("rec", rec)
        except ValueError:
            pass  # ignore if body isn't JSON

    if not (app_id and rec):
        raise HTTPException(400, "Need app_id and rec")

    decompress_one(app_id, rec)
    return {"status": "ok", "rec": rec}


@app.get("/run_decompressor")
def run_decompressor_via_get(app_id: str = Query(..., alias="app_id"), rec: str = Query(..., alias="rec")):
    decompress_one(applicant_id=app_id, rec_id=rec)
    return {"status": "ok", "rec": rec}


@app.post("/run_decompressor_all")
def run_decompressor_all():
    message = decompress_all()
    return {"status": "ok", "message": message}
