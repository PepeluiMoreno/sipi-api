"""
Test what's available in GraphQL context
"""
import requests
import json

url = "http://127.0.0.1:8040/graphql/"

# Create a mutation that doesn't actually do anything but logs context
query = """
query {
  __schema {
    queryType {
      name
    }
  }
}
"""

response = requests.post(
    url,
    json={"query": query},
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
