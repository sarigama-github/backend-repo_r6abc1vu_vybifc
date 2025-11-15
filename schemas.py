"""
Database Schemas for Gamified Carbon Tracker

Each Pydantic model corresponds to a MongoDB collection.
Class name lowercased is used as the collection name.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

class Player(BaseModel):
    username: str = Field(..., description="Unique handle for the user")
    avatar: Optional[str] = Field(None, description="Avatar URL")

class Activity(BaseModel):
    username: str = Field(..., description="Username who performed the activity")
    activity_type: Literal[
        "public_transport",
        "vegan_meal",
        "recycling",
        "bike_ride",
        "refill",
        "thrift",
        "tree_planting"
    ] = Field(..., description="Type of eco-friendly activity")
    quantity: int = Field(1, ge=1, description="How many units (rides/meals/items)")
    points: Optional[int] = Field(None, ge=0, description="Points awarded for this activity")
    notes: Optional[str] = Field(None, description="Optional note or proof link")

class Badge(BaseModel):
    username: str = Field(..., description="Username who earned the badge")
    badge_key: str = Field(..., description="Stable key for badge kind")
    name: str = Field(..., description="Badge title")
    description: str = Field(..., description="What this badge represents")
    icon: str = Field("medal", description="Icon name for the badge")
