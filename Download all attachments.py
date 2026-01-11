from jira import JIRA
import requests
import os

# ---------------------
# CONFIGURATION
# ---------------------
JIRA_URL = ""
EMAIL = ""
API_TOKEN = ""
ISSUE_KEY = ""  # Replace with your issue key
SAVE_DIR = "attachments"#list your directory full path here 

# ---------------------
# CONNECT TO JIRA
# ---------------------
jira = JIRA(server=JIRA_URL, basic_auth=(EMAIL, API_TOKEN))

# ---------------------
# DOWNLOAD ATTACHMENTS
# ---------------------
def download_attachments(issue_key, save_dir="attachments"):
    issue = jira.issue(issue_key)
    os.makedirs(save_dir, exist_ok=True)

    for attachment in issue.fields.attachment:
        file_url = attachment.content
        file_name = attachment.filename

        print(f"Downloading: {file_name}...")
        response = requests.get(file_url, auth=(EMAIL, API_TOKEN))
        if response.status_code == 200:
            with open(os.path.join(save_dir, file_name), 'wb') as f:
                f.write(response.content)
            print(f"✔ Saved: {file_name}")
        else:
            print(f"✘ Failed to download: {file_name} (HTTP {response.status_code})")

# ---------------------
# RUN IT
# ---------------------
download_attachments(ISSUE_KEY, SAVE_DIR)
