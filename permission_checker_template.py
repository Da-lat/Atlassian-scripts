import requests
import json

ATLASSIAN_USER =""
ATLASSIAN_API_TOKEN = ""

# Get all permission schemes

url_schemes = "https://<YOUR-SITE>.atlassian.net/rest/api/3/permissionscheme"

response = requests.request(
   "GET",
   url_schemes,
   auth=(ATLASSIAN_USER, ATLASSIAN_API_TOKEN),
   headers={"Accept": "application/json"}
)

json_response_schemes = json.loads(response.text)

scheme_ids = {}
for scheme in json_response_schemes['permissionSchemes']:
   print(f"ID: {scheme['id']} Name: {scheme['name']}")
   if scheme['id'] != 0:
      scheme_ids[scheme['id']] = scheme['name']

output_path = r'<PATH>/scheme_ids.json'
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(scheme_ids,f, indent=2, ensure_ascii=False)

# Get permission grants 

url_perms_grants = "https://<YOUR-SITE>.atlassian.net/rest/api/3/permissionscheme/{permissionSchemeId}/permission"

response = requests.request(
   "GET",
   url_perms_grants,
   auth=(ATLASSIAN_USER, ATLASSIAN_API_TOKEN),
   headers={"Accept": "application/json"}
)

grants_to_check = []

for scheme_id in scheme_ids.keys():
   print(f"Getting permissions for scheme ID: {scheme_id}")

   response = requests.request(
      "GET",
      url_perms_grants.format(permissionSchemeId=scheme_id),
      auth=(ATLASSIAN_USER, ATLASSIAN_API_TOKEN),
      headers={"Accept": "application/json"}
   )

   json_perm_grants = json.loads(response.text)
   for grant in json_perm_grants['permissions']:
      # if grant['holder']['type'] != 'projectRole' and grant['holder']['type'] != 'group' and grant['holder']['type'] != 'user' and grant['holder']['type'] != 'applicationRole' and grant['holder']['type'] != 'sd.customer.portal.only':
      if grant['holder']['type'] == 'anyone':
         grants_to_check.append(f"Scheme name: {scheme_ids[scheme_id]} | Grant: {grant}")

output_path = r'<PATH>/grants_to_check.json'
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(grants_to_check,f, indent=2, ensure_ascii=False)