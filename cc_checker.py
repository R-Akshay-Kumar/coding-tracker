import requests
from bs4 import BeautifulSoup

def check_codechef_status(username, problem_code):
    url = f"https://www.codechef.com/recent/user?page=0&user_handle={username}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # 1. Get HTML
        if 'content' not in data:
            return "Invalid Handle"
            
        soup = BeautifulSoup(data['content'], 'html.parser')
        rows = soup.find_all('tr')
        
        if not rows:
            return "No recent activity found"

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            
            # 2. Check Problem Code (Column 1)
            p_code = cols[1].text.strip()
            
            if p_code == problem_code:
                
                # 3. Check Status (Green Tick in Column 2)
                status_icon = cols[2].find('img')
                is_solved = status_icon and "tick" in status_icon.get('src', '')
                
                if is_solved:
                    # 4. Check Time (Column 0 title attribute)
                    # The HTML is <td title="10 hours ago">...
                    if cols[0].has_attr('title'):
                        time_text = cols[0]['title'] # e.g., "10 hours ago" or "6 days ago"
                        
                        # --- LOGIC: Parse the "Ago" text ---
                        if "sec" in time_text or "min" in time_text or "hour" in time_text:
                            return "Solved" # It was done today
                        
                        elif "day" in time_text:
                            # Extract the number: "2 days ago" -> 2
                            try:
                                days_ago = int(time_text.split()[0])
                                if days_ago <= 5:
                                    return "Solved"
                                else:
                                    return "Not Solved (Old Submission)"
                            except:
                                return "Error Parsing Date"
                        
                        else:
                            # If it says "month" or "year", it's too old
                            return "Not Solved (Old Submission)"
                            
        return "Not Solved"

    except Exception as e:
        return f"Error: {e}"

# --- TEST ---
student_name = "giddy_tear_64"
problem_to_check = "SANDWSHOP" 

print(f"Checking if {student_name} solved {problem_to_check} recently...")
result = check_codechef_status(student_name, problem_to_check)
print(f"Result: {result}")