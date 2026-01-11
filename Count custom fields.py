import sys
import requests
from requests.auth import HTTPBasicAuth

# --- CONFIGURATION ---
# Replace the placeholders below with your actual details
JIRA_URL = ""
EMAIL = ""
API_TOKEN = "" 
# ---------------------

def get_custom_fields():

    # Clean the URL just in case
    jira_url_clean = JIRA_URL.strip().rstrip('/')

    try:
        # Construct the API endpoint for fields
        # /rest/api/3/field is standard for Cloud, /rest/api/2/field often used for Server
        # We'll use 2 as it is generally compatible with both for fetching fields
        api_endpoint = f"{jira_url_clean}/rest/api/2/field"
        
        print(f"\nConnecting to {api_endpoint}...")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Make the GET request
        response = requests.get(
            api_endpoint,
            auth=HTTPBasicAuth(EMAIL, API_TOKEN),
            headers=headers
        )

        # Check for HTTP errors
        response.raise_for_status()

        print("Fetching fields (this may take a moment)...")
        
        # Parse JSON response directly
        all_fields = response.json()
        
        custom_field_count = 0
        
        print(f"\n{'ID':<25} | {'Name'}")
        print("-" * 60)

        for field in all_fields:
            # When using requests/json, 'field' is a dictionary, not an object
            # Check if 'custom' key exists and is True
            if field.get('custom') is True:
                print(f"{field.get('id'):<25} | {field.get('name')}")
                custom_field_count += 1
        
        print("-" * 60)
        print(f"\nSuccess! Found {custom_field_count} custom fields.")

    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP Error: {e}")
        if e.response.status_code == 401:
            print("Tip: Check your email and API Token (401 Unauthorized).")
        elif e.response.status_code == 404:
            print("Tip: Check your Jira URL.")
    except requests.exceptions.RequestException as e:
        print(f"\nConnection Error: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    get_custom_fields()
