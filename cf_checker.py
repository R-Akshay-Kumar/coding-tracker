import requests
import time

def check_codeforces_status(handle, problem_id):
    # 1. Ask Codeforces for the user's last 100 submissions
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=100"
    
    try:
        response = requests.get(url)
        data = response.json()

        if data['status'] != "OK":
            return f"Error: {data.get('comment', 'Invalid Handle')}"

        # --- NEW LOGIC: Calculate the time 5 days ago ---
        current_time_unix = int(time.time())
        five_days_in_seconds = 5 * 24 * 60 * 60  # 5 days * 24 hrs * 60 mins * 60 secs
        cutoff_time = current_time_unix - five_days_in_seconds

        # 2. Check submissions
        submissions = data['result']
        for sub in submissions:
            # Construct the problem ID
            if 'contestId' in sub['problem']:
                current_id = str(sub['problem']['contestId']) + sub['problem']['index']
                
                # Check 1: Is it the right problem?
                # Check 2: Did they get it 'OK'?
                # Check 3: Was it submitted AFTER the cutoff time (recent 5 days)?
                if (current_id == problem_id and 
                    sub['verdict'] == 'OK' and 
                    sub['creationTimeSeconds'] > cutoff_time):
                    
                    return "Solved"
        
        return "Not Solved"

    except Exception as e:
        return f"Error: {e}"

# --- TEST ---
student_name = "bharath_maguluri"
problem_to_check = "231A" 

print(f"Checking if {student_name} solved {problem_to_check} in the last 5 days...")
result = check_codeforces_status(student_name, problem_to_check)
print(f"Result: {result}")