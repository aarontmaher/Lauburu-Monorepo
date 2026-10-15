import pytest
import sys

def main():
    print("Running all tiers...")
    sys.exit(pytest.main(["-v", "tests/"]))

if __name__ == "__main__":
    main()
