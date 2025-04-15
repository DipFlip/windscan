import requests
import re
import time
import json
from urllib.parse import urlparse, parse_qs
import shutil
import datetime # Added for date calculations

def _get_month_abbr(month):
    """Returns the 3-letter lowercase month abbreviation."""
    try:
        return datetime.date(2000, month, 1).strftime('%b').lower()
    except ValueError:
        raise ValueError("Invalid month provided. Must be between 1 and 12.")

def _get_gdas_week_num(day):
    """Calculates the GDAS week number (1-5) based on the day."""
    if 1 <= day <= 7:
        return 1
    elif 8 <= day <= 14:
        return 2
    elif 15 <= day <= 21:
        return 3
    elif 22 <= day <= 28:
        return 4
    elif 29 <= day <= 31:
        return 5
    else:
        raise ValueError("Invalid day provided. Must be between 1 and 31.")

def run_hysplit_job(latitude=41.980000, longitude=-87.900000,
                      start_year=22, start_month=10, start_day=29, start_hour=22):
    """
    Runs the HYSPLIT job request sequence based on the recorded messages.

    Args:
        latitude (float): Starting latitude in decimal degrees. Default is 41.98.
        longitude (float): Starting longitude in decimal degrees (negative for West). Default is -87.90.
        start_year (int): Start year (2-digit format, e.g., 22 for 2022). Default is 22.
        start_month (int): Start month (1-12). Default is 10.
        start_day (int): Start day (1-31). Default is 29.
        start_hour (int): Start hour (0-23). Default is 22.

    Returns:
        tuple: (job_id, session) or (None, None) if failed.
    """
    session = requests.Session()

    # Validate inputs and calculate derived values
    try:
        month_abbr = _get_month_abbr(start_month)
        week_num = _get_gdas_week_num(start_day)
        # Ensure year is two digits, padding if necessary (e.g., 9 -> 09)
        year_str = f"{start_year:02d}"
    except ValueError as e:
        print(f"Input validation error: {e}")
        return None, None

    # Construct the dynamic mfile name
    mfile_name = f"gdas1.{month_abbr}{year_str}.w{week_num}"
    print(f"Using meteorological data file: {mfile_name}")

    # Headers often remain similar, define a base set
    base_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "en-US,en;q=0.9,sv;q=0.8,ja;q=0.7,de;q=0.6,la;q=0.5",
        "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "upgrade-insecure-requests": "1",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

    # Step 1: POST to trajasrc.pl (Reverse order from messages.json)
    url1 = "https://www.ready.noaa.gov/hypub-bin/trajasrc.pl"
    headers1 = {**base_headers,
                "cache-control": "max-age=0",
                "content-type": "application/x-www-form-urlencoded",
                "sec-fetch-user": "?1",
                "Referer": "https://www.ready.noaa.gov/hypub-bin/trajtype.pl?runtype=archive"
               }
    data1 = "nsrc=1&trjtype=1"
    try:
        print(f"POSTing to {url1}")
        response1 = session.post(url1, headers=headers1, data=data1)
        response1.raise_for_status()
        print(f"Status Code: {response1.status_code}")
        # print(f"Response Text (truncated): {response1.text[:200]}...") # Optional: Log response snippet
        time.sleep(1) # Add delay
    except requests.exceptions.RequestException as e:
        print(f"Error during step 1: {e}")
        return None, None

    # Step 2: POST to trajsrcm.pl
    url2 = "https://www.ready.noaa.gov/hypub-bin/trajsrcm.pl"
    headers2 = {**base_headers,
                "cache-control": "max-age=0",
                "content-type": "application/x-www-form-urlencoded",
                "sec-fetch-user": "?1",
                "Referer": "https://www.ready.noaa.gov/hypub-bin/trajasrc.pl"
               }

    # Determine N/S and E/W and absolute values for data2
    lat_ns = 'N' if latitude >= 0 else 'S'
    lon_ew = 'E' if longitude >= 0 else 'W'
    abs_lat = abs(latitude)
    abs_lon = abs(longitude)

    data2 = f"metdata=GDAS1&SOURCELOC=decdegree&Lat={abs_lat:.6f}&Latns={lat_ns}&Lon={abs_lon:.6f}&Lonew={lon_ew}&Latd=&Latm=&Lats=&Latdns=N&Lond=&Lonm=&Lons=&Londew=W&CITYNAME=&WMO="
    try:
        print(f"POSTing to {url2}")
        response2 = session.post(url2, headers=headers2, data=data2)
        response2.raise_for_status()
        print(f"Status Code: {response2.status_code}")
        # print(f"Response Text (truncated): {response2.text[:200]}...") # Optional: Log response snippet
        time.sleep(1) # Add delay
    except requests.exceptions.RequestException as e:
        print(f"Error during step 2: {e}")
        return None, None

    # Step 3: POST to traj1.pl
    url3 = "https://www.ready.noaa.gov/hypub-bin/traj1.pl"
    headers3 = {**base_headers,
                "cache-control": "max-age=0",
                "content-type": "application/x-www-form-urlencoded",
                "sec-fetch-user": "?1",
                "Referer": "https://www.ready.noaa.gov/hypub-bin/trajsrcm.pl"
               }
    # Use the dynamically generated mfile name
    data3 = f"mfile={mfile_name}"
    try:
        print(f"POSTing to {url3}")
        response3 = session.post(url3, headers=headers3, data=data3)
        response3.raise_for_status()
        print(f"Status Code: {response3.status_code}")
        # print(f"Response Text (truncated): {response3.text[:200]}...") # Optional: Log response snippet
        time.sleep(1) # Add delay
    except requests.exceptions.RequestException as e:
        print(f"Error during step 3: {e}")
        return None, None

    # Step 4: POST to traj2.pl - This submits the main job parameters
    url4 = "https://www.ready.noaa.gov/hypub-bin/traj2.pl"
    headers4 = {**base_headers,
                "cache-control": "max-age=0",
                "content-type": "application/x-www-form-urlencoded",
                "sec-fetch-user": "?1",
                "Referer": "https://www.ready.noaa.gov/hypub-bin/traj1.pl"
               }
    # Note: data4 expects longitude directly (negative for West)
    # Use the provided start date/time parameters
    data4 = f"direction=Backward&vertical=0&Start+year={year_str}&Start+month={start_month}&Start+day={start_day}&Start+hour={start_hour}&duration=168&repeatsrc=0&ntrajs=24&Source+lat={latitude:.6f}&Source+lon={longitude:.6f}&Source+lat2=&Source+lon2=&Source+lat3=&Source+lon3=&Midlayer+height=No&Source+hgt1=500&Source+hunit=0&Source+hgt2=0&Source+hgt3=0&gis=1&gsize=96&Zoom+Factor=70&projection=0&Vertical+Unit=1&Label+Interval=6&color=Yes&colortype=Yes&pltsrc=1&circle=-1&county=arlmap&psfile=No&pdffile=Yes&mplot=YES&rain=1"
    job_submission_response = None
    try:
        print(f"POSTing to {url4}")
        job_submission_response = session.post(url4, headers=headers4, data=data4)
        job_submission_response.raise_for_status()
        print(f"Status Code: {job_submission_response.status_code}")
        # This response HTML contains the link to the results page
        # print(f"Response Text (truncated): {job_submission_response.text[:500]}...") # Optional: Log response snippet
    except requests.exceptions.RequestException as e:
        print(f"Error during step 4 (Job Submission): {e}")
        return None, None

    # Step 5: Extract the results URL and job ID from the response of Step 4
    # The response typically contains a meta refresh tag or a link pointing to trajresults.pl?jobidno=XXXXX
    job_id = None
    if job_submission_response and job_submission_response.text:
        # Look for the job ID in meta refresh tag (Corrected regex)
        # Use raw string r'...' and single backslashes for special regex characters
        meta_match = re.search(r'CONTENT="\d+;\s*URL=[^"]*/hypub-bin/trajresults\.pl\?jobidno=(\d+)"', job_submission_response.text, re.IGNORECASE)
        if meta_match:
            job_id = meta_match.group(1)
            print(f"Found job ID in meta refresh: {job_id}")
        else:
            # Look for the job ID in anchor tags
            anchor_match = re.search(r'<a href="[^"]*/hypub-bin/trajresults\.pl\?jobidno=(\d+)"', job_submission_response.text, re.IGNORECASE)
            if anchor_match:
                job_id = anchor_match.group(1)
                print(f"Found job ID in link: {job_id}")
            else:
                 # Sometimes the job ID might be in the URL if there was a redirect
                 parsed_url = urlparse(job_submission_response.url)
                 query_params = parse_qs(parsed_url.query)
                 if 'jobidno' in query_params:
                     job_id = query_params['jobidno'][0]
                     print(f"Found job ID in final URL: {job_id}")
                 else:
                    print("Could not find job ID in response HTML or URL.")
                    # print(f"Final URL: {job_submission_response.url}") # Log the final URL for debugging
                    # print(f"Response Text: {job_submission_response.text}") # Log full text for debugging
                    return None, None # Return None for job_id and session
    else:
        print("No response content received from job submission.")
        return None, None # Return None for job_id and session

    # Return the job_id and the session for potential reuse (like downloading)
    return job_id, session

def download_results(job_id, session):
    """
    Downloads the HYSPLIT results zip file.

    Args:
        job_id (str): The job ID obtained from submission.
        session (requests.Session): The session used for the job submission.

    Returns:
        str: The path to the downloaded file, or None if download failed.
    """
    if not job_id or not session:
        print("Invalid job ID or session for download.")
        return None

    download_url = f"https://www.ready.noaa.gov/hypubout/gis_{job_id}.zip"
    download_filename = f"gis_{job_id}.zip"

    print(f"Waiting 10 seconds before downloading results for job {job_id}...")
    time.sleep(10)

    print(f"Attempting to download results from: {download_url}")
    try:
        # Use the same session to maintain cookies if necessary
        # Allow redirects as the server might redirect initially
        # Stream the download to handle potentially large files
        response = session.get(download_url, stream=True, allow_redirects=True)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Check if the content looks like a zip file (optional but good practice)
        content_type = response.headers.get('content-type', '').lower()
        if 'application/zip' not in content_type and 'application/octet-stream' not in content_type:
             # Sometimes servers might not set the correct content-type, especially for direct file links.
             # Let's be a bit more lenient but print a warning.
             print(f"Warning: Unexpected content-type '{content_type}'. Proceeding with download.")
             # We could add more checks here, like content-disposition if needed.

        # Save the file
        with open(download_filename, 'wb') as f:
            # Use shutil.copyfileobj for efficient file writing
            shutil.copyfileobj(response.raw, f)

        print(f"Successfully downloaded results to: {download_filename}")
        return download_filename

    except requests.exceptions.RequestException as e:
        print(f"Error downloading results for job {job_id}: {e}")
        # Check for specific status codes if needed (e.g., 404 Not Found)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            # print(f"Response Headers: {e.response.headers}") # Debug headers
            # print(f"Response Text (partial): {e.response.text[:200]}...") # Debug response text if not binary
        return None
    except Exception as e: # Catch other potential errors like file writing issues
        print(f"An unexpected error occurred during download: {e}")
        return None

if __name__ == "__main__":
    print("Starting HYSPLIT job submission...")
    # Call with default lat/lon and date/time for now, but can be overridden:
    # Example: Run for Jan 5th, 2023, 14:00 UTC from LA (34.05, -118.24)
    # job_id, session = run_hysplit_job(latitude=34.05, longitude=-118.24,
    #                                   start_year=23, start_month=1, start_day=5, start_hour=14)
    job_id, session = run_hysplit_job() # Use defaults: Lat=41.98, Lon=-87.90, Date=2022-10-29 22:00
    if job_id and session:
        print(f"Successfully submitted job. Job ID: {job_id}")
        print(f"Check results page at: https://www.ready.noaa.gov/hypub-bin/trajresults.pl?jobidno={job_id}")

        # Attempt to download the results
        downloaded_file = download_results(job_id, session)
        if downloaded_file:
            print(f"Result download successful: {downloaded_file}")
        else:
            print("Result download failed.")
    else:
        print("Job submission failed.") 