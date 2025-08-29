# test_env.py
from dotenv import load_dotenv
import os

load_dotenv()

print("=== Testing Environment Variables ===")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_ANON_KEY: {'✅ Set' if os.getenv('SUPABASE_ANON_KEY') else '❌ Not Set'}")
print(f"Database user: {os.getenv('user')}")
print(f"Database host: {os.getenv('host')}")
print("====================================")

if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
    print("✅ All required environment variables are set!")
else:
    print("❌ Missing required environment variables!")
