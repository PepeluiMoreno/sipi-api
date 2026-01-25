"""
Test GraphQL API query for comunidades autonomas
"""
import requests
import json

url = "http://127.0.0.1:8040/graphql/"

query = """
query {
  comunidadesAutonomas {
    id
    nombre
    nombreOficial
    codigoIne
  }
}
"""

response = requests.post(
    url,
    json={"query": query},
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"Response:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
