import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import datetime
import pandas as pd
from pymongo import MongoClient
from .utils import Config

db_config = Config.env_config

Base = declarative_base()

class Feedback(Base):

    __tablename__ = 'feedbacks'

    id_ = sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)
    eval_id = sa.Column("eval_id", sa.Text)
    eval_name = sa.Column("eval_name", sa.Text)
    test_id = sa.Column("test_id", sa.Text)
    passed = sa.Column("passed", sa.Boolean)
    comments = sa.Column("comments", sa.Text)
    timestamp = sa.Column("timestamp", sa.DateTime)

    def __init__(self, feedback_dict):
        self.eval_id = str(feedback_dict['eval_id'])
        self.eval_name = str(feedback_dict['eval_name'])
        self.test_id = str(feedback_dict['test_id'])
        self.passed = feedback_dict['passed']
        self.comments = str(feedback_dict['comments'])
        self.timestamp = feedback_dict['timestamp']

    def __repr__(self):
        return f'({self.eval_id}, {self.eval_name}, {self.test_id}, {self.passed}, {self.comments}, {self.timestamp})'

engine = sa.create_engine(f'postgresql://{db_config["USER"]}:{db_config["PASSWORD"]}@{db_config["HOST"]}/{db_config["DATABASE"]}')
try:
    Base.metadata.create_all(bind=engine)
except OperationalError as exp:
    print(exp)

def saveRating(rating_dict):

    def saveData(table_class, sess, values):

        results = (
            sess.query(table_class)
            .filter((table_class.eval_id == rating_dict['eval_id']), 
                    (table_class.test_id == rating_dict['test_id']))
            .one_or_none()
        )
        
        if not results:
            table = table_class(rating_dict)
            sess.add(table)
            sess.commit()
        else:
            for k, v in values.items():
                setattr(results, k, v)
            sess.commit()

    sess = sessionmaker(bind=engine)()
    
    rating_dict['timestamp'] = datetime.datetime.now()

    saveData(Feedback, sess, {k:rating_dict[k] for k in ['eval_id', 'eval_name', 'test_id', 'passed', 'comments', 'timestamp']})

def getRating(eval_id):

    df = pd.read_sql(sql=f"""SELECT 
                            *
                        FROM
                            feedbacks
                        WHERE "eval_id" = '{eval_id}'
                    """, con=engine)
    return df

class MongoDB():

    def __init__(self, db_name: str, collection: str | None = None):
        client = MongoClient(f'mongodb://{db_config['MONGO_HOST']}:{db_config['MONGO_PORT']}')
        self.db = client[db_name]
        if collection: self.collection = self.db[collection]

    def exists(self):
        return self.collection.name in self.listEvals()
    
    def listEvals(self):
        return sorted(self.db.list_collection_names())

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

class EvalDB(MongoDB):

    def __init__(self, collection: str|None = None):
        super().__init__(db_name=db_config['MONGO_EVAL_DB_NAME'], collection=collection)

    def getTimeStamp(self):
        return datetime.datetime.fromtimestamp(float(self.collection.find_one({'_id': 0})['event_id']))

class EvalConfigDB(MongoDB):

    def __init__(self, collection: str|None = None):
        super().__init__(db_name=db_config['MONGO_EVAL_CONFIG_DB_NAME'], collection=collection)