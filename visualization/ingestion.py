# Copyright 2025 highstreet technologies USA Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python3
"""
Data Ingestion Script for Test Results Visualization

This script monitors a directory for new test results files (results_*.zip),
processes them, and stores the data in TimescaleDB for visualization in Grafana.
"""

import json
import os
import time
import logging
import psycopg2
import tempfile
import zipfile
import shutil
import mimetypes
import hashlib
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv('DB_HOST', 'timescaledb')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_NAME = os.getenv('DB_NAME', 'testresults')
DB_CONNECT_RETRIES = int(os.getenv('DB_CONNECT_RETRIES', '5'))
DB_CONNECT_RETRY_DELAY = int(os.getenv('DB_CONNECT_RETRY_DELAY', '5'))

# Directory to monitor for new test results files
DATA_DIR = os.getenv('DATA_DIR', '/app/data')

# How often to check for new files (in seconds)
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '60'))

# MinIO connection parameters
MINIO_HOST = os.getenv('MINIO_HOST', 'minio')
MINIO_PORT = os.getenv('MINIO_PORT', '9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'artifacts')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# Set of processed files to avoid reprocessing
processed_files = set()

# Database connection object
db_connection = None

# MinIO client object
minio_client = None


def get_minio_client():
    """Create a connection to the MinIO server with retry mechanism."""
    global minio_client

    # If we already have a valid client, return it
    if minio_client:
        try:
            # Test if the client is still valid by checking if the bucket exists
            minio_client.bucket_exists(MINIO_BUCKET)
            return minio_client
        except Exception:
            # Client is no longer valid, create a new one
            minio_client = None

    # Try to establish a new connection with retries
    retries = 0
    while retries < DB_CONNECT_RETRIES:  # Reuse the same retry parameters as DB
        try:
            client = Minio(
                f"{MINIO_HOST}:{MINIO_PORT}",
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )

            # Check if the bucket exists, create it if it doesn't
            if not client.bucket_exists(MINIO_BUCKET):
                client.make_bucket(MINIO_BUCKET)
                logger.info(f"Created MinIO bucket: {MINIO_BUCKET}")

            minio_client = client
            logger.info("Successfully connected to MinIO")
            return client
        except Exception as e:
            retries += 1
            if retries < DB_CONNECT_RETRIES:
                logger.warning(f"Error connecting to MinIO (attempt {retries}/{DB_CONNECT_RETRIES}): {e}")
                logger.warning(f"Retrying in {DB_CONNECT_RETRY_DELAY} seconds...")
                time.sleep(DB_CONNECT_RETRY_DELAY)
            else:
                logger.error(f"Error connecting to MinIO after {DB_CONNECT_RETRIES} attempts: {e}")
                return None


def get_db_connection():
    """Create a connection to the database with retry mechanism."""
    global db_connection

    # If we already have a valid connection, return it
    if db_connection and not db_connection.closed:
        try:
            # Test if the connection is still valid
            cursor = db_connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            return db_connection
        except Exception:
            # Connection is no longer valid, close it and try to reconnect
            try:
                db_connection.close()
            except Exception:
                pass
            db_connection = None

    # Try to establish a new connection with retries
    retries = 0
    while retries < DB_CONNECT_RETRIES:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME
            )
            db_connection = conn
            logger.info("Successfully connected to the database")
            return conn
        except Exception as e:
            retries += 1
            if retries < DB_CONNECT_RETRIES:
                logger.warning(f"Error connecting to database (attempt {retries}/{DB_CONNECT_RETRIES}): {e}")
                logger.warning(f"Retrying in {DB_CONNECT_RETRY_DELAY} seconds...")
                time.sleep(DB_CONNECT_RETRY_DELAY)
            else:
                logger.error(f"Error connecting to database after {DB_CONNECT_RETRIES} attempts: {e}")
                return None


def process_test_results_file(file_path):
    """Process a test results file and store the data in the database."""
    temp_dir = None
    zip_ref = None
    try:
        logger.info(f"Processing file: {file_path}")

        # Create a temporary directory to extract the zip file
        temp_dir = tempfile.mkdtemp()
        logger.debug(f"Created temporary directory: {temp_dir}")

        # Open the zip file
        zip_ref = zipfile.ZipFile(file_path, 'r')

        # Extract the results.json file
        zip_ref.extract('results.json', temp_dir)
        logger.debug(f"Extracted results.json from {file_path} to {temp_dir}")

        # Read the JSON file
        json_file_path = os.path.join(temp_dir, 'results.json')
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Get a database connection
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get database connection")
            return False

        cursor = conn.cursor()

        try:
            # Begin transaction
            cursor.execute("BEGIN;")

            # Insert test run data
            test_metadata = data.get('testMetadata', {})
            test_id = test_metadata.get('testId', '')
            timestamp = Path(file_path).stem.split('_')[-1]  # Extract timestamp from filename
            dut_name = test_metadata.get('dutName', '')
            result = test_metadata.get('result', '')
            test_type = test_metadata.get('testType', '')
            start_date = test_metadata.get('startDate', '')
            stop_date = test_metadata.get('stopDate', '')

            cursor.execute("""
                INSERT INTO test_runs (test_id, timestamp, dut_name, result, test_type, start_date, stop_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (test_id, timestamp, dut_name, result, test_type, start_date, stop_date))

            test_run_id = cursor.fetchone()[0]

            # Process test groups and test cases
            for test_group in data.get('testResults', []):
                process_test_group(cursor, test_run_id, test_group, None, temp_dir, zip_ref)

            # Commit transaction
            cursor.execute("COMMIT;")
            logger.info(f"Successfully processed file: {file_path}")
            return True

        except Exception as e:
            # Rollback transaction on error
            cursor.execute("ROLLBACK;")
            logger.error(f"Error processing file {file_path}: {e}")
            return False

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        return False
    finally:
        # Close the zip file
        if zip_ref:
            try:
                zip_ref.close()
            except Exception as e:
                logger.warning(f"Failed to close zip file: {e}")

        # Clean up the temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {temp_dir}: {e}")


def process_test_group(cursor, test_run_id, test_group, parent_group_id=None, temp_dir=None, zip_file=None):
    """Process a test group and its test cases."""
    # Insert test group
    cursor.execute("""
        INSERT INTO test_groups (test_run_id, number, name, description, parent_group_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        test_run_id,
        test_group.get('number', ''),
        test_group.get('name', ''),
        test_group.get('description', ''),
        parent_group_id
    ))

    group_id = cursor.fetchone()[0]

    # Process test cases or nested groups
    for item in test_group.get('groupItems', []):
        if 'groupItems' in item:
            # This is a nested group
            process_test_group(cursor, test_run_id, item, group_id, temp_dir, zip_file)
        else:
            # This is a test case
            process_test_case(cursor, test_run_id, group_id, item, temp_dir, zip_file)


def process_test_case(cursor, test_run_id, group_id, test_case, temp_dir=None, zip_file=None):
    """Process a test case and its metrics and measurements."""
    # Insert test case
    cursor.execute("""
        INSERT INTO test_cases (test_run_id, group_id, number, name, description, result, status, start_date, stop_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        test_run_id,
        group_id,
        test_case.get('number', ''),
        test_case.get('name', ''),
        test_case.get('description', ''),
        test_case.get('result', ''),
        test_case.get('status', ''),
        test_case.get('startDate', None),
        test_case.get('stopDate', None)
    ))

    test_case_id = cursor.fetchone()[0]

    # Process metrics
    for metric in test_case.get('metrics', []):
        process_metric(cursor, test_case_id, metric)

    # Process direct measurements (if any)
    for measurement in test_case.get('measurements', []):
        process_measurement(cursor, None, test_case_id, measurement)

    # Process artifacts (if any and if zip_file is provided)
    if temp_dir and zip_file and 'artifacts' in test_case:
        for artifact in test_case.get('artifacts', []):
            process_artifact(cursor, test_run_id, test_case_id, artifact, temp_dir, zip_file)


def process_metric(cursor, test_case_id, metric):
    """Process a metric and its measurements."""
    # Insert metric
    cursor.execute("""
        INSERT INTO metrics (test_case_id, description, result, status)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """, (
        test_case_id,
        metric.get('description', ''),
        metric.get('result', ''),
        metric.get('status', '')
    ))

    metric_id = cursor.fetchone()[0]

    # Process measurements
    for measurement in metric.get('measurements', []):
        process_measurement(cursor, metric_id, test_case_id, measurement)


def upload_artifact_to_minio(file_path, object_name):
    """Upload an artifact to MinIO and return the object path."""
    try:
        # Get MinIO client
        client = get_minio_client()
        if not client:
            logger.error("Failed to get MinIO client")
            return None

        # Determine content type
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'

        # Upload file to MinIO
        client.fput_object(
            MINIO_BUCKET,
            object_name,
            file_path,
            content_type=content_type
        )

        logger.info(f"Uploaded artifact to MinIO: {object_name}")
        return object_name
    except Exception as e:
        logger.error(f"Error uploading artifact to MinIO: {e}")
        return None


def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def process_artifact(cursor, test_run_id, test_case_id, artifact, temp_dir, zip_file):
    """Process an artifact and store its metadata in the database."""
    try:
        # Extract artifact information
        name = artifact.get('name', '')
        description = artifact.get('description', '')
        original_path = artifact.get('path', '')

        if not name or not original_path:
            logger.warning(f"Skipping artifact with missing name or path: {artifact}")
            return

        # Extract the artifact from the zip file
        try:
            zip_file.extract(original_path, temp_dir)
            extracted_path = os.path.join(temp_dir, original_path)
        except Exception as e:
            logger.warning(f"Failed to extract artifact {original_path}: {e}")
            return

        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(extracted_path)
        logger.debug(f"Calculated hash for {original_path}: {file_hash}")

        # Check if this artifact already exists in the database
        cursor.execute("""
            SELECT minio_path FROM artifacts WHERE file_hash = %s LIMIT 1;
        """, (file_hash,))

        existing_artifact = cursor.fetchone()

        if existing_artifact:
            # Artifact already exists, reuse the existing MinIO path
            minio_path = existing_artifact[0]
            logger.info(f"Reusing existing artifact with hash {file_hash}: {minio_path}")
            # Don't insert a new record, just return
            return
        else:
            # Artifact doesn't exist, upload it to MinIO
            # Generate a unique object name for MinIO
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            object_name = f"{test_run_id}/{file_hash[:8]}_{os.path.basename(original_path)}"

            # Upload the artifact to MinIO
            minio_path = upload_artifact_to_minio(extracted_path, object_name)
            if not minio_path:
                logger.warning(f"Failed to upload artifact {original_path} to MinIO")
                return

            logger.info(f"Uploaded new artifact with hash {file_hash}: {minio_path}")

            # Get file size
            size = os.path.getsize(extracted_path)

            # Determine content type
            content_type, _ = mimetypes.guess_type(extracted_path)
            if not content_type:
                content_type = 'application/octet-stream'

            # Insert artifact metadata into the database
            cursor.execute("""
                INSERT INTO artifacts (test_run_id, test_case_id, name, description, original_path, minio_path, content_type, size, file_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                test_run_id,
                test_case_id,
                name,
                description,
                original_path,
                minio_path,
                content_type,
                size,
                file_hash
            ))

            logger.info(f"Processed artifact: {name}")
    except Exception as e:
        logger.error(f"Error processing artifact: {e}")


def process_measurement(cursor, metric_id, test_case_id, measurement):
    """Process a measurement."""
    # Insert measurement
    cursor.execute("""
        INSERT INTO measurements (metric_id, test_case_id, name, value, units)
        VALUES (%s, %s, %s, %s, %s);
    """, (
        metric_id,
        test_case_id,
        measurement.get('name', ''),
        json.dumps(measurement.get('values', [])),
        measurement.get('units', '')
    ))


class TestResultsHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def on_created(self, event):
        """Handle file creation events."""
        logger.info(f"File system event detected (created): {event.src_path}")
        if not event.is_directory:
            logger.info(f"File created: {event.src_path}")
            if event.src_path.endswith('.zip') and 'results_' in event.src_path:
                logger.info(f"Detected new results zip file: {event.src_path}")
                file_path = event.src_path
                if file_path not in processed_files:
                    logger.info(f"Processing new file: {file_path}")
                    if process_test_results_file(file_path):
                        processed_files.add(file_path)
                        logger.info(f"Successfully processed and added to processed_files: {file_path}")
                    else:
                        logger.warning(f"Failed to process file: {file_path}")
                else:
                    logger.debug(f"Skipping already processed file: {file_path}")
            else:
                logger.debug(f"Ignoring non-results file: {event.src_path}")

    def on_modified(self, event):
        """Handle file modification events."""
        logger.info(f"File system event detected (modified): {event.src_path}")
        if not event.is_directory and event.src_path.endswith('.zip') and 'results_' in event.src_path:
            logger.info(f"Results zip file modified: {event.src_path}")

    def on_deleted(self, event):
        """Handle file deletion events."""
        logger.info(f"File system event detected (deleted): {event.src_path}")
        if not event.is_directory and event.src_path.endswith('.zip') and 'results_' in event.src_path:
            logger.info(f"Results zip file deleted: {event.src_path}")
            # Remove from processed_files if it was there
            if event.src_path in processed_files:
                processed_files.remove(event.src_path)
                logger.info(f"Removed from processed_files: {event.src_path}")

    def on_moved(self, event):
        """Handle file move events."""
        logger.info(f"File system event detected (moved): {event.src_path} -> {event.dest_path}")
        # Check if source was a results zip file
        if not event.is_directory and event.src_path.endswith('.zip') and 'results_' in event.src_path:
            logger.info(f"Results zip file moved from: {event.src_path}")
            # Remove source from processed_files if it was there
            if event.src_path in processed_files:
                processed_files.remove(event.src_path)
                logger.info(f"Removed source from processed_files: {event.src_path}")

        # Check if destination is a results zip file
        if not event.is_directory and event.dest_path.endswith('.zip') and 'results_' in event.dest_path:
            logger.info(f"Results zip file moved to: {event.dest_path}")
            # Process the file at its new location if not already processed
            if event.dest_path not in processed_files:
                logger.info(f"Processing moved file: {event.dest_path}")
                if process_test_results_file(event.dest_path):
                    processed_files.add(event.dest_path)
                    logger.info(f"Successfully processed and added to processed_files: {event.dest_path}")
                else:
                    logger.warning(f"Failed to process moved file: {event.dest_path}")
            else:
                logger.debug(f"Skipping already processed moved file: {event.dest_path}")


def scan_existing_files():
    """Scan for existing test results files and process them."""
    logger.info(f"Scanning directory {DATA_DIR} for existing test results files")

    # List all files in the directory to help with debugging
    try:
        all_files = list(Path(DATA_DIR).glob('*'))
        logger.info(f"Found {len(all_files)} files in {DATA_DIR}: {[f.name for f in all_files]}")

        # Check file permissions and details
        for file_path in all_files:
            try:
                stat_info = os.stat(file_path)
                permissions = oct(stat_info.st_mode)[-3:]  # Get the last 3 digits of octal representation
                size = stat_info.st_size
                logger.info(f"File details - {file_path.name}: permissions={permissions}, size={size} bytes, " +
                           f"readable={os.access(file_path, os.R_OK)}, writable={os.access(file_path, os.W_OK)}")
            except Exception as perm_e:
                logger.error(f"Error checking permissions for {file_path}: {perm_e}")
    except Exception as e:
        logger.error(f"Error listing files in {DATA_DIR}: {e}")

    # Look for results_*.zip files
    zip_files = list(Path(DATA_DIR).glob('results_*.zip'))
    logger.info(f"Found {len(zip_files)} results_*.zip files in {DATA_DIR}: {[f.name for f in zip_files]}")

    # Check if zip files can be opened and read
    for zip_file in zip_files:
        try:
            logger.info(f"Attempting to open zip file: {zip_file}")
            with zipfile.ZipFile(zip_file, 'r') as zf:
                file_list = zf.namelist()
                logger.info(f"Zip file contents for {zip_file.name}: {file_list}")
                if 'results.json' in file_list:
                    logger.info(f"results.json found in {zip_file.name}")
                    try:
                        with zf.open('results.json') as json_file:
                            # Just read a small part to verify it's readable
                            data = json_file.read(100)
                            logger.info(f"Successfully read from results.json in {zip_file.name}")
                    except Exception as json_e:
                        logger.error(f"Error reading results.json from {zip_file.name}: {json_e}")
                else:
                    logger.warning(f"results.json not found in {zip_file.name}")
        except Exception as zip_e:
            logger.error(f"Error opening zip file {zip_file}: {zip_e}")

    # Log the current contents of processed_files
    logger.info(f"Currently processed files ({len(processed_files)}): {[os.path.basename(f) for f in processed_files]}")

    for file_path in zip_files:
        str_file_path = str(file_path)
        if str_file_path not in processed_files:
            logger.info(f"Processing new file: {file_path}")
            if process_test_results_file(str_file_path):
                processed_files.add(str_file_path)
                logger.info(f"Successfully processed and added to processed_files: {file_path}")
            else:
                logger.warning(f"Failed to process file: {file_path}")
        else:
            logger.debug(f"Skipping already processed file: {file_path}")


def main():
    """Main function."""
    logger.info("Starting test results data ingestion service")

    # Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Attempt to establish a database connection at startup
    logger.info("Attempting to establish initial database connection...")
    if get_db_connection():
        logger.info("Initial database connection successful")
    else:
        logger.warning("Failed to establish initial database connection. Will retry during processing.")

    # Process existing files
    scan_existing_files()

    # Set up file system observer
    event_handler = TestResultsHandler()
    observer = Observer()

    # Check if the directory exists before scheduling the observer
    if not os.path.exists(DATA_DIR):
        logger.error(f"Directory {DATA_DIR} does not exist. Creating it.")
        os.makedirs(DATA_DIR, exist_ok=True)

    # Log the absolute path of the directory being watched
    abs_data_dir = os.path.abspath(DATA_DIR)
    logger.info(f"Absolute path of watched directory: {abs_data_dir}")

    # Schedule the observer with the absolute path
    observer.schedule(event_handler, abs_data_dir, recursive=False)
    observer.start()
    logger.info(f"Observer started for directory: {abs_data_dir}")

    try:
        logger.info(f"Watching directory {DATA_DIR} for new test results files")
        while True:
            # Periodically scan for new files in case some were missed by the observer
            scan_existing_files()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Stopping observer.")
        observer.stop()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        observer.stop()

    logger.info("Waiting for observer to join...")
    observer.join()
    logger.info("Observer joined. Exiting.")


if __name__ == "__main__":
    main()
