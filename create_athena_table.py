#!/usr/bin/env python3
import boto3
import os
import pyarrow
from pyarrow.parquet import ParquetFile
from pyathena import connect
import random
import re
import sys

def get_command_line_option(name:str, default:str = '') -> str:
    pattern = re.compile(f'^--{name}=(.*)$')
    option = [opt for opt in sys.argv[1:] if pattern.match(opt)]
    if option:
        return pattern.match(option[0]).group(1)
    else:
        return default
    
def get_bucket_name_and_prefix(s3_uri:str):
    match = re.match('s3://([^/]+)/(.*)$', s3_uri)
    if not match:
        raise ValueError(f'S3 URI is invalid: {s3_uri}')
    return match.group(1), match.group(2)
    
def explain_then_exit() -> None:
    print('''
create_athena_table.py --profile-name=PROFILE_NAME --s3-uri=S3_URI --database-name=DATABASE_NAME --table-name=TABLE_NAME --region-name=REGION_NAME [--data-catalog=DATA_CATALOG] [--athena-results-s3-bucket=ATHENA_RESULTS_S3_BUCKET_URI]
Creates an Athena DB table in an already existing database, with the data from parquet files located on an S3 bucket.
* PROFILE_NAME: is the AWS credential profile name.
* S3_URI: is the source for parquet files to be used to create the Athena table.
* DATABASE_NAME: name of an existing Athena database.
* TABLE_NAME: name of the table being created.
* REGION_NAME: name of the region where the database resides.
* DATA_CATALOG: Optional: name of the data catalog. Default is AwsDataCatalog
* ATHENA_RESULTS_S3_NAME: Optional: URI of the S3 bucket configured for Athena results. 
Example:
create_athena_table.py --profile-name=my_profile --s3-uri=s3://my-bucket/path/to/some/parquets/ --database-name=mydb --table-name=pqtdata --region-name=eu-central-1
    ''')
    exit(1)

def get_column_definition(column:pyarrow._parquet.ColumnSchema) -> str:
    name          = column.name
    logical_type  = str(column.logical_type).upper()
    physical_type = str(column.physical_type).upper()
    precision     = column.precision
    scale         = column.scale
    athena_type   = 'binary'
    if logical_type == 'STRING':
        athena_type = 'string'
    if logical_type == 'NONE' and physical_type == 'INT96':
        athena_type = 'timestamp'
    if logical_type == 'NONE' and physical_type == 'INT64':
        athena_type = 'bigint'
    if logical_type == 'NONE' and physical_type == 'INT32':
        athena_type = 'int'
    if logical_type == 'NONE' and physical_type == 'BOOLEAN':
        athena_type = 'boolean'
    if logical_type.startswith('DECIMAL'):
        athena_type = f'decimal({precision},{scale})'
    if logical_type.startswith('DECIMAL'):
        athena_type = f'decimal({precision},{scale})'
    if logical_type.startswith('DECIMAL'):
        athena_type = f'decimal({precision},{scale})'        
    definition = f'`{name}` {athena_type}'
    return definition
    
def get_column_definitions(schema:pyarrow._parquet.ParquetSchema) -> str:
    columns_descriptors = [get_column_definition(schema.column(i)) for i in range(len(schema.names))]
    columns_descriptors_sql_format = ", ".join(columns_descriptors)
    return columns_descriptors_sql_format

def get_athena_results_s3_bucket(s3:object) -> str:
    buckets = s3.list_buckets()
    candidates = [b['Name'] for b in buckets['Buckets'] if 'athena-results' in  b['Name'].lower()]
    if len(candidates) == 1:
        return f's3://{candidates[0]}'
    raise ValueError('Could not find an Athena results S3 bucket. Please inform one with the --athena-results-s3-bucket option.')

if any(re.match('^(-h|--help|-\?|--\?)$', arg) for arg in sys.argv[1:]):
    explain_then_exit()

profile_name  = get_command_line_option('profile-name')
s3_uri        = get_command_line_option('s3-uri')
database_name = get_command_line_option('database-name')
table_name    = get_command_line_option('table-name')
region_name   = get_command_line_option('region-name')
athena_results_s3_bucket = get_command_line_option('athena-results-s3-bucket')
data_catalog  = get_command_line_option('data-catalog', 'AwsDataCatalog')
if profile_name == '' or database_name == '' or table_name == '' or s3_uri == '' or region_name == '':
    explain_then_exit()
    
bucket_name, prefix = get_bucket_name_and_prefix(s3_uri)
s3 = boto3.Session(profile_name = profile_name, region_name=region_name).client('s3')
if athena_results_s3_bucket == '':
    athena_results_s3_bucket = get_athena_results_s3_bucket(s3)

athena = boto3.Session(profile_name = profile_name, region_name=region_name).client('athena')

objects = s3.list_objects(Bucket = bucket_name, Prefix = prefix)
parquet_name = random.choice([o['Key'] for o in objects['Contents'] if o['Key'].endswith('.parquet')])
    
download_path = os.path.join(os.environ['HOME'], 'Downloads/d.parquet')
if os.path.exists(download_path):
    os.remove(download_path)
s3.download_file(bucket_name, parquet_name, download_path)
schema = ParquetFile(download_path).schema
os.remove(download_path)
column_definitions = get_column_definitions(schema)
create_statement = '''
CREATE EXTERNAL TABLE IF NOT EXISTS `#database_name#`.`#table_name#` (#column_definitions#)
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat' OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION '#s3_uri#'
TBLPROPERTIES ('classification' = 'parquet');
'''
create_statement = create_statement.replace('#database_name#',      database_name)
create_statement = create_statement.replace('#table_name#',         table_name)
create_statement = create_statement.replace('#column_definitions#', column_definitions)
create_statement = create_statement.replace('#s3_uri#',             s3_uri)

cursor = connect(s3_staging_dir=athena_results_s3_bucket, region_name=region_name, profile_name=profile_name).cursor()
cursor.execute(create_statement)
cursor.close()


