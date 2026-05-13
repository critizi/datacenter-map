"""
Wi-Fi Password Recovery & WPA2 Encoding Educational Tool

Demonstrates two things:
  1. How to retrieve a stored Wi-Fi password from macOS Keychain
     (which syncs via iCloud Keychain from your iPhone)
  2. How WPA2-PSK encodes your plain-text password into a
     cryptographic key (PMK) using PBKDF2-SHA1

IMPORTANT: Only use this on networks you own or have permission to access.

Requirements: macOS (uses the `security` CLI tool built into macOS)
"""

import subprocess
import hashlib
import sys
import platform


# ---------------------------------------------------------------------------
# Part 1 — Retrieve the stored password from macOS Keychain
# ---------------------------------------------------------------------------

def get_wifi_password_from_keychain(ssid: str) -> str | None:
    """
    Query the macOS system Keychain for a stored Wi-Fi password.

    macOS stores Wi-Fi passwords in the System keychain under the
    AirPort network service. When iCloud Keychain is enabled on your
    iPhone, passwords sync here automatically.

    Uses the built-in `security` CLI — no third-party dependencies needed.
    """
    if platform.system() != "Darwin":
        print("[!] Keychain lookup only works on macOS.")
        print("    On your iPhone: Settings → Wi-Fi → (i) → Password")
        return None

    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-wa", ssid],
            capture_output=True,
            text=True,
        )
        password = result.stdout.strip()
        if result.returncode != 0 or not password:
            print(f"[!] No stored password found for '{ssid}'.")
            print("    Make sure iCloud Keychain is enabled on your iPhone and Mac.")
            return None
        return password
    except FileNotFoundError:
        print("[!] `security` command not found — are you on macOS?")
        return None


def list_known_wifi_networks() -> list[str]:
    """
    List Wi-Fi networks your Mac has previously joined.
    These are candidates whose passwords are in the Keychain.
    """
    if platform.system() != "Darwin":
        print("[!] Network list lookup only works on macOS.")
        return []

    try:
        result = subprocess.run(
            [
                "networksetup",
                "-listpreferredwirelessnetworks",
                "en0",  # Wi-Fi interface — may be en1 on some Macs
            ],
            capture_output=True,
            text=True,
        )
        lines = result.stdout.strip().splitlines()
        # First line is a header ("Preferred networks on en0:")
        networks = [line.strip() for line in lines[1:] if line.strip()]
        return networks
    except FileNotFoundError:
        return []


# ---------------------------------------------------------------------------
# Part 2 — WPA2-PSK encoding: how your password becomes a cryptographic key
# ---------------------------------------------------------------------------

def derive_pmk(password: str, ssid: str) -> bytes:
    """
    Derive the WPA2 Pairwise Master Key (PMK) from a plain-text password.

    WPA2-PSK (Wi-Fi Protected Access 2, Pre-Shared Key) never transmits
    your password over the air. Instead it applies PBKDF2-HMAC-SHA1:

        PMK = PBKDF2(HMAC-SHA1, password, ssid, iterations=4096, dklen=32)

    Parameters:
      password  — your Wi-Fi password (8–63 ASCII chars for WPA2)
      ssid      — the network name (acts as the cryptographic salt)

    The SSID-as-salt means the same password on two differently named
    networks produces completely different PMKs, preventing pre-computed
    rainbow-table attacks.
    """
    pmk = hashlib.pbkdf2_hmac(
        hash_name="sha1",
        password=password.encode("ascii"),
        salt=ssid.encode("ascii"),
        iterations=4096,
        dklen=32,         # 256 bits
    )
    return pmk


def explain_encoding(password: str, ssid: str) -> None:
    """Print a human-readable breakdown of the WPA2 key derivation."""
    print("\n" + "=" * 60)
    print("WPA2-PSK Key Derivation Breakdown")
    print("=" * 60)
    print(f"  SSID (network name) : {ssid!r}")
    print(f"  Password            : {password!r}")
    print(f"  Algorithm           : PBKDF2-HMAC-SHA1")
    print(f"  Iterations          : 4096")
    print(f"  Output length       : 32 bytes (256 bits)")
    print()

    pmk = derive_pmk(password, ssid)
    print(f"  Pairwise Master Key (PMK):")
    print(f"    hex : {pmk.hex()}")
    print(f"    b64 : {__import__('base64').b64encode(pmk).decode()}")
    print()
    print("  What happens next (conceptually):")
    print("  1. Your device and the router each know the PMK.")
    print("  2. They run a 4-way handshake to derive a session key (PTK)")
    print("     using fresh random nonces — so each session is unique.")
    print("  3. All actual traffic is encrypted with AES-CCMP using the PTK.")
    print("  4. Your plain-text password is NEVER transmitted.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Wi-Fi Password Recovery & WPA2 Encoding Tool")
    print("(Educational — use only on your own networks)\n")

    # --- Step 1: show known networks ---
    print("[*] Fetching known Wi-Fi networks from your Mac...")
    networks = list_known_wifi_networks()
    if networks:
        print(f"[+] Found {len(networks)} known network(s):")
        for i, name in enumerate(networks, 1):
            print(f"    {i:>2}. {name}")
    else:
        print("    (Could not list networks — continuing with manual entry)")

    # --- Step 2: pick the target SSID ---
    if networks:
        raw = input("\nEnter the number or name of your Wi-Fi network: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(networks):
            ssid = networks[int(raw) - 1]
        else:
            ssid = raw
    else:
        ssid = input("Enter your Wi-Fi network name (SSID): ").strip()

    if not ssid:
        print("[!] No SSID provided. Exiting.")
        sys.exit(1)

    # --- Step 3: retrieve the password ---
    print(f"\n[*] Looking up password for '{ssid}' in Keychain...")
    password = get_wifi_password_from_keychain(ssid)

    if password:
        print(f"[+] Password retrieved: {password!r}")
    else:
        # Fall back to manual entry so the encoding demo still runs
        password = input("Enter the password manually to see the encoding demo: ").strip()

    if not password:
        print("[!] No password to work with. Exiting.")
        sys.exit(1)

    # --- Step 4: explain the WPA2 encoding ---
    explain_encoding(password, ssid)


if __name__ == "__main__":
    main()
