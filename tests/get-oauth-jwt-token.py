import http.client

conn = http.client.HTTPSConnection("<your-auth0-identity-service>.us.auth0.com")

payload = "{\"client_id\":\"<your-client-id>\",\"client_secret\":\"<your-client-secret>\",\"audience\":\"<your-audience-identifier>\",\"grant_type\":\"client_credentials\"}"

headers = { 'content-type': "application/json" }

conn.request("POST", "/oauth/token", payload, headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))