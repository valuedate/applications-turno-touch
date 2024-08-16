#!/usr/bin/env python3
import requests
import os
import time
from datetime import datetime
import configparser
import logging

def setup_logging():
    # Create a log file with the start date of the cycle
    start_date = datetime.now().strftime('%Y-%m-%d_%H-%M')
    log_filename = f'/home/turno/logs/log_{start_date}.log'  # Replace with your desired log directory and filename

    # Set up logging configuration
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M'
    )
    return log_filename

def main():
    config = configparser.ConfigParser()
    config.read('/home/turno/config.ini')  # Replace with the actual path to the config file

    loop_count = int(config['settings']['loop_count'])
    lock_file_path = config['settings']['lock_file_path']
 
    log_filename = setup_logging()
    logging.info(f"Starting new cycle. Log file: {log_filename}")

    while True:
        loop_count += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        log_message = f"{current_time} Loop number: {loop_count}"
        print(log_message)
        logging.info(log_message)
 
        if os.path.exists(lock_file_path):
            logging.info("Lock file found. Ending loop.")
            print("Lock file found. Ending loop.") 
            break

        time.sleep(300)  # Pause for 5 minutes (300 seconds)

if __name__ == "__main__":
    main()


