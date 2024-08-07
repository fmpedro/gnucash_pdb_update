'''
Python script to automatically update Price Database of a Gnucash book,
using python bindings and yfinance library, coincodex API and web scrapping
from morningstar.
Developed by Filipe Pedro.
Published on GitHub (https://github.com/fmpedro/gnucash_pdb_update)
'''

import yfinance as yf
from gnucash import Session
import gnucash
from fractions import Fraction
from datetime import datetime
import sys
import traceback
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup as bs
import logging
import re


# Configure logging:
logging.captureWarnings(True)
logging.basicConfig(
    level=logging.INFO,
    filename='gnucash_pdb_update.log',
    format='%(asctime)s | %(levelname)s - %(message)s')


# gets convertion rate of 'ticker' to usd
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

# change the following if your book is in another currency
# (I don't know of a way to get it from the book):
book_curr = 'EUR'


# connect to gnucash and access the price database and commodities table
session = Session(file, mode=0)
book = session.book
pdb = book.get_price_db()
comm_table = book.get_table()


# go through every commodity on price database
# (commodities organized by namespaces)
logging.info(f'Gnucash Price Database update started...')
for namespace in comm_table.get_namespaces():
    if namespace == 'template':  # skip non-relevant namespace
        continue
    else:
        print('== Namespace: ' + namespace + ' ==')
        # for each commodity of each namespace
        for comm in comm_table.get_commodities(namespace):
            mnemonic = comm.get_mnemonic()  # symbol used to query yfinance
            fullname = comm.get_fullname()  # full name in the price database
            cusip = comm.get_cusip()  # ISIN/CUSIP used in the price database

            if namespace == 'CURRENCY':
                if not comm.get_quote_flag():
                    # if the comm is a currency w/o records in db, skip to next
                    continue
                else:
                    if mnemonic == book_curr:
                        # it it's the book's currency don't do anything
                        continue
                    else:
                        # changes currency mnemonic to format that yfinance understands
                        mnemonic = book_curr + '=X'

            try:
                if namespace == 'CRYPTO':  # get prices of cryptocurrencies
                    # get price of ticket in USD
                    mnemonic2usd = get_rate2usd(mnemonic)

                    # if book is in USD, no conversion required. Else, convert
                    if book_curr == 'USD':
                        book_curr2usd = 1
                    elif book_curr == 'EUR':
                        book_curr2usd = get_rate2usd('EURS')

                    ticker_price = mnemonic2usd / book_curr2usd
                    ticker_price_date = pd.Timestamp(datetime.now())
                    ticker_curr = book_curr

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
                    ticker_price_date = pd.Timestamp(datetime.strptime(ticker_array[0], "%d/%m/%Y"))

                # get prices of assests in yfinance
                else:
                    ticker = yf.Ticker(mnemonic)  # query yfinance for commodity
                    ticker_price = ticker.history(period='1d').Close.iloc[-1]  # get commodity's last close price
                    ticker_price_date = ticker.history(period='1d').index[-1]  # get commodity's last close price date
                    try:
                        ticker_curr = ticker.fast_info['currency']  # get commodity's currency
                    except:
                        # if no data regarding currency is acquired, assume currency
                        ticker_curr = 'XXX'

                # Create new price entry in Price Database
                comm_curr = comm_table.lookup("CURRENCY", ticker_curr)  # find commodity's currency on commodities table for new price entry
                price_list = pdb.get_prices(comm,comm_curr)  # get commodity's price list from database
                if len(price_list) > 0:
                    # First cleanup any price entries with value 0:         
                    for entry in price_list:
                        if entry.get_value().num == 0:
                            pdb.remove_price(entry)
                    # Create the new price:
                    if price_list[0].get_time64() >= ticker_price_date.replace(tzinfo=None):  # only add new price if last one is outdated
                        print(mnemonic, '(', fullname, ')', 'is already updated...')
                    else:
                        new_price = gnucash.GncPrice(instance = price_list[0].clone(book))  # clone price instance
                        new_price_value = new_price.get_value()  #define price's value
                        # change numerator and denominator of price's value:
                        comm_fract = comm.get_fraction()
                        new_price_value.num = int(Fraction.from_float(ticker_price).limit_denominator(comm_fract).numerator)
                        new_price_value.denom = int(Fraction.from_float(ticker_price).limit_denominator(comm_fract).denominator)
                        # change new price's parameters and add to database:
                        new_price.set_value(new_price_value)
                        new_price.set_time64(ticker_price_date)
                        new_price.set_source(0)
                        new_price.set_typestr('last')
                        pdb.add_price(new_price)
                        print(mnemonic, '(', fullname, ')', 'price:', ticker_price, ticker_curr,'date:', ticker_price_date, 'updated!')
                else:
                    print(mnemonic, '(', fullname, ')', f'has no entries with {ticker_curr} currency...')
            except IndexError:
                logging.warning(f'IndexError when updating price of {fullname}')
                continue
            except Exception as error:
                logging.error(f'Error retrieving price of {fullname}... \n Error:\n{traceback.format_exc()}')
                print(mnemonic, ': ', error)
                continue

# end session
session.save()
session.end()
session.destroy()
logging.info(f'Gnucash Price Database update completed!')
print('Update completed!')
