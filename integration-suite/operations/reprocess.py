import os, base64, requests

TOKEN = "https://ec8c82aetrial.authentication.ap21.hana.ondemand.com/oauth/token"
GETPO = "https://ec8c82aetrial.it-cpitrial03-rt.cfapps.ap21.hana.ondemand.com/http/getpostatus"
cid, sec = os.environ["CPI_RUNTIME_ID"], os.environ["CPI_RUNTIME_SECRET"]

b64 = base64.b64encode(f"{cid}:{sec}".encode()).decode()
tok = requests.post(TOKEN, headers={"Authorization": f"Basic {b64}"},
                    data={"grant_type": "client_credentials"}).json()["access_token"]

po = "19007185"
r = requests.post(GETPO, headers={"Authorization": f"Bearer {tok}", "poNumber": po}, data="{}", timeout=30)
print("REPROCESS", po, "->", r.status_code)
print(r.text[:400])