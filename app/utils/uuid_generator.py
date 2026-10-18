import random
import string
import uuid
from datetime import datetime
from enum import Enum
from typing import Literal

# initializing size of string
N: Literal[10] = 10



def id_gen() -> str:
    """
    Generates a unique identifier string.
    The identifier is composed of three parts:
    1. A timestamp of the current UTC time in the format YYYYMMDDHHMMSS.
    2. A random string of lowercase letters and digits.
    3. A UUID (Universally Unique Identifier) without dashes.
    Returns:
        str: The generated unique identifier.
    """

    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=N))
    
    # Get current timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    
    # Generate UUID without dashes
    uuid_str = str(uuid.uuid4()).replace('-', '')
    
    # Combine all parts
    return f"{timestamp}{random_str}{uuid_str}"


class RefType(Enum):
    STOCK_ADJUSTMENT = "SA"
    STOCK_ADJUSTMENT_RETURN = "SARN"
    STOCK_ADJUSTMENT_RECEIPT = "SART"
    STOCK_ADJUSTMENT_ISSUE = "SAIS"
    STOCK_TRANSFER = "ST"

def generate_reference_number(ref_type: RefType=RefType.STOCK_ADJUSTMENT) -> str:
    """
    Generates a reference number.
    The reference number is composed of three parts:
    1. A timestamp of the current UTC time in the format YYYYMMDDHHMMSS.
    2. A random string of lowercase letters and digits.
    3. A UUID (Universally Unique Identifier) without dashes.
    Returns:
    """
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=N))
    return f"{ref_type.value}-{random_str}"

def generate_random_password() -> str:
    """
    Generates a random password.
    Returns:
        str: The generated random password.
    """
    return "".join(random.choices(string.ascii_letters + string.digits, k=8))