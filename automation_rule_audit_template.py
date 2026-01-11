import requests
import json

url = "https://api.atlassian.com/automation/public/{product}/{cloudid}/rest/v1/rule/summary"

ATLASSIAN_USER =""
ATLASSIAN_API_TOKEN = ""

headers = {
  "Accept": "application/json"
}

response = requests.request(
   "GET",
   url,
   auth=(ATLASSIAN_USER, ATLASSIAN_API_TOKEN),
   headers={"Accept": "application/json"}
)

json_response = json.loads(response.text)

while json_response['links']['next'] is not None:
    next_url = url + json_response['links']['next']
    response = requests.request(
       "GET",
       next_url,
       auth=(ATLASSIAN_USER, ATLASSIAN_API_TOKEN),
       headers={"Accept": "application/json"}
    )
    json_response_page = json.loads(response.text)
    json_response['data'].extend(json_response_page['data'])
    json_response['links']['next'] = json_response_page['links']['next']

print(len(json_response['data']))

components_list = []  # accumulate all components here

for rule in json_response['data']:
    if rule['description'] == '' and rule['state'] == 'ENABLED':
        ruleUuid = rule['uuid']

        url = f"https://api.atlassian.com/automation/public/{product}/{cloudid}/rest/v1/rule/{ruleUuid}"

        headers = {
        "Accept": "application/json"
        }

        response = requests.request(
        "GET",
        url,
        auth=(ATLASSIAN_USER, ATLASSIAN_API_TOKEN),
        headers={"Accept": "application/json"}
        )

        components = json.loads(response.text)['rule']

        components_list.append(components)  # collect the page's components

# save accumulated components to a JSON file
output_path = r'YOUR_PATH\components.json'
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(components_list, f, indent=2, ensure_ascii=False)
print(f"Saved {len(components_list)} items to {output_path}")