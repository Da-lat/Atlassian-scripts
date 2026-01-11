import sys
import csv
import getpass
import requests
import json

def connect_to_jira(server_url, email, api_token):
    """
    Verifies connection to Jira server using requests.
    """
    # Ensure URL doesn't end with a slash
    base_url = server_url.rstrip('/')
    url = f"{base_url}/rest/api/3/myself"
    
    auth = (email, api_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, auth=auth, headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"Successfully connected as: {user_data.get('displayName')}")
            # Return session details for reuse
            return {"base_url": base_url, "auth": auth, "headers": headers}
        else:
            print(f"\nError connecting to Jira: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\nAn unexpected connection error occurred: {e}")
        return None

def get_projects_and_issue_types(session):
    """
    Fetches all projects and extracts their associated issue types using REST API.
    """
    print("\nFetching projects... (this may take a moment depending on the size of your instance)")
    
    project_data = []
    base_url = session['base_url']
    auth = session['auth']
    headers = session['headers']
    
    try:
        # Get all projects
        # We use expand=issueTypes to try and get them in one go, 
        # though sometimes full detail requires per-project fetching.
        projects_url = f"{base_url}/rest/api/3/project?expand=issueTypes"
        response = requests.get(projects_url, auth=auth, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching project list: {response.status_code}")
            return []

        projects = response.json()
        total_projects = len(projects)
        print(f"Found {total_projects} projects. Analyzing issue types...")

        for index, project in enumerate(projects, 1):
            if index % 10 == 0:
                print(f"Processing {index}/{total_projects}...")
            
            project_key = project.get('key')
            project_name = project.get('name')
            
            # The list endpoint with expand=issueTypes usually provides the data we need.
            # If issueTypes is missing, we fetch the specific project detail.
            issue_types_list = project.get('issueTypes', [])
            
            if not issue_types_list:
                # Fallback: Fetch specific project details if not in summary
                try:
                    detail_url = f"{base_url}/rest/api/3/project/{project_key}"
                    detail_resp = requests.get(detail_url, auth=auth, headers=headers)
                    if detail_resp.status_code == 200:
                        issue_types_list = detail_resp.json().get('issueTypes', [])
                except requests.exceptions.RequestException:
                    print(f"Could not retrieve details for project {project_key}")

            # Extract names
            issue_type_names = [it.get('name') for it in issue_types_list]
            
            # Store the data
            project_data.append({
                "Project Name": project_name,
                "Project Key": project_key,
                "Issue Types": ", ".join(issue_type_names),
                "Issue Type Count": len(issue_type_names)
            })

    except requests.exceptions.RequestException as e:
        print(f"Error during API requests: {e}")

    return project_data

def save_to_csv(data, filename="jira_project_issue_types.csv"):
    """
    Saves the analyzed data to a CSV file.
    """
    if not data:
        print("No data to save.")
        return

    try:
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)
        print(f"\nReport successfully saved to '{filename}'")
    except IOError as e:
        print(f"Error saving CSV file: {e}")

def main():
    print("--- Jira Project Issue Type Auditor (Requests Version) ---")
    print("Please enter your Jira credentials.")
    
    # User Input
    server_url = input("Jira URL (e.g., https://yourcompany.atlassian.net): ").strip()
    email = input("Email Address (User): ").strip()
    
    print("Note: For Jira Cloud, use an API Token, not your password.")
    # getpass ensures the token isn't visible on screen while typing
    api_token = getpass.getpass("API Token: ").strip()

    # Execution
    session = connect_to_jira(server_url, email, api_token)
    
    if session:
        data = get_projects_and_issue_types(session)
        
        if data:
            # Print summary to console
            print(f"\n--- Summary ({len(data)} Projects) ---")
            print(f"{'Key':<10} | {'Project Name':<30} | {'Issue Types'}")
            print("-" * 80)
            for row in data:
                display_types = (row['Issue Types'][:40] + '..') if len(row['Issue Types']) > 40 else row['Issue Types']
                print(f"{row['Project Key']:<10} | {row['Project Name']:<30} | {display_types}")
            
            save_to_csv(data)
        else:
            print("No project data found.")

if __name__ == "__main__":
    main()
