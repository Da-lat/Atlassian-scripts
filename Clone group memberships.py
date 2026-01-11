import requests
from requests.auth import HTTPBasicAuth
import sys

# --- CONFIGURATION ---
BASE_URL = ""
EMAIL = ""
API_TOKEN = ""

SOURCE_GROUP = "AWS Support"  # Copy from here
DEST_GROUP = "new-year-2026"    # Paste to here
# ---------------------

auth = HTTPBasicAuth(EMAIL, API_TOKEN)
headers = {"Accept": "application/json", "Content-Type": "application/json"}

def get_group_members(group_name):
    """Fetches all accountIds from a group."""
    members = []
    url = f"{BASE_URL}/rest/api/3/group/member"
    params = {'groupname': group_name, 'maxResults': 50}
    
    print(f"📥 Fetching members from '{group_name}'...")
    while True:
        resp = requests.get(url, headers=headers, auth=auth, params=params)
        if resp.status_code == 404:
            print(f"❌ Group '{group_name}' not found.")
            sys.exit(1)
        resp.raise_for_status()
        data = resp.json()
        
        for user in data['values']:
            if user['accountType'] == 'atlassian': # Skip apps/bots if needed
                members.append(user['accountId'])
        
        if data['isLast']:
            break
        params['startAt'] = params.get('startAt', 0) + 50
        
    return members

def add_user_to_group(account_id, group_name):
    """Adds a single user to a group."""
    url = f"{BASE_URL}/rest/api/3/group/user"
    params = {'groupname': group_name}
    payload = {'accountId': account_id}
    
    resp = requests.post(url, headers=headers, auth=auth, params=params, json=payload)
    
    if resp.status_code == 201:
        print(f"  ✅ Added user {account_id}")
    elif resp.status_code == 400:
        # Usually means user is already in group
        print(f"  Example: User {account_id} already in group (Skipped)")
    else:
        print(f"  ❌ Failed to add {account_id}: {resp.status_code} {resp.text}")

def mirror_groups():
    # 1. Get Source Members
    source_members = get_group_members(SOURCE_GROUP)
    print(f"Found {len(source_members)} users in source.")

    if not source_members:
        print("Source group is empty. Exiting.")
        return

    # 2. (Optional) Check if Dest exists, if not, you might need to create it manually 
    # or handle the 404 in the add loop.
    
    print(f"🚀 cloning users to '{DEST_GROUP}'...")
    
    count = 0
    for account_id in source_members:
        add_user_to_group(account_id, DEST_GROUP)
        count += 1
        
    print(f"\n✨ Operation Complete. Processed {count} users.")

if __name__ == "__main__":
    mirror_groups()
