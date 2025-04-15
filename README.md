# Windscan

This project contains a Python script (`windscan.py`) that interacts with the NOAA READY HYSPLIT website to submit a backward trajectory analysis job and download the resulting GIS data.

## Setup

1.  Ensure you have Python 3 installed.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script from your terminal:

```bash
python windscan.py
```

The script will:

1.  Submit a pre-configured HYSPLIT job request.
2.  Print the assigned job ID.
3.  Wait 10 seconds.
4.  Attempt to download the results as a zip file (e.g., `gis_123456.zip`). 