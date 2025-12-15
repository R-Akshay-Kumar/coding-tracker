from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
import shutil
import os
import uuid
import time
from datetime import datetime
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
origins = [
    "http://localhost:5173",             
    "http://127.0.0.1:5173",             
    "https://coding-tracker-tau.vercel.app",   # YOUR VERCEL FRONTEND
    "https://coding-tracker-backend.onrender.com" # YOUR RENDER BACKEND
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
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
        print(f"📂 Processing file: {filepath}")
        
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
                "created_at": datetime.now(),
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
        cols = list(df_result.columns)
        if 'Score' in cols:
            cols.remove('Score')
            cols.insert(2, 'Score') 
            df_result = df_result[cols]

        output_filename = f"processed_{job_id}.xlsx"
        df_result.to_excel(output_filename, index=False)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["filename"] = output_filename
        jobs[job_id]["report_id"] = report_id
    
    except Exception as e:
        print(f"🔥 Worker Error: {e}")
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
