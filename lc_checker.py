import requests
import time
import json

def check_leetcode_status(username, problem_slug):
    url = "https://leetcode.com/graphql"
    
    # Query to get the last 20 Accepted submissions
    query = """
    query recentAcSubmissions($username: String!, $limit: Int!) {
      recentAcSubmissionList(username: $username, limit: $limit) {
        titleSlug
        timestamp
      }
    }
    """
    
    variables = {
        "username": username,
        "limit": 20
    }

    try:
        response = requests.post(url, json={"query": query, "variables": variables})
        
        if response.status_code != 200:
            return f"Error: Failed to connect (Status {response.status_code})"
            
        data = response.json()
        
        if "errors" in data:
            return "Invalid Username"
            
        submissions = data['data']['recentAcSubmissionList']
        
        if not submissions:
             return "No recent accepted solutions found."

        # --- 5-DAY LOGIC ---
        current_time_unix = int(time.time())
        five_days_in_seconds = 5 * 24 * 60 * 60
        cutoff_time = current_time_unix - five_days_in_seconds

        for sub in submissions:
            # Check 1: Match the problem slug
            if sub['titleSlug'] == problem_slug:
                submission_time = int(sub['timestamp'])
                
                # Check 2: Check the time
                if submission_time > cutoff_time:
                    return "Solved"
                else:
                    return "Not Solved (Old Submission)"

        return "Not Solved"

    except Exception as e:
        return f"Error: {e}"

# --- YOUR TEST ---
student_name = "reflipo8yg"
problem_to_check = "running-sum-of-1d-array" 

print(f"Checking if {student_name} solved {problem_to_check} recently...")
result = check_leetcode_status(student_name, problem_to_check)
print(f"Result: {result}")