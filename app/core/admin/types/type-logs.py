from dataclasses import dataclass
from typing import Optional


@dataclass
class SuperadminCommunicatorLog:
    id: int
  
    subject: Optional[str]
    message: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

# # Example instantiation
# log_entry = SuperadminCommunicatorLog(
#     id=1,
#     business_ids="1,2,3",
#     subject="Example Subject",
#     message="This is an example message.",
#     created_at="2024-05-03 10:00:00",
#     updated_at="2024-05-03 10:05:00"
# )
