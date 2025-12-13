from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import shutil
import os
from datetime import datetime

# Import your engines
# Ensure cf_checker.py, lc_checker.py, and cc_checker.py are in the same folder
from cf_checker import check_codeforces_status
from lc_checker import check_leetcode_status
from cc_checker import check_codechef_status

app = FastAPI()

# --- ALLOW FRONTEND TO TALK TO BACKEND ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER: SIMPLIFY STATUS ---
def simplify_status(detailed_status):
    # Only keep "Solved". Everything else becomes "Not Solved".
    if detailed_status == "Solved":
        return "Solved"
    else:
        return "Not Solved"

@app.post("/check-status")
def check_status(
    file: UploadFile = File(...),
    cf_problem: str = Form(None),
    lc_problem: str = Form(None),
    cc_problem: str = Form(None)
):
    # 1. Save the uploaded file temporarily
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"Processing file: {temp_filename}")

    # 2. Read the file (Robust Mode)
    try:
        if temp_filename.endswith('.csv'):
             df = pd.read_csv(temp_filename)
        else:
             # FIX: Explicitly use openpyxl engine
             df = pd.read_excel(temp_filename, engine='openpyxl')
        
        # CLEANING: Convert all data to strings and remove "NaN" (empty cells)
        df = df.astype(str)
        df.replace("nan", "", inplace=True)
        df.replace("NaN", "", inplace=True)

    except Exception as e:
        print(f"CRASH READING FILE: {e}")
        return {"error": f"Could not read file: {str(e)}"}

    # 3. Create Result Columns
    if cf_problem: df[f'CF: {cf_problem}'] = "Pending"
    if lc_problem: df[f'LC: {lc_problem}'] = "Pending"
    if cc_problem: df[f'CC: {cc_problem}'] = "Pending"

    # 4. RUN THE LOGIC (Loop through students)
    total_students = len(df)
    for index, row in df.iterrows():
        print(f"Checking Student {index + 1}/{total_students}...")
        
        # -- Codeforces --
        if cf_problem:
            uid = row.get('CODEFORCES')
            if uid and uid.strip().lower() != 'nan' and uid.strip() != '':
                res = check_codeforces_status(uid.strip(), cf_problem)
                df.at[index, f'CF: {cf_problem}'] = simplify_status(res)
            else:
                df.at[index, f'CF: {cf_problem}'] = "No ID"
        
        # -- LeetCode --
        if lc_problem:
            uid = row.get('LEETCODE')
            if uid and uid.strip().lower() != 'nan' and uid.strip() != '':
                res = check_leetcode_status(uid.strip(), lc_problem)
                df.at[index, f'LC: {lc_problem}'] = simplify_status(res)
            else:
                df.at[index, f'LC: {lc_problem}'] = "No ID"

        # -- CodeChef --
        if cc_problem:
            uid = row.get('CODECHEF')
            if uid and uid.strip().lower() != 'nan' and uid.strip() != '':
                res = check_codechef_status(uid.strip(), cc_problem)
                df.at[index, f'CC: {cc_problem}'] = simplify_status(res)
            else:
                df.at[index, f'CC: {cc_problem}'] = "No ID"

    # 5. Save the result
    output_filename = f"processed_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    df.to_excel(output_filename, index=False)
    print(f"Success! Saved to {output_filename}")

    # 6. Return the file
    return FileResponse(
        path=output_filename, 
        filename=output_filename, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )