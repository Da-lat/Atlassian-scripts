import requests
import getpass

def get_user_credentials():
    print("🔐 Enter your Jira Cloud credentials")
    base_url = input("Jira URL (e.g. https://your-domain.atlassian.net): ").strip().rstrip("/")
    email = input("Your Jira email: ").strip()
    api_token = getpass.getpass("Your Jira API token (input hidden): ")
    return base_url, email, api_token

def check_projects_missing_admins(base_url, email, api_token):
    auth = (email, api_token)
    headers = {"Accept": "application/json"}

    # Step 1: Get all projects
    project_url = f"{base_url}/rest/api/3/project/search"
    try:
        project_response = requests.get(project_url, auth=auth, headers=headers)
        project_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching projects: {e}")
        return

    projects = project_response.json().get("values", [])

    print(f"\n🔍 Checking {len(projects)} project(s) for missing Administrators...\n")

    for project in projects:
        project_key = project["key"]
        project_name = project["name"]

        # Step 2: Get roles
        roles_url = f"{base_url}/rest/api/3/project/{project_key}/role"
        try:
            roles_response = requests.get(roles_url, auth=auth, headers=headers).json()
        except:
            print(f"⚠️  Could not fetch roles for {project_key}")
            continue

        admin_role_url = roles_response.get("Administrators")
        if not admin_role_url:
            print(f"⚠️  Project {project_key} ({project_name}) has no 'Administrators' role.")
            continue

        # Step 3: Check if admin role has users/groups
        admin_response = requests.get(admin_role_url, auth=auth, headers=headers).json()
        actors = admin_response.get("actors", [])

        if not actors:
            print(f"❌ Project {project_key} ({project_name}) has NO admins assigned.")
        else:
            print(f"✅ Project {project_key} ({project_name}) has {len(actors)} admin(s) assigned.")

if __name__ == "__main__":
    base_url, email, api_token = get_user_credentials()
    check_projects_missing_admins(base_url, email, api_token)
