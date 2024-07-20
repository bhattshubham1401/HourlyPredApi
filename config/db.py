from pymongo.mongo_client import MongoClient

# host = "13.127.57.185"
host = "localhost"
port = 27017
db = "jpdcl"

collection  = "predictions"
collection1 = "forcast1"
collection2 = "forcast2"
collection3 = "forcast3"
collection4 = "dlms"
collection5 = "load_profile_jdvvnl"
collection6 = "jdvvnl_lf_pred"
collection7 = "sensor"
collection8 = "weather_data"
collection9 = "jdvvnl_LF"
collection10 = "circle"
collection11 = "transformed_dataV1"
collection12 = "weather_data_forcast"

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
collection_name9 = db1[collection9]
collection_name10 = db1[collection10]
collection_name11 = db1[collection11]
collection_name12 = db1[collection12]

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
