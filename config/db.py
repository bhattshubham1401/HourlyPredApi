from pymongo.mongo_client import MongoClient

# host = "13.127.57.185"
host = "localhost"
port = 27017
db = "pvvnl"

collection = "forcast"
collection1 = "forcast1"
collection2 = "forcast2"
collection3 = "forcast3"
collection4 = "dlms"
collection5 = "feeder_data_daily_log"
collection6 = "jdvvnl_LF"
collection7 = "jdvvnlSensor"
collection8 = "weather_data"

MONGO_URL = f"mongodb://{host}:{port}"
client = MongoClient(MONGO_URL)

db1 = client[db]
'''
collection is for condition including holidays and weather data 
collection1 is for condition with simple load profile data.  
collection2 is for condition with including holidays, weather data also make stationary and correlation` 
collection3 is for condition 
'''
collection_name = db1[collection]
collection_name1 = db1[collection1]
collection_name2 = db1[collection2]
collection_name3 = db1[collection3]
collection_name4 = db1[collection4]
collection_name5 = db1[collection5]
collection_name6 = db1[collection6]
collection_name7 = db1[collection7]
collection_name8 = db1[collection8]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
