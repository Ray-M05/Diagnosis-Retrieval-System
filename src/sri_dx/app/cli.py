import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="SRI-DX: Diagnosis Retrieval System CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Index command
    subparsers.add_parser("index", help="Build search indexes from data")
    
    # Run command
    subparsers.add_parser("run", help="Run the diagnostic retrieval flow (CLI mode)")

    args = parser.parse_args()

    if args.command == "index":
        print("Indexing process started...")
        # TODO: Implement indexing logic
    elif args.command == "run":
        print("Running retrieval flow...")
        # TODO: Implement run logic
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
