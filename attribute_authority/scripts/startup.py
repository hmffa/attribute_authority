import json
import os
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.user import User
from ..models.attribute import Attribute
from ..models.user_attribute_value import UserAttributeValue
from ..core.logging_config import logger
from ..db.session import get_db

def insert_user_from_config(config_path=None, db: Session = next(get_db())):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "../user_attributes_config.json")
        config_path = os.path.abspath(config_path)
    
    try:
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}")
            return

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        with open(config_path, "r") as f:
            users_data = json.load(f)
            
        logger.info(f"Loading mock data from {config_path}")

        for data in users_data:
            # 1. Get or Create User
            user = db.query(User).filter_by(sub=data["sub"], iss=data["iss"]).first()
            if not user:
                user = User(
                    sub=data["sub"],
                    iss=data["iss"],
                    name=data.get("name"), # If present in JSON
                    email=data.get("email"), # If present in JSON
                    created_at=now
                )
                db.add(user)
                db.flush() # Flush to get user.id
                logger.info(f"Created user {data['sub']}")
            else:
                logger.info(f"User {data['sub']} already exists.")
    
            # 2. Process Attributes
            for key, values in data.items():
                # Skip reserved user fields
                if key in ["sub", "iss", "name", "email"]:
                    continue
                
                # Determine if multi-value based on JSON structure
                is_list = isinstance(values, list)
                raw_values = values if is_list else [values]
                
                # 3. Get or Create Attribute Definition (Schema)
                attr_def = db.query(Attribute).filter_by(name=key).first()
                if not attr_def:
                    attr_def = Attribute(
                        name=key,
                        is_multivalue=True, # Default to true for mock data flexbility
                        description=f"Auto-generated from startup script",
                        enabled=True,
                        created_at=now
                    )
                    db.add(attr_def)
                    db.flush() # Flush to get attr_def.id
                    logger.info(f"Created attribute definition '{key}'")

                # 4. Insert User Attribute Values
                for val in raw_values:
                    str_val = str(val)
                    
                    # Check if value exists to avoid duplicates
                    exists = db.query(UserAttributeValue).filter_by(
                        user_id=user.id,
                        attribute_id=attr_def.id,
                        value=str_val
                    ).first()
                    
                    if not exists:
                        user_attr = UserAttributeValue(
                            user_id=user.id,
                            attribute_id=attr_def.id,
                            value=str_val,
                            created_at=now,
                            updated_at=now
                        )
                        db.add(user_attr)
        
        db.commit()
        logger.info("Mock data insertion complete.")
        
    except Exception as e:
        logger.error(f"Error inserting user from config: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    insert_user_from_config()