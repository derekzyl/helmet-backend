from datetime import datetime, date

def sqlalchemy_obj_to_dict(obj):
    """
    The function `sqlalchemy_obj_to_dict` converts SQLAlchemy objects into dictionaries, handling
    various data types and structures.
    
    :param obj: The function `sqlalchemy_obj_to_dict` is designed to convert SQLAlchemy objects into
    dictionaries. It handles various scenarios such as handling None values, datetime objects, lists of
    objects, dictionaries containing SQLAlchemy objects, and single SQLAlchemy objects
    :return: The function `sqlalchemy_obj_to_dict` takes an SQLAlchemy object as input and converts it
    into a dictionary representation. The function handles various cases such as None values, datetime
    objects, lists of objects, dictionaries containing SQLAlchemy objects, and single SQLAlchemy
    objects.
    """
 
    # Handle None
    if obj is None:
        return None
        
    # Handle datetime objects
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
        
    # Handle list of objects
    if isinstance(obj, list):
        return [sqlalchemy_obj_to_dict(item) for item in obj]
        
    # Handle dictionary containing SQLAlchemy objects
    if isinstance(obj, dict):
        return {key: sqlalchemy_obj_to_dict(value) for key, value in obj.items()}
        
    # Handle single SQLAlchemy object
    if hasattr(obj, '_asdict'):
        return sqlalchemy_obj_to_dict(obj._asdict())
    elif hasattr(obj, '__dict__'):
        data = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):  # Skip SQLAlchemy internal attributes
                data[key] = sqlalchemy_obj_to_dict(value)
        return data
        
    # Return primitive types as-is
    return obj