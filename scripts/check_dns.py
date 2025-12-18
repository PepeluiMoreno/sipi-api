import socket

hostnames = [
    "pepelu-postgresql-joseluis-moreno.h.aivencloud.com",
    "pepelu-postgresql-joseluis-moreno.a.aivencloud.com",
    "pepelu-postgresql-joseluis-moreno.aivencloud.com",
    "pepelu-postgresql-joseluis-moreno.pg.aivencloud.com"
]

for h in hostnames:
    try:
        ip = socket.gethostbyname(h)
        print(f"FOUND: {h} -> {ip}")
    except socket.gaierror:
        print(f"NOT FOUND: {h}")
