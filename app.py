import os, json, asyncio
from fastapi import FastAPI, Request, HTTPException, Query
from services.compressor import compress_one, compress_all_applicants
from services.decompression import decompress_one, decompress_all
from services.shortlist import generate_shortlist_one, generate_shortlist

app = FastAPI()
locks: dict[str, asyncio.Lock] = {}  # ← NEW global lock-registry


# ───────── helper: one lock object per applicant ─────────
def _get_lock(app_id: str) -> asyncio.Lock:
    return locks.setdefault(app_id, asyncio.Lock())


@app.post("/run_compressor")
async def run(req: Request):
    body = await req.json()

    try:
        applicant_id = body["app_id"]  # e.g. "APP-000123"
        rec_id = body["rec"]  # e.g. "recA1B2C3D4E5"
    except KeyError:
        raise HTTPException(status_code=400, detail="Missing app_id or rec")

    payload = compress_one(applicant_id=applicant_id, rec_id=rec_id)

    # Run shortlisting on this applicant
    shortlist_result = generate_shortlist_one(applicant_id=applicant_id, rec_id=rec_id)

    return {"status": "ok", "rec": rec_id, "payload": payload, "shortlist_status": shortlist_result["status"]}


@app.get("/run_compressor")
def run_via_get(app_id: str = Query(..., alias="app_id"), rec: str = Query(..., alias="rec")):
    payload = compress_one(applicant_id=app_id, rec_id=rec)

    # Run shortlisting on this applicant
    shortlist_result = generate_shortlist_one(applicant_id=app_id, rec_id=rec)

    return {"status": "ok", "rec": rec, "payload": payload, "shortlist_status": shortlist_result["status"]}


@app.get("/run_compressor_all")
def run_compressor_all():
    # Compress all applicants
    compress_result = compress_all_applicants()

    # Run shortlisting on all applicants
    shortlist_result = generate_shortlist()

    return {"status": "ok", "compression": compress_result, "shortlist_status": shortlist_result["message"]}


@app.post("/run_decompressor")
async def run_decompressor(
    request: Request, app_id: str | None = Query(None, alias="app_id"), rec: str | None = Query(None, alias="rec")
):
    # also accept JSON body
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            app_id = body.get("app_id", app_id)
            rec = body.get("rec", rec)
        except ValueError:
            pass

    if not (app_id and rec):
        raise HTTPException(400, "Need app_id and rec")

    lock = _get_lock(app_id)
    async with lock:  # ← SERIALISE per applicant
        decompress_one(app_id, rec)
    return {"status": "ok", "rec": rec}


all_lock = asyncio.Lock()


@app.get("/run_decompressor")
async def run_decompressor_via_get(app_id: str = Query(..., alias="app_id"), rec: str = Query(..., alias="rec")):
    lock = _get_lock(app_id)
    async with lock:
        decompress_one(app_id, rec)
    return {"status": "ok", "rec": rec}


@app.post("/run_decompressor_all")
async def run_decompressor_all():
    async with all_lock:  # ← only ONE runs at a time
        msg = await asyncio.to_thread(decompress_all)
        # to_thread() runs blocking code without blocking the event loop
    return {"status": "ok", "message": msg}


@app.get("/run_shortlist")
def run_shortlist_single(app_id: str = Query(..., alias="app_id"), rec: str = Query(..., alias="rec")):
    shortlist_result = generate_shortlist_one(applicant_id=app_id, rec_id=rec)
    return {"status": "ok", "shortlist_status": shortlist_result["status"]}


@app.get("/run_shortlist_all")
def run_shortlist_all():
    shortlist_result = generate_shortlist()
    return {"status": "ok", "shortlist_status": shortlist_result["message"]}
