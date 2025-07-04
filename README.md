# Gnucash Price Database Updater (gnucash_pdb_update.py)

## Summary
A simple Python script to automatically update Price Database of a Gnucash book, using ~~gnucash's python bindings~~ piecash, yfinance, coincodex API and webscraping.

I developed this script for a personal need, since I was having trouble getting Gnucash's quotes download function to work and I got tired of adding new prices manualy each time I wanted to update the database.
I wanted to share the code here, since I believe that more people may be suffering from the same problem and may find this script usefull.

To use, just run the script in the command line, using "python gnucash_pdb_update.py <your_file.gnucash>"

The script goes through the commodities that are recorded in the book's price database, excluding the "template" namespace. It queries Yahoo Finance and Morningstar API for the last close price of the different commodities and updates the database if the last value is not up-to-date.

## Installation/Initial Setup
*(credit to @kenkeiras for helping with some of the setup through the instructions provided in this blog post: https://codigoparallevar.com/blog/2023/programmatic-access-to-gnucash-using-python)*

You need to have gnucash installed in your machine, as well as its Python Bindings (python3-gnucash) for the script to work.

The library requirements can be found in the *requirements.txt* file in this repository.

**Due to some incompatibilities with later python versions and some of the needed libraries, I recommend using python 3.11 to run the script.**

If you want to use a virtual environment to run it, create using the python 3.11 version (Ex: `python3.11 -m venv .venv`). You will also need to move the python bindings inside it. For that either run 
`cp -r /usr/lib/python3.*/site-packages/gnucash .venv/lib/python3.*/site-packages/gnucash`

**Note: Since the conversion of the script to use piecash, installation of the gnucash bindings is no longer required. However, your gnucash file needs to be saved as a sqlite3 file.**

## Additional Information and Recommendations
I recommend doing a backup of your gnucash book before using this script for the first time, to make sure no important information is lost. Also, this script must only be run when the book is closed, to avoid any corruption of the file and/or database.

Please let me know if you find any problems and feel free to contribute with improvements.
