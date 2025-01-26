from sqlalchemy import create_engine, text
import pandas as pd
import json
import argparse
import os
from urllib.parse import quote_plus
from pathlib import Path
from panpipelines.utils.util_functions import *


# Set up argument parser
def parse_params():
    parser = argparse.ArgumentParser(description="Execute an SQL query and export the results to a CSV file.")
    parser.add_argument('--query', nargs="+",required=True, help="The SQL query to execute.")
    parser.add_argument('--output', default='results.csv', help="The name of the output CSV file (default: results.csv).")
    parser.add_argument('--cert', default='pandb_root.crt', help="The name of the pandb ssl cert.")
    parser.add_argument('--connargs', default='pandb.json', help="The name of connection args json file.")
    parser.add_argument("--pipeline_config_file", type=Path, help="Pipeline Config File")
    return parser

if __name__ == "__main__":

    parser=parse_params()
    args, unknown_args = parser.parse_known_args()

    query = args.query
    query = " ".join([x.replace("\\","") for x in query])
    output = args.output

    cert = args.cert
    connargs = os.path.abspath(args.connargs)
    pipeline_config_file = None
    if args.pipeline_config_file:
        if Path(args.pipeline_config_file).exists():
            pipeline_config_file = str(args.pipeline_config_file)

    with open(connargs,"r") as infile:
        panargs = json.load(infile)

    encoded_password = quote_plus(panargs['password'])

    labels_dict={}
    if pipeline_config_file:
        panpipeconfig_file=str(pipeline_config_file)
        if os.path.exists(pipeline_config_file):
           print(f"{pipeline_config_file} exists.")
           with open(pipeline_config_file,'r') as infile:
               labels_dict = json.load(infile)

    if labels_dict:
        cwd = getParams(labels_dict,"CWD")
    else:
        cwd = os.path.dirname(tempfile.mkstemp()[1])

    if not os.path.dirname(output):
        output = os.path.join(cwd,output)


    # Create the connection URL
    db_url = (
        f"postgresql+psycopg2://{panargs['user']}:{encoded_password}@"
        f"{panargs['host']}:{panargs['port']}/{panargs['dbname']}?sslmode={panargs['sslmode']}&"
        f"sslrootcert={cert}"
    )

    # Connect to the database
    engine = create_engine(db_url)

    # Execute the query and retrieve data into a Pandas DataFrame
    try:
        with engine.connect() as connection:
            result = pd.read_sql_query(text(query), connection)
    except Exception as e:
        result = pd.DataFrame()

    # Save the DataFrame to a CSV file
    if not result.empty:
        result.to_csv(output, index=False)
        print(f"Data has been successfully exported to {output}.")
        output_metadata = create_metadata(output,None, metadata = {"Script":"pandb_download.py","Description":f"{query}"})
    else:
        output=None
        output_metadata=None
        print(f"Problem obtaining results for query {query}")

    if labels_dict:
        labels_dict["METADATA_FILE"]=output_metadata 
        labels_dict["OUTPUT_FILE"]=output
        export_labels(labels_dict,pipeline_config_file)
