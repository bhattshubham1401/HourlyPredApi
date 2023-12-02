from pymongo.mongo_client import MongoClient

host = "13.127.57.185"
port = 27017
db = "pvvnl"
collection = "predict"
# collection1 = "actual"
MONGO_URL = f"mongodb://{host}:{port}"
client = MongoClient(MONGO_URL)

db1 = client[db]
collection_name = db1[collection]
# collection_name1 = db1[collection1]
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)