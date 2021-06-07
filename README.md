# gnucash_pdb_update.py script

A simple Python script to automatically update Price Database of a Gnucash book, using gnucash's python bindings and yfinance library.

I developed this script for a personal need, since I was having trouble getting Gnucash's quotes download function to work and I got tired of adding new prices manualy each time I wanted to update the database.
I wanted to share the code here, since I believe that more people may be suffering from the same problem and may find this script usefull.

To use, just run the script in the command line, using "python gnucash_pdb_update.py <your_file.gnucash>"

The script goes through the commodities that are recorded in the book's price database, excluding the "template" and "CURRENCY" namespaces. It queries Yahoo Finance for the last close price of the different commodities and updates the database if the last value is not up-to-date.

It was writen assuming the book's default currency is EUR. If your book has a different default currency, it will be necessary to do some tweaks. I haven't had time to figure out a way to make the script more generic in this way. However, if you need to change it to your needs and if you need help with that, let me know.

I recommend doing a backup of your gnucash book before using this script for the first time, to make sure no important information is lost. Also, this script must only be run when the book is closed, to avoid any corruption of the file and/or database.

Please let me know if you find any problems and feel free to contribute with improvements.
