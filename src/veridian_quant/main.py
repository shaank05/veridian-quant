from src.veridian_quant.data.db_client import DatabaseClient

def main():
    print("🚀 Initializing Medallion Quant Platform...")
    
    db = DatabaseClient()
    
    # Test: Query the server for the current timestamp
    try:
        result = db.execute_query("SELECT NOW();")
        print(f"📡 Database Time: {result[0][0]}")
        print("🔗 Connection Successful!")
    except Exception as e:
        print(f"⚠️ Connection Failed. Is your SSH Tunnel open? Error: {e}")

if __name__ == "__main__":
    main()