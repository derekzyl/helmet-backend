from dataclasses import dataclass


@dataclass
class Package:
    id: int
    name: str
    description: str
    location_count: int  # No. of Business Locations, 0 = infinite option
    user_count: int
    product_count: int
    invoice_count: int
    interval: str  # 'days', 'months', or 'years'
    interval_count: int
    trial_days: int
    price: float
    created_by: int
    sort_order: int 
    is_active: bool 
    deleted_at: str 
    created_at: str 
    updated_at: str 
    
