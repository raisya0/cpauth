#!/usr/bin/env python3
# domain_scan_stream.py - Streaming version, tidak load semua ke memory

import sys
import socket
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

def check_port(domain):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((domain, 2087))
        sock.close()
        if result == 0:
            return domain
    except:
        pass
    return None

def get_output_filename(input_file):
    """Generate output filename based on input filename"""
    base = os.path.basename(input_file)
    name, ext = os.path.splitext(base)
    # If file is hidden (starts with dot), preserve the dot
    if base.startswith('.'):
        return f".{name.lstrip('.')}_whm{ext}"
    else:
        return f"{name}_whm{ext}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 domain_scan_stream.py domains.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = get_output_filename(input_file)
    max_workers = 100
    batch_size = 10000  # Proses 10rb domain per batch

    print(f"[*] Scanning domains from {input_file} for port 2087 (streaming)")
    print(f"[*] Output will be saved to {output_file}")

    with open(output_file, 'w') as out:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            processed = 0

            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Submit task
                    future = executor.submit(check_port, line)
                    futures[future] = line
                    processed += 1

                    # Batch process: setiap selesai batch_size, ambil hasil
                    if len(futures) >= batch_size:
                        for future in as_completed(futures):
                            result = future.result()
                            if result:
                                out.write(f"https://{result}:2087\n")
                                out.flush()
                                print(f"[+] {result}:2087")
                        futures.clear()
                        print(f"[*] Progress: {processed} domains scanned")

            # Sisa futures
            for future in as_completed(futures):
                result = future.result()
                if result:
                    out.write(f"https://{result}:2087\n")
                    out.flush()
                    print(f"[+] {result}:2087")

    print(f"\n[✅] Done! Output saved to {output_file}")

if __name__ == "__main__":
    main()
