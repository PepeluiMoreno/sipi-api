"""
Check available queries via introspection
"""
import requests
import json

url = "http://127.0.0.1:8040/graphql/"

query = """
query {
  __schema {
    queryType {
      fields {
        name
      }
    }
  }
}
"""

response = requests.post(
    url,
    json={"query": query},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    data = response.json()
    queries = data.get("data", {}).get("__schema", {}).get("queryType", {}).get("fields", [])

    # Filter for comunidad-related queries
    comunidad_queries = [q["name"] for q in queries if "comunidad" in q["name"].lower()]

    print(f"Found {len(queries)} total queries")
    print(f"\nComunidad-related queries:")
    for q in sorted(comunidad_queries):
        print(f"  - {q}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
