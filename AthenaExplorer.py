"""
Athena Explorer

You will need to install these packages:
pip install boto3
pip install numpy
pip install pandas
pip install pyathena
pip install streamlit

How to use it:
* Open a command prompt.
* Authenticate with AWS.
* Either use a named profile during authentication or switch to a profile before going to the next step.
* Run streamlit run AthenaExplorer.py.

What it does:
* Execute SQL statements against an Athena database.
* Display the results in a grid.
* Saves the results in a csv, json and a parquet file.
* Allows creation of charts, provided the results have specific criteria:
    * For Line Chart: First column must be string or date, other columns must be the same numeric type. Less than 128 rows.
    * For Pie Chart: First column must be string, other columns must be the same numeric type. Less than 32 rows.
* To be done:
    * Histogram charts.
    * Marginal histogram charts.
    * Create a view with the latest query statement.
    * Testing of uploading results to S3.
    * Testing of creation of Athena table.
"""
import boto3
import json
import numpy as np
import os
import pandas as pd
import re
import streamlit as st
from pyathena import connect
from typing import List, Dict

def ss(key:str, default:object = None) -> object:
    if key in st.session_state.keys():
        return st.session_state[key]
    return default

def nth_column_values(data:pd.DataFrame, column_index: int) -> List[object]:
    return [e[0] for e in data[[data.columns.values[column_index]]].values]

def numpy_numberic_types() -> List[type]:
    return [
        type(0.0), 
        type(0),
        type(np.byte(0)),
        type(np.cdouble(0)),
        type(np.cfloat(0)),
        type(np.double(0)),
        type(np.float128(0)),
        type(np.float16(0)),
        type(np.float32(0)),
        type(np.float64(0)),
        type(np.int0(0)),
        type(np.int16(0)),
        type(np.int32(0)),
        type(np.int64(0)),
        type(np.int8(0)),
        type(np.intc(0)),
        type(np.longdouble(0)),
        type(np.longfloat(0)),
        type(np.longlong(0)),
        type(np.short(0)),
        type(np.uint(0)),
        type(np.uint0(0)),
        type(np.uint16(0)),
        type(np.uint32(0)),
        type(np.uint64(0)),
        type(np.uint64(0)),
        type(np.uint8(0)),
        type(np.uintc(0)),
        type(np.uintp(0)),
        type(np.ulonglong(0)),
        ]
    
def numpy_label_types() -> List[type]:
    return [
        type('str'), 
        type(np.datetime64()),
        ]
    
def get_column_types() -> List[type]:
    data         = ss('LATEST_DATAFRAME')
    if data is None:
        return []
    
    column_types = []

    for i in range(len(data.columns)):
        values = nth_column_values(data, i)
        types  = set([type(e) for e in values])
        if len(types) > 1:
            return []
        column_types += types
    return column_types
    
def current_dataframe_row_count() -> int:
    data         = ss('LATEST_DATAFRAME')
    if data is None:
        return 0
    return len(data.values)

def get_current_dataframe_types():
    column_types = get_column_types()
    label_types  = numpy_label_types()
    value_types  = numpy_numberic_types()
    return column_types, label_types, value_types
    
def can_render_pie_chart() -> bool:
    column_types, label_types, value_types = get_current_dataframe_types()
    if len(column_types) != 2:
        return False
    return column_types[0] in label_types and column_types[1] in value_types and current_dataframe_row_count() < 32

def can_render_line_chart() -> bool:
    column_types, label_types, value_types = get_current_dataframe_types()
    if len(column_types) < 2:
        return False
    if column_types[0] in label_types:
        if all(t in value_types for t in column_types[1:]):
            return current_dataframe_row_count() < 128
    return False

def can_render_histogram_chart() -> bool:
    column_types, _, value_types = get_current_dataframe_types()
    return len(column_types) >= 1 and all(t in value_types for t in column_types)

def can_render_marginal_histogram_chart() -> bool:
    column_types, _, value_types = get_current_dataframe_types()
    return len(column_types) == 2 and all(t in value_types for t in column_types)

def check(key:str, regex_pattern: str) -> bool:
    value = ss(key)
    is_valid = value is not None and re.match(regex_pattern, value) != None
    return is_valid

def file_to_string_list(file_path:str) -> List[str]:
    with open(file_path, 'r') as f:
        return [p.replace('\n','') for p in f.readlines()]
    
def list_to_file(l: List[object], file_path:str) -> None:
    text_to_file("\n".join([str(item) for item in l]), file_path)

def file_to_text(file_path:str) -> str:
    with open(file_path, 'r') as f:
        return f.read()

def text_to_file(content: str, file_path:str) -> None:
    with open(file_path, 'w') as f:
        f.write(content)

def serialize(obj: object) -> str:
    return json.dumps(obj, sort_keys=False, indent=4)

def serialize_to_file(obj: object, file_path:str) -> None:
    text_to_file(serialize(obj), file_path)

def deserialize_from_file(file_path:str) -> object:
    return json.loads(file_to_text(file_path))

def get_bucket_name_and_prefix(s3_uri:str):
    match = re.match('s3://([^/]+)/(.*)$', s3_uri)
    if not match:
        raise ValueError(f'S3 URI is invalid: {s3_uri}')
    return match.group(1), match.group(2)

def populate_session_state_if_needed() -> None:
    print(f'populate_session_state_if_needed {st.session_state}')
    rn = ss('REGION_NAME')
    if rn is None or rn == '':
        if os.path.exists('AthenaExplorer.json'):
            state = json.loads(file_to_text('AthenaExplorer.json'))
            for key in state.keys():
                st.session_state[key] = state[key]
                
def save_session_state() -> None:
    state = {}
    string_type = type(' ')
    for key in st.session_state.keys():
        value = st.session_state[key]
        if type(value) == string_type:
            state[key] = st.session_state[key]
    text_to_file(json.dumps(state, sort_keys=False, indent=4),  'AthenaExplorer.json')

def read_sql_query(statement:str, conn:object) -> pd.DataFrame:
    try:
        df = pd.read_sql_query(statement, conn)
        return df
    except Exception as e:
        if 'security token' in str(e).lower():
            st.warning('Security token not found or expired. \nPlease refresh your credentials. \nMake sure you use the --profile option for ada credentials update. \nEnsure that you are using the same profile name from ada credentials on the "Profile Name" field.')
        else:
            st.warning(e)

def render_line_chart() -> None:
    if ss('LATEST_DATAFRAME') is not None:
        with ss('charts_expander'):
            columns = list(ss('LATEST_DATAFRAME').columns)
            x_column_name = columns[0]
            y_column_names = columns[1:]
            st.line_chart(ss('LATEST_DATAFRAME'), x=x_column_name, y=y_column_names)

def basic_vega_lite_chart_spec() -> Dict[str, object]:
    return {
        '$schema': 'https://vega.github.io/schema/vega-lite/v5.json',
        'description': '',
        'data': { 'values': [ ] },
        'layer': [
            {

                #'data': { 'url': 'file://' + ss('LATEST_DATAFRAME_JSON_PATH') },
                'encoding': {
                    'theta': {'field': 'value', 'type': 'quantitative'},
                    'color': {'field': 'category', 'type': 'nominal'}
                }
            }
        ]
    }  

def render_pie_chart() -> None:
    data = ss('LATEST_DATAFRAME')
    if data is not None:
        chart_spec = basic_vega_lite_chart_spec()
        chart_spec['layer'][0]['mark'] = 'arc'
        for row in data.values:
            value = {'category':row[0], 'value':row[1]}
            chart_spec['data']['values'].append(value)
        with ss('charts_expander'):   
            st.vega_lite_chart(spec=chart_spec)
            
def render_histogram() -> None:
    data = ss('LATEST_DATAFRAME')
    if data is not None:
        min_value = data.min(numeric_only=True).min()
        max_value = data.max(numeric_only=True).max()
        histogram_bin_count = int(ss('HISTOGRAM_SIZE'))
        bins = [round(n,2) for n in np.linspace(min_value, max_value, histogram_bin_count + 1)]
        histograms = [{'Bin':bin} for bin in bins[:-1]]
        for column_name in data.columns:
            values = [v for v in data[column_name].values.tolist() if v == v]
            binned_values = np.histogram(values, bins=bins)[0]
            for i in range(histogram_bin_count):
                histograms[i][column_name] = int(binned_values[i])
        chart_spec = basic_vega_lite_chart_spec()
        serialize_to_file(histograms, os.path.join(os.environ['HOME'], 'latest_histogram.json'))
        chart_spec['data'] = histograms
        chart_spec['opacity'] = 0.6
        colors = ['red', 'green', 'blue', 'yellow', 'gray', 'orange', 'gold', 'darkblue', 'darkgreen']
        for i in range(len(data.columns)):
            chart_spec['layer'].clear()
            column_name = data.columns[i]
            color = colors[i%len(colors)]
            layer_spec = {
                'mark': 'bar',
                'encoding': {
                    'x': { 'field': 'Bin', 'type': 'nominal'},
                    'y': { 'field': column_name, 'type': 'quantitative'},
                    'color': {'value': color}
                }
            }
            chart_spec['layer'].append(layer_spec)
            with ss('charts_expander'):   
                st.vega_lite_chart(spec=chart_spec)    

        
def render_marginal_histogram() -> None:
    with ss('charts_expander'):
        st.write('Not implemented yet') 

def create_view_with_query_results() -> None:
    st.write('Not implemented yet') 

def save_dataframe_if_needed() -> None:
    if st.session_state['LATEST_DATAFRAME'] is not None:
        ss('LATEST_DATAFRAME').to_csv(ss('LATEST_DATAFRAME_CSV_PATH'))
        
        as_dict = json.loads(ss('LATEST_DATAFRAME').to_json(path_or_buf=None, orient='table', index=False))
        serialize_to_file(as_dict['data'], ss("LATEST_DATAFRAME_JSON_PATH"))
        
        save_session_state()
        fixline = re.compile('^[0-9]*,(.*)\n*')
        lines = [fixline.match(p).group(1) for p in file_to_string_list(ss("LATEST_DATAFRAME_CSV_PATH"))]  
        list_to_file(lines, ss("LATEST_DATAFRAME_CSV_PATH"))
        parquet_path = ss("LATEST_DATAFRAME_CSV_PATH").replace(".csv",".parquet")
        ss('LATEST_DATAFRAME').to_parquet(parquet_path)
        st.text(f'Results stored at: {ss("LATEST_DATAFRAME_CSV_PATH")}, {ss("LATEST_DATAFRAME_JSON_PATH")}, {parquet_path}')
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("View name:", key="TARGET_VIEW_NAME")
        with col2:
            st.button('Create view with query results', on_click=create_view_with_query_results)    


def run_query() -> None:
    region_name_check    = check("REGION_NAME", '^[a-z]{2}-[a-z]+-[0-9]+$')
    s3_staging_dir_check = check("S3_STAGING_DIR",'^s3://[a-z][a-z0-9\-]+/?$')
    profile_name_check   = check("PROFILE_NAME","^[a-zA-Z0-9_\-]+$")
    database_name_check  = check("DATABASE_NAME","^[a-zA-Z0-9_\-]+$")
    if region_name_check and s3_staging_dir_check and profile_name_check:
        s3_staging_dir = ss('S3_STAGING_DIR')
        region_name    = ss('REGION_NAME')
        profile_name   = ss('PROFILE_NAME')
        statement      = ss('STATEMENT')
        database_name  = ss('DATABASE_NAME')
        with connect(s3_staging_dir=s3_staging_dir, region_name=region_name, profile_name=profile_name,database_name=database_name) as conn:
            statement  = statement.replace("\n", " ")
            save_session_state()
            if re.match('^.+', statement):
                with ss('result_expander'):
                    with st.spinner('Running query...'):
                        st.session_state['LATEST_DATAFRAME'] = read_sql_query(statement, conn)
                        save_dataframe_if_needed()
    else:
        wrongs = []
        if not region_name_check:
            wrongs.append('Region name')
        if not s3_staging_dir_check:
            wrongs.append('S3 Staging Directory')
        if not profile_name_check:
            wrongs.append('Profile Name')
        if not database_name_check:
            wrongs.append('Database Name')
        st.warning(f'Please correct these data points and try again: {",".join(wrongs)}')

def create_athena_table() -> None:
    profile_name  = ss('PROFILE_NAME')
    s3_uri        = ss('S3_PARQUET_URI')
    database_name = ss('DATABASE_NAME')
    table_name    = ss('TARGET_TABLE_NAME')
    region_name   = ss('REGION_NAME')
    athena_results_s3_bucket = ss('S3_STAGING_DIR')
    data_catalog  = ss('DATA_CATALOG_NAME', 'AwsDataCatalog')    

def export_to_parquet_on_s3() -> None:
    if not s3_target_parquet_uri.startswith('s3://') or not s3_target_parquet_uri.endswith('.parquet'):
        with st.session_state['parquet_export_expander']:
            st.warning('S3 URI must start with s3:// and end with .parquet')
            return

    if ss('LATEST_DATAFRAME') is None or len(ss('LATEST_DATAFRAME')) == 0:
        with st.session_state['parquet_export_expander']:
            st.warning('Please run a query to export')
            return

    profile_name  = ss('PROFILE_NAME')
    region_name   = ss('REGION_NAME')
    s3_target_parquet_uri  = ss("S3_TARGET_PARQUET_URI")
    parquet_path = ss("LATEST_DATAFRAME_CSV_PATH").replace(".csv",".parquet")
    s3 = boto3.Session(profile_name = profile_name, region_name=region_name).client('s3')
    bucket_name, prefix = get_bucket_name_and_prefix(s3_target_parquet_uri)
    with st.session_state['parquet_export_expander']:
        with st.spinner('Uploading latest query results...'):
            s3.upload_file(parquet_path, bucket_name, prefix)

populate_session_state_if_needed()
st.set_page_config(page_title="Athena Explorer",
    page_icon="🧊",layout="wide")
st.write("### Welcome to Athena Explorer")
st.session_state['LATEST_DATAFRAME_CSV_PATH'] = os.path.join(os.environ['HOME'], 'latest_dataframe.csv')
st.session_state['LATEST_DATAFRAME_JSON_PATH'] = os.path.join(os.environ['HOME'], 'latest_dataframe.json')
st.session_state['configuration_expander'] = st.expander('Configuration', expanded=True)
st.session_state['query_expander']         = st.expander('Query', expanded=True)
st.session_state['result_expander']        = st.expander('Result', expanded=True)
st.session_state['charts_expander']        = st.expander('Charts', expanded=True)
st.session_state['create_expander']        = st.expander('Create Athena table from S3 Bucket with parquets', expanded=False)
st.session_state['parquet_export_expander']= st.expander('Export Latest Results to Parquet in S3', expanded=False)

with st.session_state['configuration_expander']:
    st.text_input("Region Name:", key="REGION_NAME")
    st.text_input("S3 Staging Directory (the S3 bucket for the Athena results):", key="S3_STAGING_DIR")
    st.text_input("Profile Name:", key="PROFILE_NAME")
    st.text_input("Database Name:", key="DATABASE_NAME")
    
with st.session_state['query_expander']:
    st.text_area("Query, using fully qualified table names:", key="STATEMENT")
    col1, col2, col3 = st.columns(3)
    with col3:
        st.button(label='Run Query', on_click=run_query)

if ss('LATEST_DATAFRAME') is not None:
    with ss('result_expander'):
        st.dataframe(ss('LATEST_DATAFRAME'))

if ss('LATEST_DATAFRAME') is not None:
    with ss('charts_expander'):
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        
        if can_render_line_chart():
            with col1:
                st.button('Line Chart', on_click=render_line_chart)
        if can_render_pie_chart():
            with col2:
                st.button('Pie Chart', on_click=render_pie_chart)
        if can_render_histogram_chart():
            with col3:
                st.text_input('Size:', key='HISTOGRAM_SIZE')
            with col4:
                st.button('Histograms', on_click=render_histogram)
        if can_render_marginal_histogram_chart():
            with col5:
                st.button('Marginal Histogram', on_click=render_marginal_histogram)

with st.session_state['create_expander']:
    if ss("DATA_CATALOG_NAME") is None:
        st.session_state["DATA_CATALOG_NAME"] = 'AwsDataCatalog'
    st.text_input("Data Catalog Name:", key="DATA_CATALOG_NAME")
    st.text_input("S3 Bucket URI with the parquet files:", key="S3_PARQUET_URI")
    st.text_input("Target Table Name:", key="TARGET_TABLE_NAME")
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col8:
        st.button('Create', on_click=create_athena_table)
        
with st.session_state['parquet_export_expander']:
    st.text_input("S3 URI to receive the parquet to be created:", key="S3_TARGET_PARQUET_URI")
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col8:
        st.button('Export', on_click=export_to_parquet_on_s3)    