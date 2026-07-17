#!/usr/bin/env python3
"""
Master test runner for JARVIS-MK2.
Runs all test suites and reports overall status.
"""

import subprocess
import sys
import os

def run_test_script(script_name):
    """Run a test script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {script_name}")
    print('='*60)

    try:
        result = subprocess.run(
            [sys.executable, f"tests/{script_name}"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=30
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"ERROR: {script_name} timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"ERROR running {script_name}: {e}")
        return False

def main():
    """Run all test suites."""
    print("🧪 JARVIS-MK2 Comprehensive Test Suite")
    print("=" * 60)

    test_scripts = [
        "test_brain.py",
        "test_integration.py",
        "test_executor.py",
        "test_ai.py"
    ]

    results = []
    for script in test_scripts:
        success = run_test_script(script)
        results.append((script, success))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)

    all_passed = True
    for script, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {script}")
        if not success:
            all_passed = False

    print('-'*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! System is ready.")
        return 0
    else:
        print("💥 SOME TESTS FAILED! Please review output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())