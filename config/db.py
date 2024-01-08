from pymongo.mongo_client import MongoClient

# host = "13.127.57.185"
host = "localhost"
port = 27017
db = "pvvnl"
collection = "predictTest"
collection1 = "forcast"
collection2 = "prediction_h"
collection3 = "predict"

MONGO_URL = f"mongodb://{host}:{port}"
client = MongoClient(MONGO_URL)

db1 = client[db]
'''
collection is for condition including holidays and weather data 
collection1 is for condition without holiday and weather
collection2 is for condition with simple load profile data
collection3 is for condition including holidays, weather data also make stationary and correlation` 
'''
collection_name = db1[collection]
collection_name1 = db1[collection1]
collection_name2 = db1[collection2]
collection_name3 = db1[collection3]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
