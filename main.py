import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Activity, Player, Badge

app = FastAPI(title="GreenPoints API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POINTS_TABLE: Dict[str, int] = {
    "public_transport": 15,
    "vegan_meal": 10,
    "recycling": 8,
    "bike_ride": 12,
    "refill": 6,
    "thrift": 14,
    "tree_planting": 50,
}

class ActivityCreate(BaseModel):
    username: str
    activity_type: str
    quantity: int = 1
    notes: str | None = None

class Summary(BaseModel):
    username: str

@app.get("/")
def root():
    return {"message": "GreenPoints API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()
    except Exception as e:
        response["database"] = f"⚠️ {str(e)[:60]}"
    return response

@app.get("/api/leaderboard")
def leaderboard(limit: int = 10):
    pipeline = [
        {"$group": {"_id": "$username", "points": {"$sum": "$points"}}},
        {"$sort": {"points": -1}},
        {"$limit": limit},
    ]
    try:
        agg = list(db["activity"].aggregate(pipeline)) if db else []
        return [
            {"username": item.get("_id"), "points": int(item.get("points", 0))}
            for item in agg
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/activities")
def list_activities(username: str | None = None, limit: int = 50):
    filt = {"username": username} if username else {}
    docs = get_documents("activity", filt, limit) if db else []
    for d in docs:
        d["_id"] = str(d["_id"]) if isinstance(d.get("_id"), ObjectId) else d.get("_id")
    return docs

@app.post("/api/activities")
def log_activity(payload: ActivityCreate):
    if payload.activity_type not in POINTS_TABLE:
        raise HTTPException(status_code=400, detail="Unknown activity type")
    points_per = POINTS_TABLE[payload.activity_type]
    total_points = points_per * max(1, payload.quantity)

    activity = Activity(
        username=payload.username,
        activity_type=payload.activity_type, 
        quantity=max(1, payload.quantity),
        points=total_points,
        notes=payload.notes,
    )
    try:
        _id = create_document("activity", activity)
        # simple badge rules
        maybe_badges: list[dict[str, Any]] = []
        if payload.activity_type == "vegan_meal" and payload.quantity >= 3:
            maybe_badges.append({
                "badge_key": "plant_power",
                "name": "Plant Power",
                "description": "Logged 3+ vegan meals in one go!",
                "icon": "leaf"
            })
        if total_points >= 50:
            maybe_badges.append({
                "badge_key": "big_impact",
                "name": "Big Impact",
                "description": "Scored 50+ points from one action",
                "icon": "zap"
            })
        created_badges = []
        for b in maybe_badges:
            bdoc = Badge(username=payload.username, **b)
            bid = create_document("badge", bdoc)
            created_badges.append({"_id": bid, **b})
        return {"inserted_id": _id, "points": total_points, "badges": created_badges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/badges")
def get_badges(username: str | None = None):
    filt = {"username": username} if username else {}
    docs = get_documents("badge", filt, None) if db else []
    for d in docs:
        d["_id"] = str(d["_id"]) if isinstance(d.get("_id"), ObjectId) else d.get("_id")
    return docs

@app.post("/api/summary")
def shareable_summary(payload: Summary):
    username = payload.username
    pipeline = [
        {"$match": {"username": username}},
        {"$group": {
            "_id": "$username", 
            "points": {"$sum": "$points"},
            "count": {"$sum": 1}
        }}
    ]
    try:
        data = list(db["activity"].aggregate(pipeline)) if db else []
        total_points = int(data[0]["points"]) if data else 0
        count = int(data[0]["count"]) if data else 0
        badges = list(db["badge"].find({"username": username})) if db else []
        for b in badges:
            b["_id"] = str(b["_id"]) if isinstance(b.get("_id"), ObjectId) else b.get("_id")
        return {
            "username": username,
            "total_points": total_points,
            "activities_logged": count,
            "badges": badges,
            "share_text": f"{username} earned {total_points} Green Points with {count} eco actions! 🌿"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Seed fake transactions for demo
@app.post("/api/seed")
def seed(username: str = "neo"):
    demo = [
        {"activity_type": "public_transport", "quantity": 2},
        {"activity_type": "vegan_meal", "quantity": 3},
        {"activity_type": "recycling", "quantity": 5},
        {"activity_type": "bike_ride", "quantity": 1},
    ]
    created = []
    for item in demo:
        payload = ActivityCreate(username=username, **item)
        res = log_activity(payload)  # reuse logic
        created.append(res)
    return {"ok": True, "created": created}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
