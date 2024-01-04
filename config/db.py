from pymongo.mongo_client import MongoClient

# host = "13.127.57.185"
host = "localhost"
port = 27017
db = "pvvnl"
collection = "predictTest"
collection1 = "actual"
collection2 = "sensor"
collection3 = "prediction_h"
collection4 =  "predict"

MONGO_URL = f"mongodb://{host}:{port}"
client = MongoClient(MONGO_URL)

db1 = client[db]
collection_name = db1[collection]
collection_name1 = db1[collection1]
collection_name2 = db1[collection2]
collection_name3 = db1[collection3]
collection_name4 = db1[collection4]
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)