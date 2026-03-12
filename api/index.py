import sys
import os

# Aggiungi la root directory al path per permettere i package imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app

# Vercel needs the instance named 'app'
