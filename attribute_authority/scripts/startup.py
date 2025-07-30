import json
import os
from sqlalchemy.orm import Session

from ..models.user import User
from ..db.session import SessionLocal
from ..core.logging_config import logger
from ..db.session import get_db

def insert_user_from_config(config_path="../user_attributes_config.json", db: Session = next(get_db())):
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        print(f"Inserting user from config: {data}")
        # Check if user already exists
        user = db.query(User).filter_by(sub=data["sub"], iss=data["iss"]).first()
        if not user:
            user = User(
                sub=data["sub"],
                iss=data["iss"],
                entitlements=json.dumps(data["entitlements"])  # Serialize entitlements to JSON string
            )
            db.add(user)
            db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error inserting user from config: {e}")

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "../user_attributes_config.json")
    config_path = os.path.abspath(config_path)
    insert_user_from_config(config_path=config_path)
    logger.info("User insertion script executed successfully.")