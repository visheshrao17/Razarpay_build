import sys
import httpx
import argparse

API_URL = "http://localhost:8000/api"

def main():
    parser = argparse.ArgumentParser(description="Upload CSV sources to a SettleSense Run")
    parser.add_argument("run_id", help="The ID of the run (create one in the UI first)")
    parser.add_argument("--settlement", required=True, help="Path to settlement CSV")
    parser.add_argument("--bank", required=True, help="Path to bank_statement CSV")
    parser.add_argument("--ledger", required=True, help="Path to internal_ledger CSV")
    parser.add_argument("--payment", required=False, help="Path to payment CSV (optional)")
    
    args = parser.parse_args()

    # 1. Login to get token
    print("Logging in...")
    login_resp = httpx.post(f"{API_URL}/auth/login", data={
        "username": "operator@settlesense.dev",
        "password": "operator123"
    })
    
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        sys.exit(1)
        
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload files
    sources = {
        "settlement": args.settlement,
        "bank_statement": args.bank,
        "internal_ledger": args.ledger,
    }
    if args.payment:
        sources["payment"] = args.payment

    for source_type, filepath in sources.items():
        print(f"Uploading {source_type} from {filepath}...")
        with open(filepath, "rb") as f:
            files = {"file": (filepath.split("/")[-1], f, "text/csv")}
            data = {"source_type": source_type}
            
            resp = httpx.post(f"{API_URL}/runs/{args.run_id}/sources", 
                              headers=headers, data=data, files=files)
            
            if resp.status_code == 200:
                print(f"  -> Success: {resp.json()['valid_rows']} valid rows loaded.")
            else:
                print(f"  -> Failed: {resp.text}")

    print("\nAll files uploaded! You can now click 'Execute' in the UI for this run.")

if __name__ == "__main__":
    main()
