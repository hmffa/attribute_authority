import json
import os
from sqlalchemy.orm import Session
import datetime

from ..models.user import User
from ..models.attribute import UserAttribute
from ..core.logging_config import logger
from ..db.session import get_db

def insert_user_from_config(config_path=None, db: Session = next(get_db())):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "../user_attributes_config.json")
        config_path = os.path.abspath(config_path)
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(config_path, "r") as f:
            users = json.load(f)
        print(f"Inserting user from config: {users}")
        for data in users:
            # Check if user already exists
            user = db.query(User).filter_by(sub=data["sub"], iss=data["iss"]).first()
            if not user:
                user = User(
                    sub=data["sub"],
                    iss=data["iss"],
                    created_at=now
                )
                db.add(user)
                db.flush()
            else:
                logger.info(f"User with sub {data['sub']} already exists, skipping creation.")
    
            for key, values in data.items():
                if key in ["sub", "iss"]:
                    continue
                if isinstance(values, list):
                    for value in values:
                        attribute = UserAttribute(
                            user_id=user.id,
                            key=key,
                            value=str(value),
                            created_at=now
                        )
                        db.add(attribute)
                else:
                    attribute = UserAttribute(
                        user_id=user.id,
                        key=key,
                        value=str(values),
                        created_at=now
                    )
                    db.add(attribute)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error inserting user from config: {e}")

if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "../user_attributes_config.json")
    config_path = os.path.abspath(config_path)
    insert_user_from_config(config_path=config_path)
    logger.info("User insertion script executed successfully.")