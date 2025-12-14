import requests
import time

def check_leetcode_status(username, problem_slug):
    url = "https://leetcode.com/graphql"
    
    # GraphQL Query: Fetch recent successful submissions
    query = """
    query recentAcSubmissionList($username: String!) {
      recentAcSubmissionList(username: $username, limit: 20) {
        titleSlug
        timestamp
      }
    }
    """
    
    variables = {"username": username}
    
    try:
        response = requests.post(url, json={"query": query, "variables": variables})
        data = response.json()
        
        if 'errors' in data:
            return "Invalid User"
            
        submissions = data['data']['recentAcSubmissionList']
        
        # Check if the list is empty
        if not submissions:
            return "No recent accepted solutions found."
            
        target_slug = problem_slug.strip().lower()
        
        for sub in submissions:
            if sub['titleSlug'] == target_slug:
                return "Solved"
                
        return "Not Solved"

    except Exception as e:
        return f"Error: {e}"