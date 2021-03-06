import logging
import sys
import traceback

from announcement import AnnouncementFactory, AnnouncementMapper, Comparator
from database_lib import db_connection, JsonAdapter
from notification import TexitSubscriberFilter, TexitMessageFormatter, TextitNotifier, TextitAgent, TextitErrorReporter
from scraper import DocumentFetcher, Scraper, DateTimeUpdater
from subscriber import SubscriberFactory, SubscriberMapper

formatter = logging.Formatter('%(asctime)s:%(name)s:%(funcName)s(): %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('app.log')
stream_handler = logging.StreamHandler()
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

target_class_names = 'post-6 page type-page status-publish hentry'
target_id_name = 'post-6'
html_element = 'article'
target_url = 'http://bit.lk/index.php/category/announcement/page/1'

scraper = Scraper()
fetcher = DocumentFetcher()
datetime_updater = DateTimeUpdater(fetcher, scraper)
database = db_connection()
factory = AnnouncementFactory()

try:
    stored_collection = AnnouncementMapper(database).get_recent_announcements(factory)
    subscribers = SubscriberMapper(JsonAdapter('./subscribers.json')).get_all_subscribers(SubscriberFactory())

    web_page = fetcher.fetch_document(target_url)
    web_collection = scraper \
        .set_html_document(web_page) \
        .extract_html(html_element, target_id_name, target_class_names) \
        .get_announcements(AnnouncementFactory())

    comparator = Comparator(web_collection, stored_collection, datetime_updater)
    comparator.check_for_new_announcements()
    logger.info('Are there any new announcements? {}'.format(comparator.is_any_announcement_new()))

    if comparator.is_any_announcement_new():
        new_collection = comparator.get_new_announcements()
        datetime_updater.update_all_datetime(new_collection)
        textit_notifier = TextitNotifier(
            new_collection,
            TexitMessageFormatter(),
            subscribers,
            TexitSubscriberFilter(),
            TextitAgent()
        )
        textit_notifier.notify()
        result = AnnouncementMapper(database).save_all(new_collection)

except:
    etype, value, tb = sys.exc_info()
    exc_type = traceback.format_exception_only(etype, value)
    logger.exception(traceback.extract_tb(tb))
    # print(exc_type[0], end='')  # end specified because new line
    logger.info(exc_type[0])

    logger.info('reporting termination...')
    TextitErrorReporter().send(exc_type[0])
    logger.info('terminating script')
    exit(1)
