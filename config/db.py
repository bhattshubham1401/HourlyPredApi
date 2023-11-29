from pymongo import MongoClient

# client = MongoClient("mongodb+srv://shubhambhatt687:Shubham@1401@cluster0.sxuqrnj.mongodb.net/?retryWrites=true&w=majority")
# db = client.pvvnl
# collection_name = db["grid_log"]

from pymongo.mongo_client import MongoClient

host = "13.127.57.185"
port = 27017
db = "pvvnl"
collection = "predict"
username = "shubhambhatt687"
password = "Shubham@1401"
MONGO_URL = f"mongodb://{host}:{port}"
client = MongoClient(MONGO_URL)
db1 = client[db]
collection_name = db1[collection]
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)