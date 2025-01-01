'''
Python script to automatically update Price Database of a Gnucash book,
using piecash and yfinance library, coincodex API and web scrapping
from the web.
Will not work for XML gnucash files. Tested with sqlite3 files.
Developed by Filipe Pedro.
Published on GitHub (https://github.com/fmpedro/gnucash_pdb_update)
'''

import yfinance as yf
import piecash
from datetime import datetime
import sys
import traceback
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup as bs
import logging
import re
import os
from dotenv import load_dotenv 
from decimal import Decimal, ROUND_HALF_UP
import warnings
warnings.filterwarnings("ignore")

load_dotenv()
api_key = os.getenv("COINGECKO_API_KEY")

# Configure logging:
logging.captureWarnings(True)
logging.basicConfig(
    level=logging.INFO, #    filename='gnucash_pdb_update.log',
    format='%(asctime)s | %(levelname)s - %(message)s')


# gets convertion rate of 'ticker' to usd
def get_crypto_price(ticker, curr):
    url = f'https://api.coingecko.com/api/v3/coins/{ticker}'
    headers = { "x-cg-demo-api-key": api_key }
    response = requests.get(url, headers=headers)
    if response.ok:
        return json.loads(response.text)['market_data']['current_price'][curr.lower()]
    else:
        return 0

def get_rate2usd(ticker):
    url = 'https://coincodex.com/api/coincodex/get_coin/' + ticker
    response = requests.get(url)
    data = json.loads(response.text)
    return data['last_price_usd']


# Check if gnucash file was defined on script call:
if len(sys.argv) < 2:
    sys.exit('''ERROR: You need to define the gnucash file to use
                ("python gnucash_pdb_update.py <your_file.gnucash>)''')

file = sys.argv[1]

# connect to gnucash and access the price database and commodities table
with piecash.open_book(file, readonly=False) as book:
    
    # get book's default currency
    book_curr = book.default_currency

    # get all commodities and convert them into a dataframe
    comms = []
    comms.extend([{'namespace': comm.namespace,
                   'mnemonic': comm.mnemonic,
                   'fullname': comm.fullname,
                   'cusip': comm.cusip,
                   'quote_flag': comm.quote_flag,
                   'fraction': comm.fraction} for comm in book.commodities])
    comms_df = pd.DataFrame(comms)

    namespaces = comms_df.namespace.unique()

    # go through every commodity on price database, by namespace
    logging.info(f'Gnucash Price Database update started...')
    # cleanup any price entries with value 0: 
    [book.delete(book.prices(guid=price.guid)) for price in book.prices if price._value_num == 0]

    for namespace in namespaces:
        if namespace == 'template':  # skip non-relevant namespace
            continue
        else:
            print('== Namespace: ' + namespace + ' ==')
            # for each commodity of each namespace
            comm_table = comms_df[comms_df['namespace']==namespace]

            for comm_row in comm_table.itertuples():
                mnemonic = comm_row.mnemonic
                fraction = comm_row.fraction
                commodity = book.commodities(mnemonic=mnemonic)
                # get price list:
                price_list = [price for price in book.prices if price.commodity.mnemonic == mnemonic]
                price_list.sort(key=lambda price: price.date, reverse=True)

                if namespace == 'CURRENCY':
                    if not comm_row.quote_flag:
                        # if the comm is a currency w/o records in db, skip to next
                        continue
                    else:
                        if comm_row.mnemonic == book_curr.mnemonic:
                            # it it's the book's currency don't do anything
                            continue
                        else:
                            # changes currency mnemonic to format that yfinance understands
                            mnemonic = book_curr.mnemonic + '=X'

                try:
                    if namespace == 'CRYPTO':  # get prices of cryptocurrencies
                        # get price of ticket in the book's currency
                        ticker_price = get_crypto_price(mnemonic, book_curr.mnemonic)
                        ticker_price_date = datetime.today().date()
                        ticker_curr = book_curr.mnemonic

                    # get prices from BancoInvest website
                    elif namespace == 'BANCOINVEST':
                        url = '''https://www.morningstar.pt/pt/funds/snapshot/snapshot.aspx?id=''' + mnemonic
                        url = url.strip().replace(" ", "").replace("\n", "")

                        response = requests.get(url, verify=True)
                        soup = bs(response.content, 'lxml')
                        ticker_array = soup.find(id="overviewQuickstatsDiv").text.split("\xa0")
                        ticker_curr = ticker_array[1]
                        ticker_array = [re.sub("[^0-9/.]","",i) for i in ticker_array]
                        ticker_price = float(ticker_array[2])
                        ticker_price_date = datetime.strptime(ticker_array[0], "%d/%m/%Y").date()

                    # get prices of assests in yfinance
                    else:
                        ticker = yf.Ticker(mnemonic)  # query yfinance for commodity
                        ticker_price = ticker.history(period='1d').Close.iloc[-1]  # get commodity's last close price
                        ticker_price_date = ticker.history(period='1d').index[-1].date()  # get commodity's last close price date
                        try:
                            ticker_curr = ticker.fast_info['currency']  # get commodity's currency
                        except:
                            # if no data regarding currency is acquired, assume currency
                            ticker_curr = 'XXX'

                    # Create new price entry in Price Database
                    if len(price_list) > 0:
                        curr = price_list[0].currency
                        if price_list[0].date >= ticker_price_date:  # only add new price if last one is outdated
                            print(mnemonic, '(', comm_row.fullname, ')', 'is already updated...')
                            skip = True
                        else:
                            skip = False
                    else:
                        curr = book_curr
                        skip = False

                    # create the new price:
                    if not skip:
                        new_price = piecash.Price(commodity = commodity, date = ticker_price_date, value=Decimal(ticker_price).quantize(Decimal(str(1/fraction)), rounding=ROUND_HALF_UP), currency = curr, type='last')
                        book.add(new_price)
                        print(mnemonic, '(', comm_row.fullname, ')', 'price:', ticker_price, ticker_curr,'date:', ticker_price_date, 'updated!')

                except IndexError:
                    logging.warning(f'IndexError when updating price of {comm_row.fullname}')
                    continue
                except Exception as error:
                    logging.error(f'Error retrieving price of {comm_row.fullname}... \n Error:\n{traceback.format_exc()}')
                    print(mnemonic, ': ', error)
                    continue

    # save changes
    try:
        book.save()
        logging.info(f'Gnucash Price Database update completed!')
        print('Update completed!')
    except Exception as error:
        logging.error(f'Error when saving data to gnucash database... \n Error:\n{traceback.format_exc()}')
        print('Error when saving data to gnucash database: ', error)
