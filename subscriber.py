import re
from typing import TYPE_CHECKING
from typing import Union

from database_lib import JsonAdapter

if TYPE_CHECKING:
    from typing import Union


class SubscriberFilterInterface:
    def filter(self, subscribers: list) -> list:
        pass


class Subscriber:
    def __init__(self, name: str, contact: str, status: str, date_created: 'datetime' = None,
                 subscriber_id: str = None):
        self.id = subscriber_id
        self.name = name
        self.contact = contact
        self.status = status
        self.date_created = date_created

    def __str__(self):
        return 'name: {0}, contact: {1}'.format(self.get_name(), self.get_contact())

    def set_contact(self):
        # email and number regex
        pass

    def get_contact(self) -> str:
        return self.contact

    def get_name(self) -> str:
        return self.name

    def get_status(self) -> str:
        return self.status

    def get_date_created(self) -> Union[None, 'datetime']:
        return self.date_created


class SubscriberCollection:
    def __init__(self):
        self.subscribers = {}

    def __str__(self):
        if self.is_empty():
            return 'Collection is empty'
        subscribers_str = []
        for subscribers in self.subscribers.values():
            subscribers_str.append(str(subscribers))
        return '\n'.join(subscribers_str)

    def __iter__(self) -> 'Iterator':
        return iter(self.subscribers)

    def filter(self, subscriber_filter: 'SubscriberFilterInterface') -> list:
        return subscriber_filter.filter(self.get_list())

    def is_from_db(self) -> bool:
        if self.is_empty():
            print('Collection is empty. May raise exception in future')
        for subscriber in self.subscribers.values():
            if subscriber.get_id() is None:
                return False
        return True

    def is_empty(self) -> bool:
        if self.get_size() == 0:
            return True
        return False

    def get_collection(self) -> dict:
        """
        Returns a collection of Subscriber objects as dictionary where the contact is the key
        """
        return self.subscribers

    def get_list(self) -> list:
        """
        Returns a list of Subscriber objects
        """
        return list(self.subscribers.values())

    def get_by_key(self, key: str) -> 'Subscriber':
        return self.subscribers[key]

    def get_size(self) -> int:
        return len(self.subscribers)

    def set_collection(self, collection: list) -> 'SubscriberCollection':
        for subscriber in collection:
            self.add_to_collection(subscriber)
        return self

    def add_to_collection(self, subscriber: 'Subscriber') -> None:
        if subscriber.get_contact() in self.subscribers:
            print('{} contact is already in collection'.format(subscriber.get_contact()))
        self.subscribers[subscriber.get_contact()] = subscriber


class SubscriberFactory:
    def create_from_dict(self, subscriber_dict) -> 'Subscriber':
        return Subscriber(
            subscriber_dict['name'],
            subscriber_dict['contact'],
            subscriber_dict['status'],
        )

    def create_subscriber_collection(self, subscriber_data_list: list) -> 'SubscriberCollection':
        subscriber_list = []
        for subscriber_data in subscriber_data_list:
            subscriber = self.create_from_dict(subscriber_data)
            subscriber_list.append(subscriber)
        return SubscriberCollection().set_collection(subscriber_list)


class SubscriberMapper:  # mapper is kind of redundant abstraction
    def __init__(self, adapter: JsonAdapter):
        self.adapter = adapter
        self.factory = None

    def save_all(self, collection: SubscriberCollection):
        pass

    def get_all_subscribers(self, factory: 'SubscriberFactory') -> 'SubscriberCollection':
        self.factory = factory
        subscriber_collection = []
        subscribers_list_dict = self.adapter.get_all()
        for subscriber_dict in subscribers_list_dict:
            if self.is_subscriber_contact_valid(subscriber_dict['contact']):
                subscriber = self.factory.create_from_dict(subscriber_dict)
                subscriber_collection.append(subscriber)
            else:
                print('Subscriber contact "{}" is not valid'.format(subscriber_dict['contact']))

        return SubscriberCollection().set_collection(
            subscriber_collection)  # where is the subscriber collection coming from

    @staticmethod
    def is_subscriber_contact_valid(contact):
        contact = str(contact)
        email_regex = r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)'
        telephone_regex = r'^947(0|1|2|5|6|7|8)\d{7}$'

        if re.match(telephone_regex, contact) or re.match(email_regex, contact):
            return True
        return False
