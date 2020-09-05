import os
import logging
import json
import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(funcName)s(): %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('app.log')
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

HOST = os.environ.get('HOST')
DATABASE = os.environ.get('DATABASE')
USER = os.environ.get('USER')
PASSWORD = os.environ.get('PASSWORD')


def db_connection() -> psycopg2.extensions.connection:
    try:
        logger.info('Connecting to {0} with user {1}'.format(DATABASE, USER))
        con = psycopg2.connect(host=HOST, database=DATABASE, user=USER, password=PASSWORD)
        return con
    except psycopg2.Error as e:
        logger.exception(e)
        exit("cannot connect to database")


class JsonAdapter:
    def __init__(self, json_source_file: str):
        with open(json_source_file) as json_data:
            self.subscribers_list_dict = json.load(json_data)

    def get_all(self) -> list:
        return self.subscribers_list_dict
