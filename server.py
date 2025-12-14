from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
import shutil
import os
from datetime import datetime

# Import your engines
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

def simplify_status(detailed_status):
    return "Solved" if detailed_status == "Solved" else "Not Solved"

@app.post("/check-status")
def check_status(
    file: UploadFile = File(...),
    cf_problems: List[str] = Form([]), # Accepting a LIST of problems now
    lc_problems: List[str] = Form([]),
    cc_problems: List[str] = Form([])
):
    # 1. Save File
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. Read & Clean
        if temp_filename.endswith('.csv'):
             df = pd.read_csv(temp_filename)
        else:
             df = pd.read_excel(temp_filename, engine='openpyxl')
        
        df = df.astype(str)
        df.replace(["nan", "NaN"], "", inplace=True)
        
        # Identify User ID Columns (to use them, then delete them)
        # We try to match variations like "CODEFORCES" or "Codeforces"
        cols = {c.upper(): c for c in df.columns}
        cf_col = cols.get('CODEFORCES')
        lc_col = cols.get('LEETCODE')
        cc_col = cols.get('CODECHEF')

        # 3. Process Students
        total_students = len(df)
        print(f"Processing {total_students} students...")

        # Initialize Score Column
        df['Score'] = 0

        for index, row in df.iterrows():
            print(f"Checking Student {index + 1} / {total_students}...") 
            
            current_score = 0
            
            # --- Check Multiple Codeforces Problems ---
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

            # --- Check Multiple LeetCode Problems ---
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

            # --- Check Multiple CodeChef Problems ---
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

            # Save the total score for this student
            df.at[index, 'Score'] = current_score

        # 4. Cleanup: Remove ID Columns
        columns_to_remove = [c for c in [cf_col, lc_col, cc_col] if c]
        df.drop(columns=columns_to_remove, inplace=True)

        # 5. Reorder: Put 'Score' right after Name/Roll Number
        cols = list(df.columns)
        cols.remove('Score')
        insert_pos = 3 if len(cols) >= 2 else 1
        cols.insert(insert_pos, 'Score')
        df = df[cols]

    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": f"Server Error: {str(e)}"}

    # 6. Save & Return
    output_filename = f"processed_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    df.to_excel(output_filename, index=False)
    return FileResponse(output_filename, filename=output_filename)