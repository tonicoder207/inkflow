import os
import secrets
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_key(license_type="standard", max_devices=1, notes=""):
    # Generate a professional looking key: INK-XXXX-XXXX
    key = f"INK-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    
    data = {
        "license_key": key,
        "license_type": license_type,
        "max_devices": max_devices,
        "notes": notes,
        "status": "active"
    }
    
    try:
        res = supabase.table("licenses").insert(data).execute()
        if res.data:
            print("\n" + "="*40)
            print("🚀 LICENSE KEY GENERATED SUCCESSFULLY!")
            print("="*40)
            print(f"Key:         {key}")
            print(f"Type:        {license_type}")
            print(f"Max Devices: {max_devices}")
            print(f"Notes:       {notes}")
            print("="*40)
            print("\nYou can now send this key to your friend!")
        else:
            print("Error: Could not insert license into database.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print("--- InkFlow License Generator ---")
    type_choice = input("License Type (standard/premium) [standard]: ") or "standard"
    devices = input("Max Devices [1]: ") or "1"
    notes = input("Friend's Name / Notes: ") or "Friend"
    
    generate_key(type_choice, int(devices), notes)
