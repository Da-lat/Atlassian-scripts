import requests
import json
from requests.auth import HTTPBasicAuth
import csv

# --- Configuration ---
JIRA_BASE_URL = ""
USERNAME = ""
API_TOKEN = ""
OUTPUT_FILE = "jira_screen_export.csv"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def get_all_screens(session):
    """
    Fetches the list of all screens (ID and Name).
    """
    print("Fetching list of all screens...")
    screens = []
    start_at = 0
    max_results = 100
    
    while True:
        url = f"{JIRA_BASE_URL}/rest/api/3/screens"
        params = {"startAt": start_at, "maxResults": max_results}
        
        try:
            response = session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            values = data.get('values', data) if isinstance(data, dict) else data
            
            if not values:
                break
            
            screens.extend(values)
            
            if isinstance(data, dict) and data.get('isLast'):
                break
            if len(values) < max_results:
                break
                
            start_at += len(values)
            
        except Exception as e:
            print(f"Error fetching screens list: {e}")
            break
            
    print(f"-> Found {len(screens)} screens.")
    return screens

def get_fields_for_screen(session, screen_id):
    """
    1. Gets all Tabs for a screen.
    2. Gets all Fields for each Tab.
    Returns a list of dictionaries containing field info.
    """
    all_fields_data = []
    
    # Step 1: Get Tabs
    tabs_url = f"{JIRA_BASE_URL}/rest/api/3/screens/{screen_id}/tabs"
    try:
        tabs_resp = session.get(tabs_url)
        if tabs_resp.status_code == 404:
            return []
        tabs_resp.raise_for_status()
        tabs = tabs_resp.json()
    except Exception:
        # Silently fail on tab errors to keep the CSV clean, or print if debugging
        return []

    # Step 2: Get Fields for each Tab
    for tab in tabs:
        tab_id = tab['id']
        tab_name = tab['name']
        
        fields_url = f"{JIRA_BASE_URL}/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields"
        try:
            fields_resp = session.get(fields_url)
            fields_resp.raise_for_status()
            fields = fields_resp.json()
            
            for field in fields:
                field_id = field.get('id')
                field_name = field.get('name')
                
                # Determine type
                if field_id.startswith("customfield_"):
                    f_type = "CUSTOM"
                else:
                    f_type = "SYSTEM"
                
                all_fields_data.append({
                    "tab": tab_name,
                    "field_id": field_id,
                    "field_name": field_name,
                    "type": f_type
                })
                
        except Exception:
            continue

    return all_fields_data

def main():
    # 1. Setup Session
    session = requests.Session()
    session.auth = HTTPBasicAuth(USERNAME, API_TOKEN)
    session.headers.update(HEADERS)

    # 2. Get Screens
    screens = get_all_screens(session)
    total_screens = len(screens)

    print(f"Starting detailed scan. Writing to {OUTPUT_FILE}...")

    # 3. Open CSV and Iterate
    # 'utf-8-sig' ensures Excel opens the CSV with correct special characters
    with open(OUTPUT_FILE, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        
        # Write CSV Header
        writer.writerow(['Screen Name', 'Screen ID', 'Tab Name', 'Field Type', 'Field Name', 'Field ID'])

        for index, screen in enumerate(screens):
            s_id = screen['id']
            s_name = screen['name']
            
            # User feedback (Console progress)
            print(f"Processing {index + 1}/{total_screens}: {s_name}...")

            # Fetch Fields
            fields_list = get_fields_for_screen(session, s_id)

            if not fields_list:
                # Write a row indicating empty screen
                writer.writerow([s_name, s_id, "N/A", "N/A", "No fields configured", ""])
            else:
                for item in fields_list:
                    writer.writerow([
                        s_name, 
                        s_id, 
                        item['tab'], 
                        item['type'], 
                        item['field_name'], 
                        item['field_id']
                    ])

    print(f"\nDone! Successfully exported data to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
