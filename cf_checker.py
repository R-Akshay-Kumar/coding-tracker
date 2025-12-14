import requests

def check_codeforces_status(username, problem_id):
    url = f"https://codeforces.com/api/user.status?handle={username}&from=1&count=100"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['status'] != 'OK':
            return "Error: Invalid Handle or Private"
            
        submissions = data['result']
        
        # Standardize problem ID (e.g., "231A" -> "231A")
        target_id = problem_id.strip().upper()
        
        for sub in submissions:
            # Construct problem ID from API data (ContestID + Index, e.g. 231 + A)
            if 'contestId' in sub['problem'] and 'index' in sub['problem']:
                p_id = str(sub['problem']['contestId']) + sub['problem']['index']
                
                if p_id == target_id:
                    # CHECK: Is it a correct solution?
                    if sub['verdict'] == 'OK':
                        return "Solved"
                        
        return "Not Solved"

    except Exception as e:
        return f"Error: {e}"