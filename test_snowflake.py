"""Quick connectivity + key-pair auth check for Snowflake."""
import os
from pathlib import Path

from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
import snowflake.connector

load_dotenv()


def load_private_key() -> bytes:
    key_path = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"])
    with key_path.open("rb") as f:
        p_key = serialization.load_pem_private_key(f.read(), password=None)
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def main() -> None:
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=load_private_key(),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
        role=os.environ.get("SNOWFLAKE_ROLE"),
    )
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT CURRENT_USER(), CURRENT_ACCOUNT(), "
            "CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_ROLE()"
        )
        user, account, wh, db, role = cur.fetchone()
        print("Connected to Snowflake")
        print(f"  user      : {user}")
        print(f"  account   : {account}")
        print(f"  warehouse : {wh}")
        print(f"  database  : {db}")
        print(f"  role      : {role}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
