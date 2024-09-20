# pip install azure-kusto-data[pandas]
# pip install azure-kusto-ingest[pandas]
import os
import re
import argparse
import pandas as pd
from kusto_utils import KustoUtils, GREEN, CYAN, NO_COLOR

def get_kusto_schema(kc: KustoUtils) -> pd.DataFrame:
    cached_schema_filepath = kc.cluster_url + '_' + kc.database_name
    cached_schema_filepath = re.sub(r'[^A-Za-z0-9]', '_', cached_schema_filepath.replace('https://', ''))
    cached_schema_filepath += '.csv'
    if os.path.exists(cached_schema_filepath):
        print(f"{GREEN}Reading schema from {CYAN}{cached_schema_filepath}{NO_COLOR}")
        return pd.read_csv(cached_schema_filepath)
    print(f"{GREEN}Reading schema from kusto, this may take a while{NO_COLOR}")
    sc = kc.get_kusto_database_schema()
    sc.to_csv(cached_schema_filepath, index=False)
    return sc

def main(cluster_url: str, database: str, term: str, schema_filter_in_pandas_format:str) -> None:
    print(f"{GREEN}Connecting to {CYAN}{cluster_url}.{database}{NO_COLOR}")
    kc = KustoUtils(cluster_url=cluster_url, database_name=database)
    sc = get_kusto_schema(kc)
    sc = sc.query(schema_filter_in_pandas_format)[['TableName', 'ColumnName']]
    if not re.match('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', term):
        sc.query('not (ColumnName.str.endswith("id") or ColumnName.str.endswith("Id") or ColumnName.str.endswith("ID"))', inplace=True)
    sc.sort_values(by=['TableName', 'ColumnName'], inplace=True)
    query = "union \n"
    columnQueries = ",\n".join([f"(print Table='{r.TableName}', Column='{r.ColumnName}', Found = toscalar({r.TableName} | where ['{r.ColumnName}'] has '{term}' | count))" for r in sc.itertuples()])
    query += columnQueries + "\n;"
    with open('search_on_all_kusto_tables_and_columns_query.kql', 'w') as f:
        f.write(query)
    print(f"{GREEN}Searching {CYAN}{term}{GREEN} on all tables and columns, this may take a while{NO_COLOR}")
    df = kc.query(query)
    print(f"{GREEN}Finished searching{NO_COLOR}")
    columns_with_the_term = df.query('Found > 0')
    print(columns_with_the_term.head(columns_with_the_term.shape[0]))
    output_csv_file = f'search_on_all_kusto_tables_and_columns_with_term_{re.sub(r"[^A-Za-z0-9]", "_", term)}.csv'
    print(f"{GREEN}Saving results to {CYAN}{output_csv_file}{NO_COLOR}")
    columns_with_the_term.to_csv(output_csv_file, index=False)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--cluster-url', type=str, required=True)
    parser.add_argument('-d', '--database', type=str, required=True)
    parser.add_argument('-t', '--term', type=str, default='.*', required=True)
    parser.add_argument('-s', '--schema-filter-in-pandas-format', type=str, default='not (TableName.str.contains("temp") or TableName.str.contains("Temp") or TableName.str.contains("TEMP") or ColumnType != "System.String")', required=False, help='Pandas query format to filter the schema, query format can be found here: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.query.html')
    args = parser.parse_args()
    main(args.cluster_url, args.database, args.term, args.schema_filter_in_pandas_format)
