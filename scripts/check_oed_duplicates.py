"""Check OED API for duplicate entries."""
import requests

# Query OED API directly
r = requests.get(
    'https://openenzymedb-api.platform.moleculemaker.org/api/v1/data',
    params={'ec': '3.2.1.21', 'limit': 200},
    timeout=60
)
data = r.json().get('data', [])

# Find D2C716
d2c = [d for d in data if 'D2C716' in str(d.get('uniprot', ''))]
print(f"D2C716 entries in OED API: {len(d2c)}")
for d in d2c:
    print(f"  kcat={d.get('kcat_value')}, Km={d.get('km_value')}, substrate={d.get('substrate')}")

# Find F4YTG7
print()
f4y = [d for d in data if 'F4YTG7' in str(d.get('uniprot', ''))]
print(f"F4YTG7 entries in OED API (should be EG, but check): {len(f4y)}")

# Check EG API
r2 = requests.get(
    'https://openenzymedb-api.platform.moleculemaker.org/api/v1/data',
    params={'ec': '3.2.1.4', 'limit': 200},
    timeout=60
)
data2 = r2.json().get('data', [])
f4y2 = [d for d in data2 if 'F4YTG7' in str(d.get('uniprot', ''))]
print(f"F4YTG7 entries in OED API (EC 3.2.1.4): {len(f4y2)}")
for d in f4y2[:5]:
    print(f"  kcat={d.get('kcat_value')}, Km={d.get('km_value')}, substrate={d.get('substrate')}")
