import os, base64, requests

BASE  = "https://ec8c82aetrial.it-cpitrial03.cfapps.ap21.hana.ondemand.com"
TOKEN = "https://ec8c82aetrial.authentication.ap21.hana.ondemand.com/oauth/token"
cid, sec = os.environ["CPI_CLIENTID"], os.environ["CPI_CLIENTSECRET"]

b64 = base64.b64encode(f"{cid}:{sec}".encode()).decode()
tok = requests.post(TOKEN, headers={"Authorization": f"Basic {b64}"},
                    data={"grant_type": "client_credentials"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Accept": "application/json"}

r = requests.get(f"{BASE}/api/v1/DataStores", headers=H)
print(r.status_code)
print(r.text[:800])