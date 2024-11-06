#!/bin/bash

source .venv/bin/activate
python gnucash_pdb_update.py ../gnucash/gnucash_fmpedro/gnucash_fmpedro.gnucash
deactivate
