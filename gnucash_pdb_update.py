'''
Python script to automatically update Price Database of a Gnucash book,
using python bindings and yfinance library and web scrapping from morningstar

Developed by Filipe Pedro. Published on GitHub (https://github.com/fmpedro/gnucash_pdb_update)
'''

import yfinance as yf
from gnucash import Session
import gnucash
from fractions import Fraction
import datetime
import sys
import traceback

# Check if gnucash file was defined on script call:
if len(sys.argv) < 2:
    sys.exit("ERROR: You need to define the gnucash file to use \n(\"python gnucash_pdb_update.py <your_file.gnucash>)\"")

file = sys.argv[1]
book_curr = 'EUR' #change this if your book is in another currency (don't know way to get it from the book)


# connect to gnucash and access the price database and commodities table
session = Session(file, mode=0)
book = session.book
pdb = book.get_price_db()
comm_table = book.get_table()


# go through every commodity on price database (commodities organized by namespaces)
for namespace in comm_table.get_namespaces():
    if namespace == 'template': #skip non-relevant namespace
        continue
    else:
        # for each commodity of each namespace
        for comm in comm_table.get_commodities(namespace):
            mnemonic = comm.get_mnemonic() #symbol used to query yfinance
            fullname = comm.get_fullname() #full name defined in the price database
            
            if namespace == 'CURRENCY':
                if not comm.get_quote_flag():
                    continue #if the commodity is a currency without records in database, skip to next  
                else:
                    if mnemonic == book_curr:
                        continue #it it's the book's currency don't do anything
                    else:
                        mnemonic = book_curr + '=X' #changes currency mnemonic to format that yfinance understands
            try:
                ticker = yf.Ticker(mnemonic) #query yfinance for commodity
                ticker_price = ticker.history(period='1d').Close[-1] #get commodity's last close price
                ticker_price_date = ticker.history(period='1d').index[-1] #get commodity's last close price
                try:
                	ticker_curr = ticker.info['currency'] #get commodity's currency
                except: # if no data regarding currency is acquired, assume currency is EUR
                	ticker_curr = 'EUR'
                comm_curr = comm_table.lookup("CURRENCY", ticker_curr) #find commodity's currency on
                                                                       #commodities table for new price entry
                price_list=pdb.get_prices(comm,comm_curr) #get commodity's price list from database
                if price_list[0].get_time64() >= ticker_price_date: #only add new price if last one is outdated
                    print(mnemonic, '(', fullname, ')', 'is already updated...')
                else:
                    new_price = gnucash.GncPrice(instance = price_list[0].clone(book)) #clone price instance
                    new_price_value = new_price.get_value() #define price's value
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
                    print(mnemonic, '(', fullname, ')', 'price:', ticker_price, ticker_curr, 'updated!')
            except IndexError:
            	continue
            except Exception as error:
                print(mnemonic,': ',traceback.format_exc())
                continue


# end session
session.save()
session.end()
session.destroy()
print('Update completed!')