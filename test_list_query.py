"""
Test different query variants
"""
import requests
import json

url = "http://127.0.0.1:8040/graphql/"

queries_to_test = [
    ("comunidadesAutonomas", """
query {
  comunidadesAutonomas {
    id
    nombre
    codigoIne
  }
}
"""),
    ("listComunidadesAutonomas", """
query {
  listComunidadesAutonomas {
    id
    nombre
    codigoIne
  }
}
"""),
    ("listComunidadAutonomas", """
query {
  listComunidadAutonomas {
    id
    nombre
    codigoIne
  }
}
"""),
]

for name, query in queries_to_test:
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)

    response = requests.post(
        url,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )

    data = response.json()
    if "data" in data:
        result_key = list(data["data"].keys())[0] if data["data"] else None
        if result_key and data["data"][result_key]:
            print(f"SUCCESS: Got {len(data['data'][result_key])} results")
            if data["data"][result_key]:
                print(f"First result: {data['data'][result_key][0]}")
        else:
            print(f"EMPTY: Query succeeded but returned no data")
    if "errors" in data:
        print(f"ERROR: {data['errors']}")
