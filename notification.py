import logging
import os
import re

import requests
from dotenv import load_dotenv, find_dotenv

from announcement import AnnouncementFormatterInterface, AnnouncementCollection
from subscriber import SubscriberFilterInterface, SubscriberCollection

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


class NotifierInterface:
    def __init__(
            self,
            a: 'AnnouncementCollection',
            af: 'AnnouncementFormatterInterface',
            s: 'SubscriberCollection',
            sf: 'SubscriberFilterInterface',
            n: 'NotificationAgentInterface'):
        pass

    def notify(self):
        pass

    def prepare_messages(self):
        pass

    def prepare_subscribers(self):
        pass

    def filter_subscribers(self):
        pass


class NotificationAgentInterface:
    def send(self, message: str, recipients: list):
        pass


class TextitNotifier(NotifierInterface):
    def __init__(self, a: 'AnnouncementCollection', af: 'AnnouncementFormatterInterface', s: 'SubscriberCollection',
                 sf: 'SubscriberFilterInterface', n: 'NotificationAgentInterface'):
        super().__init__(a, af, s, sf, n)  # using super as an informal interface
        self.announcements = a
        self.announcement_formatter = af
        self.subscribers = s
        self.subscriber_filter = sf
        self.notification_agent = n

    def prepare_messages(self):
        return self.announcements.format(self.announcement_formatter)

    def filter_subscribers(self):
        filtered_subscribers = []
        subscribers = self.subscribers.filter(self.subscriber_filter)
        for subscriber in subscribers:
            filtered_subscribers.append(str(subscriber.get_contact()))
        return filtered_subscribers

    def notify(self):
        messages = self.prepare_messages()
        subscribers = self.filter_subscribers()
        for message in messages:  # send each message to all subscribers
            status = self.notification_agent.send(message, subscribers)
            logger.info('Message sent? {}'.format(status))


class TexitSubscriberFilter(SubscriberFilterInterface):
    def __init__(self):
        self.telephone_regex = r'^947(0|1|2|5|6|7|8)\d{7}$'
        self.filtered_subscribers = []

    def filter(self, subscribers: list) -> list:
        for subscriber in subscribers:
            if self.is_textit_compliant(subscriber):
                self.filtered_subscribers.append(subscriber)
        return self.filtered_subscribers

    def is_textit_compliant(self, subscriber: 'Subscriber') -> bool:
        if re.match(self.telephone_regex, str(subscriber.get_contact())):
            return True
        return False


class TexitMessageFormatter(AnnouncementFormatterInterface):
    def __init__(self):
        self.messages = []

    def format(self, announcements: list) -> list:
        for announcement in announcements:
            message = \
                '(test) BIT Announcement:%0a' \
                '{0} -%0a{1} %0aPublished on {2}'.format(
                    announcement.get_title(),
                    announcement.get_url(),
                    announcement.get_published_datetime().strftime('%d-%b-%Y, %I:%M %p'))
            self.messages.append(message)
        return self.messages


class TextitAgent(NotificationAgentInterface):
    def __init__(self):
        self.configuration = {
            'id': os.environ.get('TEXTIT_ID'),
            'pw': os.environ.get('TEXTIT_PW'),
        }
        self.url = 'http://www.textit.biz/sendmsg/index.php'

    def send(self, messages: str, recipients: list):
        self.set_recipients(recipients)
        self.set_message(messages)
        logger.info('textit api call to endpoint: {}'.format(self.url))
        response = requests.post(self.url, data=self.configuration)

        logger.info('textit api call status code: {}'.format(response.status_code))
        logger.info('textit api response status {}'.format(response.text.split(':')[0]))
        logger.info('textit api response: {}'.format(response.text))
        if response.status_code == 200 and response.text.split(':')[0] == 'OK':
            return True
        else:
            return False

    def set_recipients(self, recipients: list) -> None:
        self.configuration['to'] = ','.join(recipients)

    def set_message(self, message: str) -> None:
        self.configuration['text'] = message


class TextitErrorReporter:
    def __init__(self):
        self.agent = TextitAgent()

    def send(self, error_message: str):
        self.agent.send(error_message, [os.environ.get('TEXTIT_ID')])
