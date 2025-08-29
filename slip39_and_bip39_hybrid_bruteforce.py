#!/usr/bin/env python3
"""
Simple SLIP-39 + BIP-39 Passphrase Brute Force Tool

This tool:
1. Reads a SLIP-39 mnemonic from .env
2. Recovers the seed from SLIP-39
3. Uses that seed with BIP-39 passphrase derivation to brute force passphrases
4. Matches generated addresses against a target address
"""

import os
import hashlib
import itertools
from typing import List, Iterator
from dotenv import load_dotenv
import slip39
from eth_account import Account

# Enable HD wallet features
Account.enable_unaudited_hdwallet_features()


def generate_passphrase_combinations(components: List[str]) -> Iterator[str]:
    """Generate all possible combinations of passphrase components."""
    # Try empty passphrase first
    yield ""
    
    # Then try all combinations and permutations
    for length in range(1, len(components) + 1):
        for combo in itertools.combinations(components, length):
            for perm in itertools.permutations(combo):
                yield "".join(perm)


def slip39_seed_to_eth_address(mnemonic: str, passphrase: str = "", account_index: int = 0, method: str = "keystone") -> str:
    """Convert SLIP-39 mnemonic + passphrase to Ethereum address using different methods."""
    
    if method == "keystone":
        # Method 1: SLIP-39 Native Passphrase (Works with Keystone)
        try:
            if passphrase:
                master_secret = slip39.recover([mnemonic], passphrase=passphrase.encode('utf-8'))
            else:
                master_secret = slip39.recover([mnemonic])
            
            eth_account = slip39.account(master_secret, 'ETH', f"m/44'/60'/0'/0/{account_index}")
            return eth_account.address
        except Exception as e:
            raise ValueError(f"Error generating address (Keystone method): {e}")
    
    elif method == "trezor_bip39":
        # Method 2: SLIP-39 + BIP-39 Mode (Potentially Trezor Compatible)
        try:
            if passphrase:
                master_secret = slip39.recover([mnemonic], passphrase=passphrase.encode('utf-8'), using_bip39=True)
            else:
                master_secret = slip39.recover([mnemonic], using_bip39=True)
            
            eth_account = slip39.account(master_secret, 'ETH', f"m/44'/60'/0'/0/{account_index}")
            return eth_account.address
        except Exception as e:
            raise ValueError(f"Error generating address (Trezor BIP-39 method): {e}")
    
    elif method == "manual_bip39":
        # Method 3: SLIP-39 Entropy + Manual BIP-39 Passphrase Derivation
        try:
            import hashlib
            from eth_account import Account
            
            # Enable HD wallet features
            Account.enable_unaudited_hdwallet_features()
            
            # Get SLIP-39 entropy as BIP-39 seed
            entropy_as_seed = slip39.recover([mnemonic], using_bip39=True)
            
            # Apply BIP-39 style passphrase derivation
            if passphrase:
                final_seed = hashlib.pbkdf2_hmac(
                    'sha512',
                    entropy_as_seed,
                    passphrase.encode('utf-8'),
                    2048,
                    64
                )
            else:
                final_seed = entropy_as_seed
            
            # Use first 32 bytes as private key
            private_key = final_seed[:32]
            account = Account.from_key(private_key)
            return account.address
        except Exception as e:
            raise ValueError(f"Error generating address (Manual BIP-39 method): {e}")
    
    elif method == "trezor_pure":
        # Method 4: Pure Trezor Mode - using_bip39=True for BOTH Step 1 and passphrase
        try:
            # Step 1: Use BIP-39 mode for recovery (this might be what Trezor does)
            base_seed = slip39.recover([mnemonic], using_bip39=True)
            
            # Step 2: Apply BIP-39 style passphrase to the BIP-39 seed
            import hashlib
            
            if passphrase:
                # BIP-39 standard: PBKDF2 with "mnemonic" + passphrase as salt
                final_seed = hashlib.pbkdf2_hmac(
                    'sha512',
                    base_seed,
                    f"mnemonic{passphrase}".encode('utf-8'),
                    2048,
                    64
                )
            else:
                final_seed = base_seed
            
            # Step 3: Use first 32 bytes as private key (simple approach)
            from eth_account import Account
            Account.enable_unaudited_hdwallet_features()
            
            private_key_bytes = final_seed[:32]
            account = Account.from_key(private_key_bytes)
            return account.address
        except Exception as e:
            raise ValueError(f"Error generating address (Pure Trezor method): {e}")
    
    else:
        raise ValueError(f"Unknown method: {method}")


def test_all_methods(mnemonic: str, passphrase: str, target_address: str, account_index: int = 0) -> dict:
    """Test all derivation methods and return results."""
    methods = {
        "keystone": "SLIP-39 Native (Keystone)",
        "trezor_bip39": "SLIP-39 + BIP-39 Mode (Trezor?)",
        "manual_bip39": "Manual BIP-39 Derivation",
        "trezor_pure": "Pure Trezor Mode (BIP-39 Step1+Step2)"
    }
    
    results = {}
    
    for method_key, method_name in methods.items():
        try:
            address = slip39_seed_to_eth_address(mnemonic, passphrase, account_index, method_key)
            matches = address.lower() == target_address.lower()
            results[method_key] = {
                "name": method_name,
                "address": address,
                "matches": matches,
                "error": None
            }
        except Exception as e:
            results[method_key] = {
                "name": method_name,
                "address": None,
                "matches": False,
                "error": str(e)
            }
    
    return results


def main():
    # Load environment
    load_dotenv()
    
    # Get configuration from .env
    mnemonic = os.getenv('MNEMONIC', '').strip()
    components_str = os.getenv('WORDS', '').strip()
    target_address = os.getenv('TARGET_ADDRESS', '').strip()
    
    if not mnemonic:
        print("❌ Error: MNEMONIC not found in .env file")
        return
    
    if not components_str:
        print("❌ Error: WORDS not found in .env file")
        return
    
    if not target_address:
        print("❌ Error: TARGET_ADDRESS not found in .env file")
        return
    
    # Parse components
    if ',' in components_str:
        components = [w.strip() for w in components_str.split(',') if w.strip()]
    else:
        components = components_str.split()
    
    # Normalize target address
    target_address = target_address.lower()
    if not target_address.startswith('0x'):
        target_address = '0x' + target_address
    
    print(f"🔍 Starting SLIP-39 seed recovery + BIP-39 passphrase brute force")
    print(f"📝 Mnemonic: {mnemonic[:50]}...")
    print(f"🔧 Components: {', '.join(components)}")
    print(f"🎯 Target: {target_address}")
    print()
    
    # Step 1: Recover master secret from SLIP-39 mnemonic
    print("🔐 Step 1: Recovering master secret from SLIP-39 mnemonic...")
    try:
        # Use SLIP-39 to get the master secret
        master_secret = slip39.recover([mnemonic])
        
        print(f"✅ SLIP-39 master secret recovered successfully")
        print(f"📊 Master secret: {master_secret.hex()[:32]}...")
        print(f"📊 Master secret length: {len(master_secret)} bytes")
            
    except Exception as e:
        print(f"❌ Error recovering SLIP-39 master secret: {e}")
        print("💡 Your mnemonic might not be a complete/valid SLIP-39 share")
        return
    
    print()
    
    # Step 2: Test empty passphrase with all methods first
    print("🔐 Step 2: Testing empty passphrase with all methods...")
    empty_results = test_all_methods(mnemonic, "", target_address)
    
    working_method = None
    for method_key, result in empty_results.items():
        status = "✅ MATCH!" if result["matches"] else "❌"
        if result["error"]:
            print(f"   {result['name']}: ERROR - {result['error']}")
        else:
            print(f"   {result['name']}: {result['address']} {status}")
            if result["matches"]:
                working_method = method_key
                print(f"🎉 SUCCESS! Empty passphrase matches using {result['name']} method!")
                return
    
    if not working_method:
        print("❌ Empty passphrase doesn't match with any method")
        print("💡 Will test all methods during brute force...")
    
    print()
    
    # Step 3: Brute force with component combinations
    print("🔐 Step 3: Brute forcing passphrase combinations...")
    
    total_combinations = sum(
        len(list(itertools.permutations(itertools.combinations(components, r), r)))
        for r in range(1, len(components) + 1)
    )
    print(f"🔢 Total combinations to try: {total_combinations}")
    print()
    
    attempt = 0
    for passphrase in generate_passphrase_combinations(components):
        if passphrase == "":  # Skip empty, already tested
            continue
            
        attempt += 1
        
        # Test all methods for this passphrase
        passphrase_results = test_all_methods(mnemonic, passphrase, target_address)
        
        # Check if any method matches
        match_found = False
        matching_method = None
        matching_address = None
        
        for method_key, result in passphrase_results.items():
            if result["matches"]:
                match_found = True
                matching_method = result["name"]
                matching_address = result["address"]
                break
        
        # Show progress
        if attempt <= 5 or attempt % 10 == 0 or match_found:
            print(f"🔄 Attempt {attempt}: '{passphrase}'")
            for method_key, result in passphrase_results.items():
                status = "✅ MATCH!" if result["matches"] else "❌"
                if result["error"]:
                    print(f"      {result['name']}: ERROR")
                else:
                    print(f"      {result['name']}: {result['address']} {status}")
        
        # Check if match found
        if match_found:
            print()
            print(f"🎉 SUCCESS! Passphrase found: '{passphrase}'")
            print(f"🔧 Method: {matching_method}")
            print(f"📍 Generated address: {matching_address}")
            print(f"🎯 Target address:    {target_address}")
            print(f"✅ Match confirmed!")
            
            # Final verification
            print()
            print("🔍 Final verification:")
            verify_results = test_all_methods(mnemonic, passphrase, target_address)
            for method_key, result in verify_results.items():
                if result["matches"]:
                    print(f"   Method: {result['name']}")
                    print(f"   Passphrase: '{passphrase}'")
                    print(f"   Address: {result['address']}")
                    print(f"   Match: ✅ YES")
                    break
            return
    
    print()
    print("❌ Brute force completed. No matching passphrase found.")
    print()
    print("💡 Troubleshooting tips:")
    print("   - Verify your SLIP-39 mnemonic is complete and correct")
    print("   - Check that TARGET_ADDRESS is the correct address")
    print("   - Try adding more passphrase components to WORDS")
    print("   - Consider trying different account indices")


if __name__ == "__main__":
    main()
