import requests, base64


auth_value = base64.b64encode(f"{username}:{password}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth_value}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

resp = requests.get(url, headers=headers, params={"sysparm_limit": 1})
print(resp.status_code, resp.text)
