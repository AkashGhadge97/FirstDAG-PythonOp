#importing all the required modules
from datetime import timedelta 
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import pandas as pd
import sqlite3
import os

#get dag directory path
dag_path = os.getcwd()


def transform_data():
    booking = pd.read_csv(f"{dag_path}/raw_data/booking.csv", low_memory=False)
    client = pd.read_csv(f"{dag_path}/raw_data/client.csv", low_memory=False)
    hotel = pd.read_csv(f"{dag_path}/raw_data/hotel.csv", low_memory=False)
    
    #merge booing.csv with client.csv
    data = pd.merge(booking, client, on = 'client_id')
    data.rename(columns={'name': 'client_name', 'type' : 'client_type'}, inplace = True)

    #merger data with hotel.csv
    data = pd.merge(data,hotel, on = 'hotel_id')
    data.rename(columns={'name' : 'hotel_name'}, inplace = True)

    #Make to date format consistent
    data.booking_date = pd.to_datetime(data.booking_date, infer_datetime_format=True)

    #Making the currency consistent
    data.loc[data.currency == 'EUR', ['booking_cost']] = data.booking_cost * 0.8
    data.currency.replace('EUR','GBR', inplace=True)

    #Removing the unnecessary columns
    data = data.drop('address', axis=1)

    #Load Processed data
    data.to_csv(f"{dag_path}/processed_data/processed_data.csv", index=False)


def load_data():
    conn = sqlite3.connect("/usr/local/airflow/db/bigdata.db")
    c=conn.cursor()
    c.execute(
        '''
          CREATE TABLE IF NOT EXISTS booking_record(
          client_id INTEGER NOT NULL,
          booking_date TEXT NOT NULL,
          room_type TEXT(512) NOT NULL,
          hotel_id INTEGER NOT NULL,
          booking_cost NUMERIC,
          currency TEXT,
          age INTEGER,
          client_name TEXT(512),
          client_type TEXT(512),
          hotel_name TEXT(512)
          );
        '''
    )
    records = pd.read_csv(f"{dag_path}/processed_data/processed_data.csv")
    records.to_sql('booking_record',conn, if_exists='replace',index=False)

#Default arguments for DAG
default_args = {
    'owner' : 'Akash Ghadge',
    'start_date' : days_ago(5)
}

ingestion_dag = DAG(
    'booking_ingestion',
    default_args = default_args,
    description = 'Created an ETL pipeline for Tourism data....',
    schedule_interval = timedelta(days=1),
    catchup = False
)

task_1 = PythonOperator(
    task_id = 'trasnform_data',
    python_callable=transform_data,
    dag = ingestion_dag
)

task_2 = PythonOperator(
    task_id = 'load_data',
    python_callable=load_data,
    dag = ingestion_dag
)

task_1 >> task_2