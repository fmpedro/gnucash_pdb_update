#!/bin/bash

source .venv/bin/activate
python gnucash_pdb_update.py ../gnucash/gnucash_fmpedro/gnucash_fmpedro.sqlite3.gnucash
deactivate