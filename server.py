from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
import shutil
import os
import uuid
import time
import random
from datetime import datetime, timezone
import pymongo
from bson import ObjectId
from urllib.parse import quote_plus
from dotenv import load_dotenv 

# --- LOAD SECRETS ---
load_dotenv()  

# --- IMPORTS ---
from cf_checker import check_codeforces_status
from lc_checker import check_leetcode_status
from cc_checker import check_codechef_status

app = FastAPI()

# --- FIX CORS ERROR (Trust Vercel & Render) ---
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE CONNECTION (SECURE) ---
username = os.getenv("MONGO_USER")
password = os.getenv("MONGO_PASSWORD")
cluster_address = os.getenv("MONGO_CLUSTER")

client = None
db = None
reports_collection = None

if not username or not password:
    print("⚠️ WARNING: MongoDB credentials not found! Check your .env file or Render settings.")
else:
    try:
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)
        MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@{cluster_address}/?appName=Cluster0"
        
        client = pymongo.MongoClient(MONGO_URI)
        db = client["student_report_db"]
        reports_collection = db["reports"]
        print("✅ Connected to MongoDB successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")

# --- GLOBAL JOB STORAGE ---
jobs = {}

def simplify_status(detailed_status):
    return "Solved" if detailed_status == "Solved" else "Not Solved"

# --- WORKER FUNCTION ---
def process_file_task(job_id: str, filepath: str, cf_problems, lc_problems, cc_problems):
    try:
        print(f" Processing file: {filepath}")
        
        # 1. Read File
        if filepath.endswith('.csv'):
             df = pd.read_csv(filepath)
        else:
             df = pd.read_excel(filepath, engine='openpyxl')
        
        # Clean data
        df = df.astype(str)
        df.replace(["nan", "NaN"], "", inplace=True)
        
        # Find Columns (Case Insensitive)
        cols = {c.upper(): c for c in df.columns}
        cf_col = cols.get('CODEFORCES')
        lc_col = cols.get('LEETCODE')
        cc_col = cols.get('CODECHEF')

        total_students = len(df)
        print(f"👥 Found {total_students} students.")
        
        jobs[job_id]["total"] = total_students
        jobs[job_id]["status"] = "processing"

        df['Score'] = 0
        student_results = [] 

        # 2. Loop Through Students
        for index, row in df.iterrows():
            jobs[job_id]["current"] = index + 1
            time.sleep(0.5) 

            current_score = 0
            student_data = row.to_dict()
            
            # --- CODEFORCES ---
            if cf_col:
                uid = row[cf_col].strip()
                if uid:
                    for prob in cf_problems:
                        if not prob: continue 
                        status = simplify_status(check_codeforces_status(uid, prob))
                        student_data[f'CF: {prob}'] = status
                        if status == "Solved": current_score += 1

            # --- LEETCODE ---
            if lc_col:
                uid = row[lc_col].strip()
                if uid:
                    for prob in lc_problems:
                        if not prob: continue
                        status = simplify_status(check_leetcode_status(uid, prob))
                        student_data[f'LC: {prob}'] = status
                        if status == "Solved": current_score += 1

            # --- CODECHEF ---
            if cc_col:
                uid = row[cc_col].strip()
                if uid:
                    for prob in cc_problems:
                        if not prob: continue
                        raw_status = check_codechef_status(uid, prob)
                        status = "Solved" if raw_status == "Solved" else "Not Solved"
                        student_data[f'CC: {prob}'] = status
                        if status == "Solved": current_score += 1

            # Save Score
            student_data['Score'] = current_score
            student_results.append(student_data)
            print(f"   ✅ Processed Student {index + 1}/{total_students}: {student_data.get('NAME', 'Unknown')}")

        # 3. Save to Database
        report_id = None
        if reports_collection is not None:
            print(f"💾 Saving {len(student_results)} records to MongoDB...")
            report_doc = {
                "created_at": datetime.now(timezone.utc),
                "total_students": total_students,
                "data": student_results
            }
            inserted = reports_collection.insert_one(report_doc)
            report_id = str(inserted.inserted_id)
            print(f"✨ Report Saved! ID: {report_id}")
        else:
            print("❌ Error: Database connection is missing.")

        # 4. Save Excel
        df_result = pd.DataFrame(student_results)
        all_cols = list(df_result.columns)
        problem_cols = [c for c in all_cols if c.startswith("CF: ") or c.startswith("LC: ") or c.startswith("CC: ")]
        score_col = ['Score'] if 'Score' in all_cols else []
        exclude_set = set(problem_cols + score_col)
        input_cols = [c for c in all_cols if c not in exclude_set]
        final_cols = input_cols + score_col + problem_cols
        df_result = df_result[final_cols]

        output_filename = f"processed_{job_id}.xlsx"
        df_result.to_excel(output_filename, index=False)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["filename"] = output_filename
        jobs[job_id]["report_id"] = report_id
    
    except Exception as e:
        print(f"🔥 Worker Error: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


def process_refresh_task(job_id: str, report_id: str):
    try:
        print(f"Refreshing Report ID: {report_id}")

        # 1. Fetch Existing Report
        if reports_collection is None:
            raise Exception("Database not connected")

        report = reports_collection.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise Exception("Report not found in DB")

        student_data_list = report.get("data", [])
        total_students = len(student_data_list)

        # 2. Identify Problems from the first student record
        if total_students > 0:
            first_row = student_data_list[0]
            cf_problems = [k.split(": ")[1] for k in first_row.keys() if k.startswith("CF: ")]
            lc_problems = [k.split(": ")[1] for k in first_row.keys() if k.startswith("LC: ")]
            cc_problems = [k.split(": ")[1] for k in first_row.keys() if k.startswith("CC: ")]
        else:
            cf_problems, lc_problems, cc_problems = [], [], []

        jobs[job_id]["total"] = total_students
        jobs[job_id]["status"] = "processing"

        updated_results = []

        # 3. Re-Crawl Loop
        for index, student in enumerate(student_data_list):
            jobs[job_id]["current"] = index + 1
            time.sleep(0.5) # Polite Delay
            current_score = 0

            # --- CHECK CODEFORCES ---
            cf_handle = student.get("CODEFORCES") or student.get("codeforces") or ""
            if cf_handle:
                for prob in cf_problems:
                    status = simplify_status(check_codeforces_status(str(cf_handle), prob))
                    student[f'CF: {prob}'] = status
                    if status == "Solved": current_score += 1

            # --- CHECK LEETCODE ---
            lc_handle = student.get("LEETCODE") or student.get("leetcode") or ""
            if lc_handle:
                for prob in lc_problems:
                    status = simplify_status(check_leetcode_status(str(lc_handle), prob))
                    student[f'LC: {prob}'] = status
                    if status == "Solved": current_score += 1

            # --- CHECK CODECHEF ---
            cc_handle = student.get("CODECHEF") or student.get("codechef") or ""
            if cc_handle:
                for prob in cc_problems:
                    raw_status = check_codechef_status(str(cc_handle), prob)
                    status = "Solved" if raw_status == "Solved" else "Not Solved"
                    student[f'CC: {prob}'] = status
                    if status == "Solved": current_score += 1

            # Update Score
            student['Score'] = current_score
            updated_results.append(student)
            print(f"   updated {index+1}/{total_students}...")

        # 4. Update Database
        reports_collection.update_one(
            {"_id": ObjectId(report_id)},
            {
                "$set": {
                    "data": updated_results,
                    "last_updated": datetime.now(timezone.utc)
                }
            }
        )
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["report_id"] = report_id
        print("✅ Refresh Complete")

    except Exception as e:
        print(f" Refresh Error: {e}")
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

@app.get("/view-report/{report_id}")
def view_report(report_id: str):
    if reports_collection is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    try:
        report = reports_collection.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        report["_id"] = str(report["_id"])
        return report
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Report ID")


@app.post("/refresh-report/{report_id}")
async def refresh_report(report_id: str, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "queued",
        "current": 0,
        "total": 0
    }
    background_tasks.add_task(process_refresh_task, job_id, report_id)
    return {"job_id": job_id}

@app.get("/download-report/{report_id}")
def download_existing_report(report_id: str):
    if reports_collection is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    try:
        report = reports_collection.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        df = pd.DataFrame(report["data"])
        
        all_cols = list(df.columns)
        
        problem_cols = [c for c in all_cols if c.startswith("CF: ") or c.startswith("LC: ") or c.startswith("CC: ")]
        score_col = ['Score'] if 'Score' in all_cols else []
        
        exclude_set = set(problem_cols + score_col)
        input_cols = [c for c in all_cols if c not in exclude_set]
        
        final_cols = input_cols + score_col + problem_cols
        df = df[final_cols]

        filename = f"Report_{report_id}.xlsx"
        df.to_excel(filename, index=False)
        
        return FileResponse(filename, filename=f"Student_Report_{report_id[-4:]}.xlsx")

    except Exception as e:
        print(f"Download Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



