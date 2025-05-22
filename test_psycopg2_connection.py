import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Assumes .env is in the same directory as this script or in the project root
# if the script is run from the project root.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(dotenv_path):
    # Fallback to project root if .env not next to script
    project_root_for_env = os.path.dirname(os.path.abspath(__file__))
    # If script is in a subdir like /scripts, this might need adjustment
    # For a script in the root, this is fine.
    # Assuming a flat structure or .env at the same level for simplicity in a test script.
    # If running from project root, load_dotenv() without path might work if .env is in root.
    load_dotenv() 
else:
    load_dotenv(dotenv_path)

print("Attempting to connect to PostgreSQL using psycopg2...")

try:
    db_user = os.getenv("SUPABASE_DB_USER")
    db_password = os.getenv("SUPABASE_DB_PASSWORD")
    db_host = os.getenv("SUPABASE_DB_HOST")
    db_name = os.getenv("SUPABASE_DB_NAME", "postgres")
    db_port = os.getenv("SUPABASE_DB_PORT", "5432")

    if not all([db_user, db_password, db_host, db_name, db_port]):
        missing_vars = [
            var_name for var_name, var_val in [
                ("SUPABASE_DB_USER", db_user),
                ("SUPABASE_DB_PASSWORD", db_password),
                ("SUPABASE_DB_HOST", db_host),
                ("SUPABASE_DB_NAME", db_name),
                ("SUPABASE_DB_PORT", db_port)
            ] if not var_val
        ]
        print(f"Error: Missing one or more database connection environment variables: {', '.join(missing_vars)}")
    else:
        # Constructing DSN for psycopg2
        # Example: "postgresql://user:password@host:port/dbname?connect_timeout=10&sslmode=require"
        # psycopg2 can take this directly, or a space-separated string:
        # "dbname='x' user='y' host='z' password='p' port='123' connect_timeout=10 sslmode='require'"
        
        dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?connect_timeout=10&sslmode=require"
        print(f"Connecting with DSN: postgresql://{db_user}:[REDACTED]@{db_host}:{db_port}/{db_name}?connect_timeout=10&sslmode=require")

        conn = None
        try:
            conn = psycopg2.connect(dsn)
            cur = conn.cursor()
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            print(f"Successfully connected to PostgreSQL! Server version: {db_version[0]}")
            cur.close()
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL using psycopg2: {e}")
        finally:
            if conn:
                conn.close()
                print("Connection closed.")

except Exception as e:
    print(f"An unexpected error occurred: {e}") 