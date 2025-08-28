import requests, base64

username = "dev2APIaccount"
password = "US7X1+g@QD*ft#96TLdbik$"

auth_value = base64.b64encode(f"{username}:{password}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth_value}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

url = "https://illuminadev2.service-now.com/api/now/table/incident"
resp = requests.get(url, headers=headers, params={"sysparm_limit": 1})
print(resp.status_code, resp.text)
