"""
Test filtros geográficos en GraphQL
"""
import requests
import json

url = "http://127.0.0.1:8040/graphql/"

tests = [
    ("Filtro por nombre exacto", """
query {
  comunidadesAutonomas(filter: {nombre: {eq: "Andalucía"}}) {
    id
    nombre
    codigoIne
  }
}
"""),
    ("Filtro por código INE", """
query {
  comunidadesAutonomas(filter: {codigoIne: {eq: "13"}}) {
    id
    nombre
    nombreOficial
    codigoIne
  }
}
"""),
    ("Filtro con LIKE (contiene)", """
query {
  comunidadesAutonomas(filter: {nombre: {like: "%Cast%"}}) {
    id
    nombre
    codigoIne
  }
}
"""),
    ("Filtro con IN (múltiples valores)", """
query {
  comunidadesAutonomas(filter: {codigoIne: {in: ["1", "13", "9"]}}) {
    id
    nombre
    codigoIne
  }
}
"""),
    ("Sin filtro, con limit", """
query {
  comunidadesAutonomas(limit: 5) {
    id
    nombre
    codigoIne
  }
}
"""),
]

print("="*80)
print("TESTS DE FILTROS GEOGRÁFICOS - GraphQL API")
print("="*80)

for test_name, query in tests:
    print(f"\n{'='*80}")
    print(f"Test: {test_name}")
    print('='*80)

    response = requests.post(
        url,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        data = response.json()

        if "errors" in data:
            print(f"❌ ERROR: {data['errors']}")
        elif "data" in data and "comunidadesAutonomas" in data["data"]:
            results = data["data"]["comunidadesAutonomas"]
            print(f"✅ SUCCESS: {len(results)} resultados")
            for item in results:
                print(f"  - {item.get('nombre', 'N/A')} (INE: {item.get('codigoIne', 'N/A')})")
        else:
            print(f"⚠️  Respuesta inesperada: {data}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text)

print(f"\n{'='*80}")
print("TESTS COMPLETADOS")
print('='*80)
