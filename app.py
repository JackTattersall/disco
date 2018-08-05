import sys

import os

import csv
import requests
from bs4 import BeautifulSoup
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional, Tuple

from time import sleep

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
sleep_for = 15


def go(url: str, acceptable_price: Optional[int]) -> Tuple[bool, str]:
    try:
        html_doc = requests.get(url)
        page = BeautifulSoup(html_doc.text, 'html.parser')
        is_listed = is_for_sale(page)
        price = get_price(page)

        if is_listed:
            if acceptable_price:
                if is_acceptable_price(acceptable_price, price):
                    return True, '{} has been listed, price from {}'.format(url, price)
                else:
                    return False, 'Listed at {}, but price to high, at {}'.format(price, acceptable_price)

            else:
                return True, '{} has been listed, price from {}'.format(url, price)
        else:
            return False, '{} Not listed'.format(url)

    except Exception as e:
        logger.error(e)


class MyWant:
    def __init__(self, record_url, price, active: str):
        self.record_url = record_url
        self.price = int(price) if price != 'None' else None
        self.active = active.lower() == 'true'


def read_wants():
    with open('urls.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        my_wants = [MyWant(row[0], row[1], row[2]) for row in reader]
        return my_wants


def send_email(body: str):
    msg = MIMEText(body)
    msg['Subject'] = 'Discogs Watcher'
    msg['From'] = 'Discogs@Watcher.com'
    msg['To'] = 'graeme.parvin@sky.com'

    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.login()
    s.send_message(msg)
    s.quit()


def get_price(page: BeautifulSoup):
    try:
        market_place = page.find('span', class_='marketplace_for_sale_count')
        actual_price = market_place.span.string
        return actual_price
    except Exception as e:
        # logger.error('Could not retrieve price, {}'.format(e))
        return '£0.00'


def is_for_sale(page: BeautifulSoup):
    try:
        market_place = page.find('span', class_='marketplace_for_sale_count')
        count = market_place.a.strong.string
        return True
    except Exception:
        return False


def is_acceptable_price(acceptable_price: int, actual_price: str):
    parsed_actual_price = int(actual_price[1:].split('.')[0])
    return parsed_actual_price < acceptable_price


# def run_test():
#     logger.info('Running test against {}'.format(control))
#     match, msg = go(control, None)
#     logger.info(msg)
#     logger.info('Sleeping for {} seconds'.format(sleep_for))
#     sleep(sleep_for)


class MyWants:
    def __init__(self, record_url: str, active: str, price_i_will_pay: str):
        self.record_url = record_url
        self.active = active.lower() == 'true'
        self.price_i_will_pay = None if price_i_will_pay.lower() == 'none' else int(price_i_will_pay)


def get_my_wants():
    file_path = os.path.join(os.path.dirname(sys.argv[0]), 'wants.csv')
    with open(file_path) as wants_csv:
        reader = csv.reader(wants_csv)
        next(reader)
        return [MyWants(want[0], want[2], want[1]) for want in reader]


if __name__ == '__main__':
    # run_test()
    logger.info(os.getcwd())

    logger.info('Start polling my wants')
    wants = get_my_wants()
    while True:
        try:
            for want in filter(lambda x: x.active, wants):

                match, msg = go(want.record_url, want.price_i_will_pay)
                logger.info(msg)

                if match:
                    send_email(msg)
                    want.active = False

                logger.info('Sleeping for {} seconds'.format(sleep_for))
                sleep(sleep_for)
        except Exception as e:
            logger.error(e)
            break
