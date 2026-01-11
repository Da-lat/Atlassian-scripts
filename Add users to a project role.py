import requests
from requests.auth import HTTPBasicAuth
import json
import sys

# --- CONFIGURATION ---
BASE_URL = ""  # No trailing slash
EMAIL = ""
API_TOKEN = ""

# The project to scan
PROJECT_KEY = ""

# The Role ID you want to add users TO
# (Run the helper function below if you don't know this ID)
TARGET_ROLE_ID = 10000
# ---------------------

# Setup Session
session = requests.Session()
session.auth = HTTPBasicAuth(EMAIL, API_TOKEN)
session.headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_role_details(project_key, role_id):
    """Fetches the self URL for a specific role in a project."""
    url = f"{BASE_URL}/rest/api/3/project/{project_key}/role/{role_id}"
    resp = session.get(url)
    if resp.status_code == 404:
        print(f"❌ Role ID {role_id} not found in project {project_key}")
        sys.exit(1)
    return resp.json()

def get_all_project_users(project_key):
    """
    Scans ALL roles in the project to build a set of unique Account IDs.
    This finds everyone who currently has 'some' access to the project.
    """
    print(f"🔍 Scanning users in project '{project_key}'...")
    
    # Get all role URLs for the project
    roles_resp = session.get(f"{BASE_URL}/rest/api/3/project/{project_key}/role")
    roles_resp.raise_for_status()
    roles_map = roles_resp.json() # Returns {"Developers": "URL", "Admin": "URL"}

    unique_users = set()

    for role_name, role_url in roles_map.items():
        # Fetch the details of who is in this role
        # The URL provided by Jira is full path, so we use it directly
        r = session.get(role_url)
        if r.status_code == 200:
            data = r.json()
            actors = data.get('actors', [])
            for actor in actors:
                # We only want actual users (atlassian-user-role-actor), not groups
                if actor['type'] == 'atlassian-user-role-actor':
                    # Add their accountId to our set
                    # Note: actor['actorUser'] object contains the accountId
                    user_id = actor.get('actorUser', {}).get('accountId')
                    if user_id:
                        unique_users.add(user_id)
    
    return unique_users

def add_users_to_target_role(project_key, role_id, user_ids):
    """Adds a list of accountIds to the specified project role."""
    if not user_ids:
        print("⚠️ No users found to add.")
        return

    print(f"🚀 Adding {len(user_ids)} users to Role ID {role_id}...")
    
    # We must post to the specific project-role endpoint
    url = f"{BASE_URL}/rest/api/3/project/{project_key}/role/{role_id}"
    
    # Jira API allows adding list of users in one request (up to a limit, usually safe for small batches)
    # Payload format: { "user": ["accountId1", "accountId2"] }
    payload = {
        "user": list(user_ids)
    }

    try:
        resp = session.post(url, json=payload)
        resp.raise_for_status()
        
        # Determine success
        data = resp.json()
        print(f"✅ Success! Updated role.")
        print(f"   Role Name: {data.get('name')}")
        print(f"   Description: {data.get('description')}")
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Failed to add users: {e}")
        print(f"   Response: {e.response.text}")

def helper_list_roles(project_key):
    """Run this once to find out which ID belongs to which Role Name"""
    print(f"📋 Listing Roles for {project_key}...")
    url = f"{BASE_URL}/rest/api/3/project/{project_key}/role"
    resp = session.get(url)
    data = resp.json()
    
    print(f"{'ID':<10} {'Role URL'}")
    print("-" * 60)
    for name, link in data.items():
        # extract ID from the end of the URL
        r_id = link.split('/')[-1]
        print(f"{r_id:<10} {name}")

# --- EXECUTION ---
if __name__ == "__main__":
    # UNCOMMENT THIS LINE FIRST to find your Role ID, then comment it out
    # helper_list_roles(PROJECT_KEY)

    # 1. Find all users currently on the project
    users_to_add = get_all_project_users(PROJECT_KEY)
    
    if users_to_add:
        print(f"Found {len(users_to_add)} unique users.")
        
        # 2. Add them to the new role
        add_users_to_target_role(PROJECT_KEY, TARGET_ROLE_ID, users_to_add)
    else:
        print("No users found in this project.")
