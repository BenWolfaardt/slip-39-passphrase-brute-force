#!/usr/bin/env python3
"""
BIP-39 Passphrase Brute Force Tool

A tool for brute forcing BIP-39 passphrases using word combinations.
Works with Trezor and other BIP-39 compatible hardware wallets.
"""

import argparse
import itertools
import math
import os
from typing import List, Iterator, Optional

from dotenv import load_dotenv
from mnemonic import Mnemonic
from eth_account import Account
import hashlib

# Enable HD wallet features for eth_account
Account.enable_unaudited_hdwallet_features()


def generate_word_combinations(words: List[str]) -> Iterator[str]:
    """Generate all possible combinations of passphrase components without spaces."""
    for length in range(1, len(words) + 1):
        for combo in itertools.combinations(words, length):
            # Try different orders of the selected components
            for perm in itertools.permutations(combo):
                yield "".join(perm)  # Concatenate without spaces


def bip39_to_ethereum_address(mnemonic_words: str, passphrase: str = "", account_index: int = 0) -> str:
    """
    Convert BIP-39 mnemonic + passphrase to Ethereum address.
    
    Args:
        mnemonic_words: BIP-39 mnemonic phrase (12, 15, 18, 21, or 24 words)
        passphrase: BIP-39 passphrase (can be empty)
        account_index: Account index in derivation path (default 0)
    
    Returns:
        Ethereum address as string
    """
    # Create Mnemonic instance
    mnemo = Mnemonic("english")
    
    # Validate mnemonic
    if not mnemo.check(mnemonic_words):
        raise ValueError("Invalid BIP-39 mnemonic")
    
    # Create account from seed using standard Ethereum derivation path
    # m/44'/60'/0'/0/{account_index}
    account = Account.from_mnemonic(mnemonic_words, passphrase=passphrase, account_path=f"m/44'/60'/0'/0/{account_index}")
    
    return account.address


def brute_force_bip39_passphrase(mnemonic: str, words: List[str], target_address: str, 
                                account_index: int = 0) -> Optional[str]:
    """
    Brute force BIP-39 passphrase using word combinations.
    
    Args:
        mnemonic: BIP-39 mnemonic phrase
        words: List of words to use for passphrase combinations
        target_address: The Ethereum address we're trying to match
        account_index: Account index in derivation path
        
    Returns:
        The successful passphrase if found, None otherwise
    """
    print(f"Starting BIP-39 passphrase brute force attack...")
    print(f"Using {len(words)} components: {', '.join(words)}")
    print(f"Target address: {target_address}")
    print(f"Account index: {account_index}")
    
    # Normalize target address
    target_address = target_address.lower().strip()
    if not target_address.startswith('0x'):
        target_address = '0x' + target_address
    
    # First, try empty passphrase (most common case)
    print("\nTesting empty passphrase first...")
    try:
        address = bip39_to_ethereum_address(mnemonic, "", account_index)
        print(f"Empty passphrase generates: {address}")
        if address.lower() == target_address.lower():
            print("✅ SUCCESS! Empty passphrase matches target address!")
            return ""
    except Exception as e:
        print(f"Error with empty passphrase: {e}")
    
    print("Empty passphrase doesn't match, trying component combinations...")
    
    # Calculate total combinations
    total_combinations = 0
    for r in range(1, len(words) + 1):
        combinations = math.comb(len(words), r)
        permutations_per_combo = math.factorial(r)
        total_combinations += combinations * permutations_per_combo
    
    print(f"Total combinations to try: {total_combinations:,}")
    
    attempt = 0
    for passphrase in generate_word_combinations(words):
        attempt += 1
        
        if attempt % 10 == 0:  # Show more frequent updates
            print(f"Attempt {attempt:,}: '{passphrase}'")
        elif attempt <= 10:  # Show first 10 attempts
            print(f"Attempt {attempt:,}: '{passphrase}'")
        
        try:
            address = bip39_to_ethereum_address(mnemonic, passphrase, account_index)
            
            if address.lower() == target_address.lower():
                print(f"\n✅ SUCCESS! Passphrase found: '{passphrase}'")
                print(f"Generated address: {address}")
                print(f"Target address:    {target_address}")
                return passphrase
                
        except Exception as e:
            print(f"Error with passphrase '{passphrase}': {e}")
            continue
    
    print("Brute force completed. Passphrase not found.")
    return None


def load_mnemonic_from_env() -> Optional[str]:
    """Load BIP-39 mnemonic from environment variable."""
    mnemonic = os.getenv('MNEMONIC', '').strip()
    return mnemonic if mnemonic else None


def load_words_from_env() -> List[str]:
    """Load passphrase components from environment variable."""
    words_env = os.getenv('WORDS', '').strip()
    if not words_env:
        return []
    
    # Support both comma and space separated
    if ',' in words_env:
        words = [w.strip() for w in words_env.split(',') if w.strip()]
    else:
        words = words_env.split()
    
    return words


def load_target_address_from_env() -> Optional[str]:
    """Load target Ethereum address from environment variable."""
    address = os.getenv('TARGET_ADDRESS', '').strip()
    return address if address else None


def validate_ethereum_address(address: str) -> bool:
    """Basic validation for Ethereum address format."""
    if not address:
        return False
    
    # Remove 0x prefix if present
    if address.startswith('0x'):
        address = address[2:]
    
    # Check if it's 40 hex characters
    if len(address) != 40:
        return False
    
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="BIP-39 Passphrase Brute Force Tool")
    parser.add_argument("--mnemonic", help="BIP-39 mnemonic phrase (overrides .env file)")
    parser.add_argument("--words", nargs="*", help="Passphrase components to use for combinations (overrides .env file)")
    parser.add_argument("--target-address", help="Target Ethereum address to match (overrides .env file)")
    parser.add_argument("--account-index", type=int, default=0, help="Account index in derivation path (default: 0)")
    
    args = parser.parse_args()
    
    # Load mnemonic from command line or .env file
    if args.mnemonic:
        mnemonic = args.mnemonic
    else:
        mnemonic = load_mnemonic_from_env()
    
    if not mnemonic:
        print("Error: No BIP-39 mnemonic found. Please set MNEMONIC in .env file or provide --mnemonic argument.")
        return
    
    print(f"Loaded BIP-39 mnemonic: {mnemonic[:50]}..." if len(mnemonic) > 50 else f"Loaded BIP-39 mnemonic: {mnemonic}")
    
    # Validate mnemonic
    try:
        mnemo = Mnemonic("english")
        if not mnemo.check(mnemonic):
            print("Error: Invalid BIP-39 mnemonic phrase.")
            return
    except Exception as e:
        print(f"Error validating mnemonic: {e}")
        return
    
    # Load words from command line or .env file
    if args.words:
        words = args.words
    else:
        words = load_words_from_env()
    
    if not words:
        print("Error: No passphrase components found for brute force. Please set WORDS in .env file or provide --words argument.")
        return
    
    print(f"Loaded {len(words)} components for combinations: {', '.join(words)}")
    
    # Load target address from command line or .env file
    if args.target_address:
        target_address = args.target_address
    else:
        target_address = load_target_address_from_env()
    
    if not target_address:
        print("Error: No target address found. Please set TARGET_ADDRESS in .env file or provide --target-address argument.")
        return
    
    if not validate_ethereum_address(target_address):
        print(f"Error: Invalid Ethereum address format: {target_address}")
        return
    
    print(f"Target address: {target_address}")
    
    # Start brute force attack
    result = brute_force_bip39_passphrase(mnemonic, words, target_address, args.account_index)
    
    if result is not None:
        print(f"\n🎉 SUCCESS! The passphrase is: '{result}'")
        
        # Verify the result
        try:
            final_address = bip39_to_ethereum_address(mnemonic, result, args.account_index)
            print(f"Final verification:")
            print(f"  Mnemonic: {mnemonic[:50]}...")
            print(f"  Passphrase: '{result}'")
            print(f"  Account index: {args.account_index}")
            print(f"  Generated address: {final_address}")
            print(f"  Target address:    {target_address}")
            print(f"  Match: {'✅ YES' if final_address.lower() == target_address.lower() else '❌ NO'}")
                
        except Exception as e:
            print(f"Error during final verification: {e}")
    else:
        print("\n❌ Passphrase not found with the given parameters.")
        print("\nTips:")
        print("- Try different account indices (--account-index 1, 2, etc.)")
        print("- Check if your passphrase component list is complete")
        print("- Verify the target address is correct")
        print("- Consider that the passphrase might contain numbers, special characters, or different cases")


if __name__ == "__main__":
    main()
