#!/usr/bin/env python3
import concurrent.futures
import csv
import glob
import os
import pyarrow.parquet as pq
import re
import sys
from datetime import datetime, timedelta
from typing import List

def convert(file_path:str) -> str:
    csv_file_path = file_path.replace('.parquet', '.csv')
    table = pq.read_metadata(file_path)
    fieldnames = table.schema.names
    parquet = pq.read_table(file_path, use_threads=True).to_pylist()
    with open(csv_file_path, 'w') as f:
        cw = csv.DictWriter(f, fieldnames = fieldnames)
        cw.writeheader()
        cw.writerows(parquet)
    return csv_file_path

def execute_multithreaded(fct, parameters_list : List[List[object]], max_workers: int = int(os.cpu_count() * 2 / 3)) -> List[object]:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = { executor.submit(fct, *params): params for params in parameters_list }
        for future in concurrent.futures.as_completed(futures):
            result   = future.result()
            results.append(result)
    return results


path   = sys.argv[1]
multithread = len(sys.argv) > 2 and sys.argv[2].lower()[0:4] == 'mult'
start = datetime.now()

if glob.os.path.isdir(path):
    filter = glob.os.path.join(path, '*.parquet')
    file_paths = glob.glob(filter)
    if multithread:
        file_paths = [[p] for p in file_paths]
        execute_multithreaded(convert, file_paths)
    else:
        for file_path in file_paths:
            convert(file_path)

if glob.os.path.isfile(path):
    convert(path)

print(datetime.now() - start)
