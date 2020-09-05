import logging
import re
from datetime import datetime
from typing import Union

from psycopg2 import extensions, extras

# from scraper import DateTimeUpdater

formatter = logging.Formatter('%(asctime)s:%(name)s:%(funcName)s(): %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('app.log')
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class CollectionSizeMismatch(Exception):
    def __int__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AnnouncementFormatterInterface:
    def format(self, announcements: list) -> list:
        pass


class AnnouncementCollection:
    def __init__(self):
        self.announcements = {}
        self.index = -1

    def __str__(self):
        if self.is_empty():
            return 'Collection is empty'
        announcements_str = []
        for announcement in self.announcements.values():
            announcements_str.append(str(announcement))
        return '\n'.join(announcements_str)

    def __iter__(self) -> 'Iterator':
        return iter(self.announcements)

    def format(self, announcement_formatter: 'AnnouncementFormatterInterface') -> list:
        return announcement_formatter.format(self.get_collection_list())

    def is_from_db(self) -> bool:
        if self.is_empty():
            print('Collection is empty. May raise exception in future')
        for announcement in self.announcements.values():
            if announcement.get_id() is None:
                return False
        return True

    def is_uniform(self) -> bool:
        a = []
        b = []
        for announcement in self.announcements.values():
            _id = announcement.get_id()
            if _id is None:
                a.append(_id)
            else:
                b.append(_id)
        return len(a) == 0 or len(b) == 0

    def is_empty(self) -> bool:
        if self.get_size() == 0:
            return True
        return False

    def get_collection(self) -> dict:
        return self.announcements

    def get_collection_list(self) -> list:
        return list(self.announcements.values())

    def get(self, key: str) -> 'Announcement':
        return self.announcements[key]

    def get_size(self) -> int:
        return len(self.announcements)

    def set_collection(self, collection: list) -> 'AnnouncementCollection':
        # self.announcements = collection
        # self.sort()
        # self.index = -1

        for announcement in collection:
            self.add_to_collection(announcement)

        self.index = -1
        return self

    def add_to_collection(self, announcement: 'Announcement') -> None:
        self.announcements[announcement.get_check_string()] = announcement
        # return self

    def sort(self) -> 'AnnouncementCollection':
        logger.info('Sorting collection...')
        sorted(self.announcements.values(), key=lambda x: x.get_published_datetime(), reverse=True)
        logger.info('Collection sorted')
        return self

    def get_same_day_announcements(self):
        collection = {}
        duplicate_announcement_list = []

        if not self.is_from_db():
            for announcement in self.announcements.values():
                datestrkey = announcement.get_published_datetime().strftime('%d%m%Y')
                if datestrkey in collection:
                    collection[datestrkey].append(announcement)
                else:
                    collection[datestrkey] = [announcement]

        for group in collection.values():
            if len(group) > 1:
                duplicate_announcement_list.extend(group)
        logger.info(
            'There are {} announcements that have similar published dates'.format(len(duplicate_announcement_list)))
        return duplicate_announcement_list

    def get_tuple_list(self):
        tuple_list = []
        for announcement in self.announcements.values():
            tuple_list.append(
                (
                    announcement.get_title(),
                    announcement.get_url(),
                    announcement.get_check_string(),
                    announcement.get_published_datetime(),
                    announcement.get_updated_datetime(),
                    announcement.get_retrieved_datetime(),
                )
            )
        return tuple_list


class AnnouncementFactory:
    def create_from_dict(self, announcement_dict) -> 'Announcement':
        logger.info(
            'Creating Announcement object from {0} data'.format('stored' if announcement_dict['id'] else 'site')
        )
        return Announcement(
            announcement_dict['id'],
            announcement_dict['title'],
            announcement_dict['url'],
            announcement_dict['published_datetime'],
            announcement_dict['updated_datetime'],
            announcement_dict['retrieved_datetime'],
            announcement_dict['stored_timestamp'],
            announcement_dict['check_string'],
        )

    def get_announcement_collection(self, announcement_data_list: list) -> 'AnnouncementCollection':
        announcement_list = []
        for announcement_data in announcement_data_list:
            announcement = self.create_from_dict(announcement_data)
            announcement_list.append(announcement)
            logger.info(
                'Created Announcement object with check string: {0}...'.format(announcement.get_check_string()[0:20])
            )
        return AnnouncementCollection().set_collection(announcement_list)


class AnnouncementMapper:
    def __init__(self, connection: extensions.connection):
        self.connection = connection
        self.factory = None

    def save_all(self, collection: AnnouncementCollection):
        sql = 'INSERT INTO ' \
              'announcement(title, url, check_string, published_datetime, updated_datetime, retrieved_datetime) ' \
              'VALUES (%s, %s, %s, %s, %s, %s)'
        var_list = collection.get_tuple_list()
        cursor: extensions.cursor = self.connection.cursor()
        result = cursor.executemany(sql, var_list)
        self.connection.commit()
        logger.info('Collection stored in database') if result is None else ''
        return result

    def get_recent_announcements(self, factory: 'AnnouncementFactory') -> 'AnnouncementCollection':
        self.factory = factory
        sql = 'select * from announcement order by published_datetime DESC limit 10'
        cursor: extensions.cursor = self.connection.cursor(cursor_factory=extras.DictCursor)
        cursor.execute(sql)
        result = cursor.fetchall()
        announcement_collection = factory.get_announcement_collection(result)
        return announcement_collection


class Announcement:
    def __init__(self, post_id, title, url, published_datetime, updated_datetime, retrieved_datetime, stored_timestamp,
                 check_string):
        self.id = post_id
        self.title = title
        self.url = url
        self.published_datetime = published_datetime
        self.updated_datetime = updated_datetime
        self.retrieved_datetime = retrieved_datetime
        self.stored_timestamp = stored_timestamp
        if not check_string:
            self.check_string = self.generate_check_string()
        else:
            self.check_string = check_string

    def __str__(self) -> str:
        return self.get_title() + ' ' + self.get_published_datetime().strftime('%d-%m-%Y')

    def generate_check_string(self) -> str:
        logger.info('Generating check string')
        title_lowercase = self.get_title().lower()
        title_alphanum_no_space = re.sub(r'[^A-Za-z0-9]', "", title_lowercase)
        date_num = self.get_published_datetime().strftime('%d%m%Y')
        return title_alphanum_no_space + date_num

    def get_id(self) -> str:
        return self.id

    def get_title(self) -> str:
        return self.title

    def get_url(self) -> str:
        return self.url

    def get_published_datetime(self) -> datetime:
        if self.published_datetime.strftime('%H%M%S') == '000000':
            logger.info('getting only published date')
        else:
            logger.info('getting published date and time')
        return self.published_datetime

    def get_updated_datetime(self) -> Union[None, datetime]:
        return self.updated_datetime

    def get_retrieved_datetime(self) -> datetime:
        return self.retrieved_datetime

    def get_stored_datetime(self) -> Union[None, datetime]:
        return self.stored_timestamp

    def get_check_string(self) -> str:
        return self.check_string

    def set_published_datetime(self, dt: datetime) -> 'Announcement':
        logger.info('setting published datetime')
        self.published_datetime = dt
        return self

    def set_updated_datetime(self, dt: datetime) -> 'Announcement':
        logger.info('setting updated datetime')
        self.updated_datetime = dt
        return self


class Comparator:
    def __init__(self, a: AnnouncementCollection, b: AnnouncementCollection, dtu: 'DateTimeUpdater'):
        web = a
        stored = b
        if a.is_from_db():
            web = b
            stored = a
        self.web_collection = web
        self.stored_collection = stored
        self.new_announcements = AnnouncementCollection()
        self.datetime_updater = dtu

    def check_for_new_announcements(self) -> 'Comparator':
        if self.stored_collection.get_size() != self.web_collection.get_size():
            raise CollectionSizeMismatch('Cannot compare collections. Not the same size')
        self.web_collection = self.datetime_updater.resolve_same_day_announcements(self.web_collection)
        self.web_collection.sort()
        self.stored_collection.sort()
        new_announcements = []
        for key in self.web_collection:
            if key not in self.stored_collection:
                new_announcements.append(self.web_collection.get(key))
        self.new_announcements.set_collection(new_announcements)
        return self

    def get_new_announcements(self) -> AnnouncementCollection:
        return self.new_announcements

    def is_any_announcement_new(self) -> bool:
        return not self.new_announcements.is_empty()
