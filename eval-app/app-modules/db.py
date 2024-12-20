import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import pandas as pd

import importlib
utils = importlib.import_module('utils')

import dotenv
db_config = dotenv.dotenv_values(utils.Config.DIR_HOME / 'app-modules' / 'db.env')

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
Base.metadata.create_all(bind=engine)

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