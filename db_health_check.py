# db_health_check.py
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 50)
print("🔍 DATABASE HEALTH CHECK")
print("=" * 50)

def test_environment_variables():
    """Test if environment variables are loaded correctly"""
    print("\n📋 ENVIRONMENT VARIABLES CHECK")
    print("-" * 30)
    
    # Supabase variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"SUPABASE_URL: {supabase_url}")
    print(f"SUPABASE_ANON_KEY: {'✅ Set (' + str(len(supabase_key)) + ' chars)' if supabase_key else '❌ Not Set'}")
    
    # PostgreSQL variables
    db_user = os.getenv("user")
    db_password = os.getenv("password")
    db_host = os.getenv("host")
    db_port = os.getenv("port", "5432")
    db_name = os.getenv("dbname")
    
    print(f"DB User: {db_user}")
    print(f"DB Password: {'✅ Set (' + str(len(db_password)) + ' chars)' if db_password else '❌ Not Set'}")
    print(f"DB Host: {db_host}")
    print(f"DB Port: {db_port}")
    print(f"DB Name: {db_name}")
    
    # Check URL format
    if supabase_url:
        if supabase_url.startswith('https://') and supabase_url.endswith('.supabase.co'):
            print("✅ Supabase URL format looks correct")
        else:
            print("❌ Supabase URL format is WRONG!")
            print("   Expected: https://your-project-ref.supabase.co")
            print(f"   Got: {supabase_url}")
            return False
    
    return all([supabase_url, supabase_key, db_user, db_password, db_host, db_name])

def test_postgresql_connection():
    """Test PostgreSQL database connection"""
    print("\n🐘 POSTGRESQL CONNECTION TEST")
    print("-" * 30)
    
    try:
        import psycopg2
        
        # Connection parameters
        db_params = {
            "user": os.getenv("user"),
            "password": os.getenv("password"),
            "host": os.getenv("host"),
            "port": os.getenv("port", "5432"),
            "dbname": os.getenv("dbname")
        }
        
        print("Attempting connection...")
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        
        # Test query
        cursor.execute("SELECT NOW(), version();")
        now, version = cursor.fetchone()
        
        print(f"✅ PostgreSQL Connection SUCCESSFUL!")
        print(f"   Server Time: {now}")
        print(f"   Version: {version.split(',')[0]}")
        
        cursor.close()
        connection.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL Connection FAILED: {str(e)}")
        return False

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    print("\n⚡ SQLALCHEMY CONNECTION TEST")
    print("-" * 30)
    
    try:
        from sqlalchemy import create_engine, text
        
        # Build connection URL
        db_url = f"postgresql://{os.getenv('user')}:{os.getenv('password')}@{os.getenv('host')}:{os.getenv('port', '5432')}/{os.getenv('dbname')}"
        
        print("Creating SQLAlchemy engine...")
        engine = create_engine(db_url, pool_pre_ping=True)
        
        print("Testing connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 'SQLAlchemy works!' as message, NOW() as time;"))
            row = result.fetchone()
            
            print(f"✅ SQLAlchemy Connection SUCCESSFUL!")
            print(f"   Message: {row[0]}")
            print(f"   Time: {row[1]}")
            
        return True
        
    except ImportError:
        print("❌ SQLAlchemy not installed. Install with: pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ SQLAlchemy Connection FAILED: {str(e)}")
        return False

def test_supabase_client():
    """Test Supabase client creation"""
    print("\n🚀 SUPABASE CLIENT TEST")
    print("-" * 30)
    
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials")
            return False
        
        print("Creating Supabase client...")
        supabase = create_client(supabase_url, supabase_key)
        
        print("Testing Supabase connection...")
        # Try to list storage buckets as a test
        buckets = supabase.storage.list_buckets()
        
        print(f"✅ Supabase Client SUCCESSFUL!")
        print(f"   Storage Buckets: {len(buckets)} found")
        
        return True
        
    except ImportError:
        print("❌ Supabase SDK not installed. Install with: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Supabase Client FAILED: {str(e)}")
        return False

def main():
    """Run all health checks"""
    
    # Test 1: Environment Variables
    env_ok = test_environment_variables()
    
    # Test 2: PostgreSQL Connection  
    pg_ok = test_postgresql_connection()
    
    # Test 3: SQLAlchemy Connection
    sql_ok = test_sqlalchemy_connection()
    
    # Test 4: Supabase Client
    supabase_ok = test_supabase_client()
    
    # Final Summary
    print("\n" + "=" * 50)
    print("📊 HEALTH CHECK SUMMARY")
    print("=" * 50)
    
    print(f"Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"PostgreSQL Connection: {'✅ PASS' if pg_ok else '❌ FAIL'}")
    print(f"SQLAlchemy Connection: {'✅ PASS' if sql_ok else '❌ FAIL'}")
    print(f"Supabase Client: {'✅ PASS' if supabase_ok else '❌ FAIL'}")
    
    overall_health = all([env_ok, pg_ok, sql_ok, supabase_ok])
    
    print(f"\nOverall Status: {'🎉 ALL SYSTEMS GO!' if overall_health else '⚠️ ISSUES DETECTED'}")
    
    if not overall_health:
        print("\n🔧 Next Steps:")
        if not env_ok:
            print("1. Fix your .env file (see instructions below)")
        if not pg_ok:
            print("2. Check PostgreSQL credentials and network connectivity")
        if not sql_ok:
            print("3. Install SQLAlchemy: pip install sqlalchemy psycopg2-binary")
        if not supabase_ok:
            print("4. Fix Supabase URL and install SDK: pip install supabase")
    
    return overall_health

if __name__ == "__main__":
    main()
