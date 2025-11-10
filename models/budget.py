from pydantic import BaseModel, Field
from typing import Dict

class Budget(BaseModel):
    """Schema for managing daily and weekly budgets and user preferences."""
    
    # Stores the daily budget limit for various categories. Default is an empty dictionary.
    daily_limits: Dict[str, float] = Field(default_factory=dict, 
                                          description="Category: Daily limit in currency.")
    
    # Stores the weekly budget limit for various categories. Default is an empty dictionary.
    weekly_limits: Dict[str, float] = Field(default_factory=dict, 
                                           description="Category: Weekly limit in currency.")
    
    # Stores the user's name for personalized greetings.
    user_name: str = "Kean"
    
    # Stores the primary currency symbol for display.
    currency_symbol: str = "₱"