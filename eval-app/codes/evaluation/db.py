from .utils import Config
from pymongo import MongoClient

class EvalDB():

    def __init__(self, collection: str):
        client = MongoClient(f'mongodb://{Config.env_config['MONGO_HOST']}:{Config.env_config['MONGO_PORT']}')
        db = client[Config.env_config['MONGO_EVAL_DB_NAME']]
        self.collection = db[collection]

    def add(self, data: list[dict] | dict):
        if isinstance(data, list):
            self.collection.insert_many(data)
        elif isinstance(data, dict):
            self.collection.insert_one(data)
        else:
            raise Exception('Invalid data type. Data type must be either dict or list of dicts.')
        
    def getAll(self):
        return self.collection.find({})
        
    def drop(self):
        self.collection.drop()

    def update(self, filter: dict, value: dict):
        self.collection.update_one(filter, {"$set": value})