# Test Results Visualization

This directory contains a Docker-based solution for visualizing test results from the Hybrid M-Plane Test Runner. The solution uses TimescaleDB for storing the test results data and Grafana for visualization.

## Components

The solution consists of the following components:

1. **TimescaleDB**: A time-series database built on PostgreSQL, used for storing the test results data.
2. **MinIO**: An object storage service compatible with Amazon S3 API, used for storing test artifacts.
3. **Grafana**: A visualization and analytics platform, used for creating dashboards to visualize the test results data.
4. **Data Ingestion Service**: A custom Python service that monitors the output directory for new test results files, processes them, stores the data in TimescaleDB, and uploads artifacts to MinIO.

## Directory Structure

```
visualization/
├── docker-compose.yml         # Docker Compose file for the solution
├── Dockerfile.ingestion       # Dockerfile for the data ingestion service
├── requirements.txt           # Python dependencies for the data ingestion service
├── ingestion.py               # Data ingestion script
├── init-scripts/              # Database initialization scripts
│   └── 01-init-tables.sql     # Script to create the database tables
├── grafana/                   # Grafana configuration
│   ├── provisioning/          # Grafana provisioning configuration
│   │   ├── datasources/       # Datasource configuration
│   │   │   └── timescaledb.yaml  # TimescaleDB datasource configuration
│   │   └── dashboards/        # Dashboard configuration
│   │       └── dashboards.yaml   # Dashboard provider configuration
│   └── dashboards/            # Dashboard definitions
│       └── test_results_dashboard.json  # Initial dashboard for test results
└── README.md                  # This file
```

## Getting Started

### Prerequisites

- Docker and Docker Compose installed on your system
- The Hybrid M-Plane Test Runner project with test results in the `output` directory

### Running the Solution

1. Navigate to the project root directory:

   ```bash
   cd /path/to/tifg
   ```

2. Start the visualization solution:

   ```bash
   cd visualization
   docker-compose up -d
   ```

3. Access Grafana at http://localhost:3000 (default credentials: admin/admin)

4. Access MinIO Console at http://localhost:9001 (default credentials: minioadmin/minioadmin)

5. The data ingestion service will automatically process existing test results files in the `output` directory and monitor for new files. Test artifacts will be extracted and stored in MinIO with deduplication (identical artifacts are stored only once).

## Customization

### Adding New Dashboards

You can create new dashboards directly in Grafana and save them. They will be persisted in the Grafana volume.

Alternatively, you can add new dashboard JSON files to the `grafana/dashboards` directory and restart the containers.

### Available Dashboards

The solution comes with the following pre-configured dashboards:

1. **Test Results Dashboard**: Shows test run results, test case distribution, and recent test cases.
2. **Test Artifacts Dashboard**: Shows test artifacts stored in MinIO, including links to download them, artifact statistics, and storage usage information.

### Modifying the Database Schema

If you need to modify the database schema, you can edit the `init-scripts/01-init-tables.sql` file. The current schema includes tables for:

- `test_runs`: High-level information about each test run
- `test_groups`: Information about test groups
- `test_cases`: Information about individual test cases
- `metrics`: Information about test metrics
- `measurements`: Information about test measurements
- `artifacts`: Metadata about test artifacts stored in MinIO, with deduplication based on file content hash

Note that you'll need to remove the TimescaleDB volume to apply schema changes:

```bash
docker-compose down
docker volume rm visualization_timescaledb_data
docker-compose up -d
```

### Customizing the Data Ingestion

If you need to customize the data ingestion process, you can modify the `ingestion.py` script. After making changes, rebuild and restart the data ingestion service:

```bash
docker-compose build data-ingestion
docker-compose up -d data-ingestion
```

### Artifact Deduplication

The system implements artifact deduplication to save storage space and improve performance:

1. When a test artifact is processed, a SHA-256 hash of its content is calculated
2. The system checks if an artifact with the same hash already exists in the database
3. If a match is found, the existing MinIO path is reused instead of uploading the file again
4. If no match is found, the artifact is uploaded to MinIO and its metadata is stored in the database

This ensures that identical artifacts are stored only once in MinIO, even if they are referenced by multiple test cases or test runs. The deduplication is based on the actual file content, not just the filename or path.

## Troubleshooting

### Checking Logs

You can check the logs of each service to troubleshoot issues:

```bash
# TimescaleDB logs
docker-compose logs timescaledb

# MinIO logs
docker-compose logs minio

# Grafana logs
docker-compose logs grafana

# Data ingestion service logs
docker-compose logs data-ingestion
```

### Common Issues

- **Database connection issues**: Ensure that the TimescaleDB container is running and that the data ingestion service can connect to it.
- **MinIO connection issues**: Ensure that the MinIO container is running and that the data ingestion service can connect to it.
- **Missing data in Grafana**: Check that the TimescaleDB datasource is configured correctly in Grafana and that the data ingestion service is processing the test results files.
- **Missing artifacts in MinIO**: Check that the test results files contain artifacts and that the data ingestion service is extracting and uploading them correctly.
- **Dashboard not loading**: Verify that the dashboard JSON file is valid and that the dashboard provider is configured correctly.

## Further Development

Here are some ideas for further development of the visualization solution:

- Add more sophisticated dashboards for different aspects of the test results
- Implement alerting based on test results
- Add user authentication and authorization for Grafana and MinIO
- Implement data retention policies for TimescaleDB and MinIO
- Add support for exporting visualizations and reports

### Artifact Visualization Enhancements

The current artifact visualization can be further enhanced with:

1. **Artifact Preview**: Add capability to preview certain types of artifacts (images, text files, logs, etc.) directly in Grafana using plugins like [Grafana Image Renderer](https://grafana.com/grafana/plugins/grafana-image-renderer/).

2. **Advanced Filtering**: Implement more advanced filtering options for artifacts based on content type, size, test case result, etc.

3. **Artifact Tagging**: Add ability to tag artifacts with custom labels for better organization and filtering.

4. **Artifact Comparison**: Create a panel that allows comparing similar artifacts from different test runs.

5. **Artifact Lifecycle Management**: Implement policies for artifact retention, archiving, and deletion based on age, size, or importance.

6. **Integration with Test Cases**: Enhance the Test Results Dashboard to show related artifacts for each test case.

7. **Artifact Search**: Implement full-text search capabilities for artifact content (for text-based artifacts).

8. **Artifact Analytics**: Add more sophisticated analytics for artifacts, such as content analysis for log files to identify patterns or anomalies.

9. **Artifact Download Bundle**: Add capability to download multiple artifacts as a single ZIP file.

10. **Direct MinIO Integration**: Add a link to the MinIO console for advanced artifact management.
