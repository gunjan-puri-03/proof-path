"""
Database setup helper script.
Run this once with your PostgreSQL superuser credentials to create the
kyc_user and yottaflex_kyc database.

Usage:
    python scripts/setup_database.py --pg-user postgres --pg-password YOUR_PASSWORD
"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="YottaFlex KYC Database Setup")
    parser.add_argument("--pg-host", default="localhost")
    parser.add_argument("--pg-port", default="5432")
    parser.add_argument("--pg-user", default="postgres",
                        help="PostgreSQL superuser (to create DB and user)")
    parser.add_argument("--pg-password", required=True,
                        help="Password for the PostgreSQL superuser")
    parser.add_argument("--kyc-user", default="kyc_user")
    parser.add_argument("--kyc-password", default="kyc_password")
    parser.add_argument("--kyc-db", default="yottaflex_kyc")
    args = parser.parse_args()

    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

    print(f"Connecting to PostgreSQL at {args.pg_host}:{args.pg_port} as {args.pg_user}...")
    conn = psycopg2.connect(
        host=args.pg_host,
        port=args.pg_port,
        user=args.pg_user,
        password=args.pg_password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Create user
    cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname='{args.kyc_user}'")
    if cur.fetchone():
        print(f"  User '{args.kyc_user}' already exists.")
    else:
        cur.execute(f"CREATE USER {args.kyc_user} WITH PASSWORD '{args.kyc_password}'")
        print(f"  Created user '{args.kyc_user}'.")

    # Create database
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{args.kyc_db}'")
    if cur.fetchone():
        print(f"  Database '{args.kyc_db}' already exists.")
    else:
        cur.execute(f"CREATE DATABASE {args.kyc_db} OWNER {args.kyc_user}")
        print(f"  Created database '{args.kyc_db}'.")

    cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {args.kyc_db} TO {args.kyc_user}")
    print(f"  Granted privileges on '{args.kyc_db}' to '{args.kyc_user}'.")

    cur.close()
    conn.close()

    # Write .env file
    env_content = f"""# YottaFlex KYC - Environment Configuration
DATABASE_URL=postgresql://{args.kyc_user}:{args.kyc_password}@{args.pg_host}:{args.pg_port}/{args.kyc_db}
POSTGRES_HOST={args.pg_host}
POSTGRES_PORT={args.pg_port}
POSTGRES_DB={args.kyc_db}
POSTGRES_USER={args.kyc_user}
POSTGRES_PASSWORD={args.kyc_password}
APP_ENV=development
APP_DEBUG=true
GENERATOR_SEED=20261022
GENERATOR_MODE=full
"""
    with open(".env", "w") as f:
        f.write(env_content)
    print("  Written .env file.")

    print("\nDatabase setup complete!")
    print("Next steps:")
    print("  1. python -m alembic upgrade head")
    print("  2. python -m data_generator.generator --mode starter")
    print("  3. python -m pytest tests/ -v")
    print("  4. python -m uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
