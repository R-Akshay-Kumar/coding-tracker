import requests
from bs4 import BeautifulSoup

def check_codechef_status(username, problem_code):
    # Note: This fetches the 'Recent Activity' feed (last ~20-50 actions)
    url = f"https://www.codechef.com/recent/user?page=0&user_handle={username}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'content' not in data:
            return "Invalid Handle"
            
        soup = BeautifulSoup(data['content'], 'html.parser')
        rows = soup.find_all('tr')
        
        if not rows:
            return "No recent activity found"

        target_code = problem_code.strip().upper()

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            
            # Column 1: Problem Code
            p_code = cols[1].text.strip().upper()
            
            if p_code == target_code:
                # Column 2: Status Icon
                status_icon = cols[2].find('img')
                # We check if the icon source contains "tick" (Success)
                is_solved = status_icon and "tick" in status_icon.get('src', '')
                
                if is_solved:
                    return "Solved"
                            
        return "Not Solved"

    except Exception as e:
        return f"Error: {e}"