from dataclasses import dataclass


@dataclass
class Subscription:
    id: int
    business_id: int
    package_id: int
    start_date: str  # Use datetime.date or datetime.datetime in Python
    trial_end_date: str  # Use datetime.date or datetime.datetime in Python
    end_date: str  # Use datetime.date or datetime.datetime in Python
    package_price: float
    package_details: str
    created_id: int
    paid_via: str # = None
    payment_transaction_id: str # = None
    status: str # = 'waiting'  # 'approved', 'waiting', or 'declined'
    deleted_at: str # = None
    created_at: str # = None
    updated_at: str # = None
