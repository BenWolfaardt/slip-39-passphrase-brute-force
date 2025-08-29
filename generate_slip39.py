#!/usr/bin/env python3
"""
SLIP-39 Mnemonic Generator REPL

Interactive tool for generating random SLIP-39 mnemonics for testing purposes.
"""

import secrets
import slip39
from typing import Dict, Tuple, Optional, Any


def generate_random_slip39(
    name: str = "Test",
    group_threshold: int = 2,
    groups: Optional[Dict[str, Tuple[int, int]]] = None,
    passphrase: str = "",
    strength: int = 128
) -> Any:
    """
    Generate random SLIP-39 mnemonics.
    
    Args:
        name: Name for the wallet
        group_threshold: Number of groups required for recovery
        groups: Dict of group_name: (required, total) for each group
        passphrase: Optional passphrase for additional security
        strength: Seed strength in bits (128, 256, or 512)
    
    Returns:
        SLIP-39 Details object containing all the mnemonics
    """
    if groups is None:
        # Default groups: Mine (1/1), Family (2/3), Friends (3/5)
        groups = {
            "Mine": (1, 1),
            "Family": (2, 3), 
            "Friends": (3, 5)
        }
    
    # Generate random master secret
    master_secret = secrets.token_bytes(strength // 8)
    
    # Create SLIP-39 mnemonics
    details = slip39.create(
        name=name,
        group_threshold=group_threshold,
        groups=groups,
        master_secret=master_secret,
        passphrase=passphrase.encode('utf-8') if passphrase else b"",
        strength=strength
    )
    
    return details


def display_slip39_details(details: Any):
    """Display the SLIP-39 details in a nice format."""
    print(f"\n=== SLIP-39 Wallet: {details.name} ===")
    print(f"Group threshold: {details.group_threshold} of {len(details.groups)} groups required")
    print(f"Using BIP-39: {details.using_bip39}")
    
    print("\n--- Mnemonic Groups ---")
    for group_name, (required, mnemonics) in details.groups.items():
        print(f"\n{group_name} Group ({required}/{len(mnemonics)} required):")
        for i, mnemonic in enumerate(mnemonics, 1):
            print(f"  {i}: {mnemonic}")
    
    print("\n--- Sample Accounts ---")
    if details.accounts:
        for i, account_group in enumerate(details.accounts):
            print(f"Account Group {i+1}:")
            for account in account_group:
                print(f"  {account.crypto} {account.path}: {account.address}")


def create_test_mnemonics_with_passphrase():
    """Create test SLIP-39 mnemonics with a known passphrase for testing."""
    print("\n🔧 Creating test SLIP-39 mnemonics with known passphrase...")
    
    # Create simple 2-of-3 setup with known passphrase
    details = generate_random_slip39(
        name="Test-Passphrase",
        group_threshold=2,
        groups={
            "Group1": (1, 1),
            "Group2": (1, 1), 
            "Group3": (1, 1)
        },
        passphrase="test password 123",  # Known passphrase for testing
        strength=128
    )
    
    display_slip39_details(details)
    
    print(f"\n📋 Test Configuration:")
    print(f"   Passphrase: 'test password 123'")
    print(f"   Words to try: ['test', 'password', '123']")
    print(f"   Any 2 of the 3 mnemonics above should work for recovery")
    
    # Show first two mnemonics for testing
    mnemonics = []
    for group_name, (required, group_mnemonics) in details.groups.items():
        mnemonics.extend(group_mnemonics)
    
    print(f"\n📝 Use these two mnemonics for testing:")
    print(f"   Mnemonic 1: {mnemonics[0]}")
    print(f"   Mnemonic 2: {mnemonics[1]}")
    
    return details


def interactive_repl():
    """Interactive REPL for generating SLIP-39 mnemonics."""
    print("🔐 SLIP-39 Mnemonic Generator REPL")
    print("=" * 40)
    print("Commands:")
    print("  generate - Generate new SLIP-39 mnemonics")
    print("  example - Generate example mnemonics")
    print("  test - Generate test mnemonics with known passphrase")
    print("  simple - Generate simple 2-of-3 mnemonics")
    print("  help - Show this help message")
    print("  quit - Exit the REPL")
    print()
    
    while True:
        try:
            command = input("slip39> ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
                
            elif command in ['help', 'h']:
                print("\nAvailable commands:")
                print("  generate - Generate new SLIP-39 mnemonics with custom parameters")
                print("  example - Generate example mnemonics with default settings")
                print("  test - Generate test mnemonics with known passphrase for brute force testing")
                print("  simple - Generate simple 2-of-3 mnemonics")
                print("  help - Show this help message")
                print("  quit - Exit the REPL")
                
            elif command == 'test':
                create_test_mnemonics_with_passphrase()
                
            elif command == 'example':
                print("\nGenerating example SLIP-39 mnemonics...")
                details = generate_random_slip39(
                    name="Example",
                    group_threshold=2,
                    groups={
                        "Personal": (1, 1),
                        "Family": (2, 3),
                        "Friends": (2, 4)
                    },
                    passphrase="example123",
                    strength=128
                )
                display_slip39_details(details)
                
            elif command == 'simple':
                print("\nGenerating simple 2-of-3 SLIP-39 mnemonics...")
                details = generate_random_slip39(
                    name="Simple",
                    group_threshold=2,
                    groups={
                        "Group1": (1, 1),
                        "Group2": (1, 1),
                        "Group3": (1, 1)
                    },
                    passphrase="",
                    strength=128
                )
                display_slip39_details(details)
                
            elif command == 'generate':
                print("\n--- Custom SLIP-39 Generation ---")
                
                name = input("Wallet name [Test]: ").strip() or "Test"
                
                print("\nGroup Configuration:")
                print("Enter groups in format 'name:required:total' (e.g., 'Family:2:3')")
                print("Press enter with empty line when done")
                
                groups = {}
                while True:
                    group_input = input(f"Group {len(groups)+1}: ").strip()
                    if not group_input:
                        break
                    
                    try:
                        parts = group_input.split(':')
                        if len(parts) != 3:
                            raise ValueError("Invalid format")
                        
                        group_name, required, total = parts
                        required, total = int(required), int(total)
                        
                        if required > total or required < 1 or total < 1:
                            raise ValueError("Invalid required/total values")
                        
                        groups[group_name.strip()] = (required, total)
                        print(f"  Added group '{group_name}': {required} of {total} required")
                        
                    except ValueError as e:
                        print(f"  Error: Invalid format. Use 'name:required:total'")
                        continue
                
                if not groups:
                    print("No groups specified, using default groups")
                    groups = {"Group1": (1, 1), "Group2": (1, 1), "Group3": (1, 1)}
                
                try:
                    group_threshold = int(input(f"Group threshold [2]: ").strip() or "2")
                    if group_threshold > len(groups) or group_threshold < 1:
                        group_threshold = min(2, len(groups))
                        print(f"  Adjusted group threshold to {group_threshold}")
                except ValueError:
                    group_threshold = 2
                
                passphrase = input("Passphrase (optional): ").strip()
                
                try:
                    strength = int(input("Strength in bits [128]: ").strip() or "128")
                    if strength not in [128, 256, 512]:
                        strength = 128
                        print("  Using default strength 128 bits")
                except ValueError:
                    strength = 128
                
                print("\nGenerating SLIP-39 mnemonics...")
                details = generate_random_slip39(
                    name=name,
                    group_threshold=group_threshold,
                    groups=groups,
                    passphrase=passphrase,
                    strength=strength
                )
                display_slip39_details(details)
                
            elif command == '':
                continue
                
            else:
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except EOFError:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    interactive_repl()
