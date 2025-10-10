import requests
api="f86208ba1e3bc347311c2defce8d689f"; secret="ad69a7bef44e0714e11c746276e4c352"
r = requests.get("https://api.mailjet.com/v3/REST/apikey", auth=(api, secret), timeout=15)
print(r.status_code, r.text)
