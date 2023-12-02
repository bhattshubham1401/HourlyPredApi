from pymongo.mongo_client import MongoClient
from urllib.parse import quote_plus

# Your MongoDB connection details
host = "13.127.57.185"
port = 27017
db = "pvvnl"
username = "ml_user"
password = "Project@3i2"
collection = "predict"
collection1 = "actual"

# Escape username and password
escaped_username = quote_plus(username)
escaped_password = quote_plus(password)

# Construct the MongoDB connection string
MONGO_URL = f"mongodb://{escaped_username}:{escaped_password}@{host}:{port}/{db}"
client = MongoClient(MONGO_URL)
db1 = client[db]
collection_name = db1[collection]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)