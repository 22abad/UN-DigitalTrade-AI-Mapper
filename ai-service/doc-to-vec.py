# read the chunks from db, do embedding
import os
import urllib.parse
import psycopg2
import argparse
from transformers import AutoTokenizer, AutoModel
import numpy as np
import torch

