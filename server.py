from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
import shutil
import os
import uuid
import time
from datetime import datetime

from cf_checker import check_codeforces_status
from lc_checker import check_leetcode_status
from cc_checker import check_codechef_status

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL JOB STORAGE ---
jobs = {}

def simplify_status(detailed_status):
    return "Solved" if detailed_status == "Solved" else "Not Solved"

# --- THE WORKER TASK ---
def process_file_task(job_id: str, filepath: str, cf_problems, lc_problems, cc_problems):
    try:
        # 1. Read File
        if filepath.endswith('.csv'):
             df = pd.read_csv(filepath)
        else:
             df = pd.read_excel(filepath, engine='openpyxl')
        
        df = df.astype(str)
        df.replace(["nan", "NaN"], "", inplace=True)
        
        cols = {c.upper(): c for c in df.columns}
        cf_col = cols.get('CODEFORCES')
        lc_col = cols.get('LEETCODE')
        cc_col = cols.get('CODECHEF')

        total_students = len(df)
        jobs[job_id]["total"] = total_students
        jobs[job_id]["status"] = "processing"

        # Initialize Score
        df['Score'] = 0

        # 2. Loop Through Students
        for index, row in df.iterrows():
            jobs[job_id]["current"] = index + 1

            time.sleep(2)
            current_score = 0
            
            # CF
            if cf_col:
                uid = row[cf_col].strip()
                if uid:
                    for prob in cf_problems:
                        if not prob: continue 
                        status = simplify_status(check_codeforces_status(uid, prob))
                        df.at[index, f'CF: {prob}'] = status
                        if status == "Solved": current_score += 1
                else:
                    for prob in cf_problems: 
                        if prob: df.at[index, f'CF: {prob}'] = "No ID"

            # LC
            if lc_col:
                uid = row[lc_col].strip()
                if uid:
                    for prob in lc_problems:
                        if not prob: continue
                        status = simplify_status(check_leetcode_status(uid, prob))
                        df.at[index, f'LC: {prob}'] = status
                        if status == "Solved": current_score += 1
                else:
                    for prob in lc_problems:
                        if prob: df.at[index, f'LC: {prob}'] = "No ID"

            # CC
            if cc_col:
                uid = row[cc_col].strip()
                if uid:
                    for prob in cc_problems:
                        if not prob: continue
                        status = simplify_status(check_codechef_status(uid, prob))
                        df.at[index, f'CC: {prob}'] = status
                        if status == "Solved": current_score += 1
                else:
                    for prob in cc_problems:
                        if prob: df.at[index, f'CC: {prob}'] = "No ID"

            df.at[index, 'Score'] = current_score

        # 3. Cleanup & Save
        columns_to_remove = [c for c in [cf_col, lc_col, cc_col] if c]
        df.drop(columns=columns_to_remove, inplace=True)
        
        cols = list(df.columns)
        cols.remove('Score')
        insert_pos = 2 if len(cols) >= 2 else 1
        cols.insert(insert_pos, 'Score')
        df = df[cols]

        output_filename = f"processed_{job_id}.xlsx"
        df.to_excel(output_filename, index=False)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["filename"] = output_filename
    
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

# --- API ENDPOINTS ---
@app.post("/start-check")
async def start_check(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    cf_problems: List[str] = Form([]),
    lc_problems: List[str] = Form([]),
    cc_problems: List[str] = Form([])
):
    job_id = str(uuid.uuid4())
    temp_filename = f"temp_{job_id}.xlsx"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    jobs[job_id] = {
        "status": "queued",
        "current": 0,
        "total": 0,
        "filename": None
    }
    background_tasks.add_task(process_file_task, job_id, temp_filename, cf_problems, lc_problems, cc_problems)
    return {"job_id": job_id}

@app.get("/progress/{job_id}")
def get_progress(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})

@app.get("/download/{job_id}")
def download_file(job_id: str):
    job = jobs.get(job_id)
    if job and job["status"] == "completed":
        return FileResponse(job["filename"], filename="Student_Report.xlsx")
    return {"error": "File not ready"}

