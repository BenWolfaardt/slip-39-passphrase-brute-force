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


def slip39_seed_to_eth_address(master_secret: bytes, passphrase: str = "", account_index: int = 0) -> str:
    """Convert SLIP-39 master secret + passphrase to Ethereum address using proper SLIP-39 derivation."""
    try:
        # Use slip39.account for proper derivation - this matches hardware wallets!
        if passphrase:
            eth_account = slip39.account(master_secret, 'ETH', f"m/44'/60'/0'/0/{account_index}", passphrase=passphrase)
        else:
            eth_account = slip39.account(master_secret, 'ETH', f"m/44'/60'/0'/0/{account_index}")
        
        return eth_account.address
    except Exception as e:
        raise ValueError(f"Error generating address: {e}")


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
    
    # Step 2: Test empty passphrase first
    print("🔐 Step 2: Testing empty passphrase...")
    try:
        address = slip39_seed_to_eth_address(master_secret, "", 0)
        print(f"📍 Empty passphrase → {address}")
        if address.lower() == target_address.lower():
            print(f"🎉 SUCCESS! Empty passphrase matches target!")
            return
    except Exception as e:
        print(f"⚠️  Error with empty passphrase: {e}")
    
    print("❌ Empty passphrase doesn't match")
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
        
        try:
            address = slip39_seed_to_eth_address(master_secret, passphrase, 0)
            
            # Show progress
            if attempt <= 5 or attempt % 10 == 0:
                print(f"🔄 Attempt {attempt}: '{passphrase}' → {address}")
            
            # Check if match
            if address.lower() == target_address.lower():
                print()
                print(f"🎉 SUCCESS! Passphrase found: '{passphrase}'")
                print(f"📍 Generated address: {address}")
                print(f"🎯 Target address:    {target_address}")
                print(f"✅ Match confirmed!")
                
                # Final verification
                print()
                print("🔍 Final verification:")
                verify_address = slip39_seed_to_eth_address(master_secret, passphrase, 0)
                print(f"   Passphrase: '{passphrase}'")
                print(f"   Address: {verify_address}")
                print(f"   Match: {'✅ YES' if verify_address.lower() == target_address.lower() else '❌ NO'}")
                return
                
        except Exception as e:
            if attempt <= 5:
                print(f"⚠️  Attempt {attempt}: '{passphrase}' → Error: {e}")
    
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
