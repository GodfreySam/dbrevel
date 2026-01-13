"""
MongoDB Seed Data Script
Run this after containers are up:
python examples/ecommerce/seed_mongo.py
"""

import random
from datetime import datetime, timedelta

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['dbreveldemo']

# Clear existing data
db.sessions.delete_many({})
db.reviews.delete_many({})

print("Seeding MongoDB...")

# Sessions data
sessions = []
for user_id in range(1, 11):
    for i in range(random.randint(3, 10)):
        session = {
            "user_id": user_id,
            "started_at": datetime.now() - timedelta(days=random.randint(1, 30)),
            "ended_at": datetime.now() - timedelta(days=random.randint(0, 29)),
            "pages_viewed": random.randint(5, 50),
            "device": random.choice(["mobile", "desktop", "tablet"]),
            "country": "NG",
            "city": random.choice(["Lagos", "Abuja", "Kano", "Ibadan", "Port Harcourt"])
        }
        sessions.append(session)

db.sessions.insert_many(sessions)
print(f"✓ Inserted {len(sessions)} sessions")

# Reviews data
reviews = []
product_ids = list(range(1, 11))
user_ids = list(range(1, 11))

review_texts = [
    "Excellent product! Very satisfied with my purchase.",
    "Good quality but delivery was a bit slow.",
    "Amazing! Exactly as described. Will buy again.",
    "Not bad, but could be better for the price.",
    "Fantastic! Highly recommend to everyone.",
    "Product is okay. Nothing special.",
    "Love it! Best purchase I've made in a while.",
    "Disappointed. Quality not as expected.",
    "Great value for money. Very happy!",
    "Perfect! Exceeded my expectations."
]

for _ in range(50):
    review = {
        "product_id": random.choice(product_ids),
        "user_id": random.choice(user_ids),
        "rating": random.randint(3, 5),
        "title": f"Review from Customer {random.randint(1, 10)}",
        "text": random.choice(review_texts),
        "helpful_count": random.randint(0, 25),
        # 75% verified
        "verified_purchase": random.choice([True, True, True, False]),
        "created_at": datetime.now() - timedelta(days=random.randint(1, 60))
    }
    reviews.append(review)

db.reviews.insert_many(reviews)
print(f"✓ Inserted {len(reviews)} reviews")

# Create indexes
db.sessions.create_index("user_id")
db.sessions.create_index("started_at")
db.reviews.create_index("product_id")
db.reviews.create_index("user_id")
db.reviews.create_index("rating")

print("✓ MongoDB seeding complete!")
print(f"  - Sessions collection: {db.sessions.count_documents({})} documents")
print(f"  - Reviews collection: {db.reviews.count_documents({})} documents")

client.close()
