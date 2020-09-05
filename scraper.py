import logging
import re
from datetime import datetime
from datetime import timezone as python_timezone
from time import sleep
from typing import Union

import iso8601
import requests
from bs4 import BeautifulSoup, SoupStrainer, Tag, NavigableString
from pytz import timezone

from announcement import AnnouncementFactory, AnnouncementCollection

formatter = logging.Formatter('%(asctime)s:%(name)s:%(funcName)s(): %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('test.log')
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


class HTMLPartialNotFound(Exception):
    def __init__(self, method: str, element: str, id_name: str, class_names: str):
        self.message = \
            'Exception raised in {3} - HTML extraction failed. ' \
            'Could not find element "{0}" with id="{1}" and class="{2}"'.format(element, id_name, class_names, method)
        super().__init__(self.message)


class DateStringFormatMismatch(Exception):
    def __init__(self, method_name: str, date_string: str):
        self.message = \
            'Exception raised in {0} - ' \
            'Cannot parse date from "{1}" string from announcement list'.format(method_name, date_string)
        super().__init__(self.message)


class ISO8601FormatMismatch(Exception):
    def __init__(self):
        self.message = \
            'Expected ISO8601 datetime string with timezone in format (yyyy-mm-ddThh:mm:ss:[+-]hh:ss)'
        super().__init__(self.message)


class AnnouncementContentNotFound(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class HTMLStructureMismatch(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class DocumentFetcher:
    def __init__(self):
        self.html_document = b''
        self.headers = {
            'Host': 'bit.lk',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/84.0.4147.105 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Language': 'en-US,en;q=0.9'
        }

    def fetch_document(self, url: str) -> bytes:
        """Download the webpage given by the url using python requests library"""
        self.html_document = b''
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            self.html_document = response.content
            logger.info('web page {0} fetched with status code: {1}'.format(url, response.status_code))
            return self.html_document
        except requests.exceptions.RequestException:
            logger.exception('Exception raised in Scraper.fetch_document()')
            raise

    def set_headers(self, headers: dict) -> None:
        """Set the headers the request used to download a webpage"""
        self.headers = headers

    def set_user_agent(self, user_agent: str) -> None:
        """Set an alternative user-agent header"""
        self.headers['User-Agent'] = user_agent


class Scraper:
    def __init__(self):
        self.html_document = b''
        self.html_partial = None
        self.announcement_data_list = []

    def set_html_document(self, html_document: bytes) -> 'Scraper':
        self.html_document = html_document
        return self

    def extract_html(self, html_element: str, id_attribute: Union[None, str], class_attributes: str) -> 'Scraper':
        parse_only_article = SoupStrainer(html_element, {'id': id_attribute})
        soup = BeautifulSoup(self.html_document, 'html.parser', parse_only=parse_only_article)
        self.html_partial = soup.find(html_element, id=id_attribute, class_=class_attributes)
        if self.html_partial is None:
            raise HTMLPartialNotFound('Scraper.extract_html()', html_element, id_attribute, class_attributes)
        logger.info('Extracted html element "{0}"'.format(html_element))
        return self

    def get_datetime(self) -> datetime:
        regex = r'^(\d{4})-(\d{2})-(\d{2})T(\d{2})\:(\d{2})\:(\d{2})[+-](\d{2})\:(\d{2})$'
        if self.html_partial.name == 'time':
            announcement_datetime_str = self.html_partial.attrs['datetime']
            if re.match(regex, announcement_datetime_str) is None:
                raise ISO8601FormatMismatch()
            announcement_datetime = iso8601.parse_date(announcement_datetime_str)
            return announcement_datetime.astimezone(timezone('Asia/Colombo'))

    def parse_announcement_data(self) -> 'Scraper':
        """
        Extract announcement data from the extracted html partial

        The html partial should be a Tag object returned from BeautifulSoup4.find()
        """
        logger.info('Parsing extracted html partial')
        for tag in self.html_partial:  # there are 63 tags
            if tag.name == 'h4':
                announcement_data = self.get_data_from_tag(tag)
                self.announcement_data_list.append(announcement_data)
        logger.info('Compiled announcement data list from html web page partial')
        return self

    def get_announcement_data_list(self) -> list:
        self.parse_announcement_data()
        return self.announcement_data_list

    def verify_tag_structure(self, tag: Tag) -> None:
        if tag.name != 'h4':
            raise HTMLStructureMismatch('Title container element not found')
        if not hasattr(tag, 'contents') or len(tag.contents) != 1:
            raise HTMLStructureMismatch('Element has no children or too many children')
        if tag.contents[0].name != 'a':
            raise HTMLStructureMismatch('HTML anchor element is not found')
        if not hasattr(tag.contents[0], 'href'):
            raise HTMLStructureMismatch('Cannot find href attribute')
        if hasattr(tag.next_sibling, 'string') and tag.next_sibling.string != '\n':
            raise HTMLStructureMismatch('There should be a new line after the h4 title element')
        if tag.next_sibling.next_sibling.name != 'strong':
            raise HTMLStructureMismatch('Date only string wrapper is not HTML strong element. Check HTML structure')
        if type(tag.next_sibling.next_sibling.contents) is not list:
            raise HTMLStructureMismatch('Cannot find date only string from an announcement list post')

    def check_announcement_content_validity(self, a: dict) -> None:
        """
        check the title and url of the announcement

        :param a: Dictionary with announcement data
        """
        url_regex = r'[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)'

        if a['title'] == '' or type(a['title']) is not NavigableString:
            raise AnnouncementContentNotFound('Announcement title is empty or invalid')
        if re.match(url_regex, a['url'], re.IGNORECASE) is None:
            raise AnnouncementContentNotFound('Announcement URL is invalid')

    def get_data_from_tag(self, tag: Tag) -> dict:
        """
        Extract announcement data from a BeautifulSoup4 Tag object

        :param tag: BeautifulSoup4 Tag object
        :return: A dictionary of extracted data of a single announcement
        """
        self.verify_tag_structure(tag)
        title = tag.string
        url = tag.contents[0]['href']  # tag.contents[0].name is 'a'
        date_string = tag.next_sibling.next_sibling.contents[0]
        published_date = (self.get_date_from_string(date_string))
        announcement_data = {
            'id': None,
            'title': title,
            'url': url,
            'check_string': None,
            'published_datetime': published_date,
            'updated_datetime': None,
            'retrieved_datetime': datetime.now(),
            'stored_timestamp': None
        }
        self.check_announcement_content_validity(announcement_data)
        return announcement_data

    def get_announcements(self, factory: 'AnnouncementFactory') -> 'AnnouncementCollection':
        """
        Returns a collection of announcement objects in the form of an AnnouncementCollection object

        :param factory: An instance of AnnouncementFactory
        :return: An instance of AnnouncementCollection
        """
        collection = factory.get_announcement_collection(self.get_announcement_data_list())
        return collection

    @staticmethod
    def get_date_from_string(date_string: str) -> datetime:
        """
        Create a date only datetime object by extracting a date from a string

        The date string should be in the format "May 11st, 2020 by "
        else method raises DateStringFormatMismatch exception.

        About the date: The month is the full English name. The date is ordinal.

        :param date_string: A string in the format of "May 11st, 2020 by ". Note the space after word 'by '
        :return: A date only datetime object with 00:00:00 time
        """
        regex = r'^(January|February|March?|April|May|June|July|August|September|October|November|December)' \
                r' (\d{1,2})(st|nd|rd|th), (\d{4}) by $'

        if re.match(regex, date_string) is None:
            raise DateStringFormatMismatch('Scraper.get_date_from_string()', date_string)

        date_list = date_string.split(' ')

        if len(date_list[1]) == 5:  # i.e. '11st,' with comma
            date_list[1] = date_list[1][0:2]
        else:  # i.e '2nd,' no zero prefix because ordinal date
            date_list[1] = date_list[1][0:1].zfill(1)

        new_date_string = ' '.join(date_list[0:3])  # new date extracted by removing 'by', spaces and commas
        date = datetime.strptime(new_date_string, '%B %d %Y')
        date = date.replace(tzinfo=python_timezone.utc)  # localizing to avoid comparison error when sorting later
        return date


class DateTimeUpdater:
    """
    Update the datetime of scraped datetime values
    """

    def __init__(self, fetcher: DocumentFetcher, scraper: Scraper):
        self.fetcher = fetcher
        self.scraper = scraper

    def resolve_same_day_announcements(self, collection: AnnouncementCollection):
        same_day_announcements = collection.get_same_day_announcements()
        for announcement in same_day_announcements:
            logger.info('Updating published datetime of same day announcements')
            web_page = self.fetcher.fetch_document(announcement.get_url())
            self.scraper.set_html_document(web_page)
            self.scraper.extract_html('time', id_attribute=None, class_attributes='published')
            announcement.set_published_datetime(self.scraper.get_datetime())
        return collection

    def update_all_datetime(self, collection: AnnouncementCollection):
        collection = collection.get_collection_list()
        for announcement in collection:
            web_page = self.fetcher.fetch_document(announcement.get_url())
            self.scraper.set_html_document(web_page)
            self.scraper.extract_html('time', id_attribute=None, class_attributes='published')
            announcement.set_published_datetime(self.scraper.get_datetime())
            self.scraper.extract_html('time', id_attribute=None, class_attributes='updated')
            announcement.set_updated_datetime(self.scraper.get_datetime())
            logger.info('waiting 4s ...')
            sleep(4)
        return collection
