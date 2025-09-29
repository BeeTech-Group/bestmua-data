#!/usr/bin/env python3
"""Test runner script for bestmua-data project."""

import sys
import unittest
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_tests(test_pattern=None, verbosity=2):
    """Run tests with optional pattern filtering."""
    # Discover tests
    loader = unittest.TestLoader()
    
    if test_pattern:
        # Run specific test pattern
        suite = loader.loadTestsFromName(test_pattern)
    else:
        # Discover all tests
        test_dir = Path(__file__).parent
        suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return success/failure
    return len(result.failures) == 0 and len(result.errors) == 0

def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run bestmua-data tests')
    parser.add_argument('pattern', nargs='?', help='Test pattern to run (e.g., test_normalizer.TestDataNormalizer.test_normalize_text)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet output')
    
    args = parser.parse_args()
    
    # Set verbosity
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity = 1
    
    print("Running bestmua-data tests...")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print("-" * 50)
    
    # Run tests
    success = run_tests(args.pattern, verbosity)
    
    if success:
        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)
        sys.exit(0)
    else:
        print("\n" + "=" * 50)
        print("SOME TESTS FAILED!")
        print("=" * 50)
        sys.exit(1)

if __name__ == '__main__':
    main()