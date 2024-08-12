import requests,ssl,socket, time,sqlite3,platform, concurrent.futures, subprocess, re, threading
from datetime import datetime
# Configuration
url = 'https://google.com'  # Replace with the target URL
hostname = 'google.com'  # Replace with the target hostname
request_interval = 2  # Time between requests in seconds
measurement_duration = 10  # Total duration to measure MTBF in seconds (e.g., 3600 seconds = 1 hour)
db_name = 'service_monitoring.db'  # SQLite database file
hosts = ["google.com", "github.com", "nonexistentwebsite.com"]
stop_thread = False
# Initialize the database
def init_db():

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hsts_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            status TEXT,
            header TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forward_secrecy_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT,
            status TEXT,
            error_message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mtbf_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            mtbf REAL,
            failures INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ping_results
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    host TEXT, 
                    status INTEGER, 
                    time_ms REAL, 
                    timestamp DATETIME)''')
    conn.commit()
    conn.close()



# Save HSTS result to the database
def save_hsts_result(url, status, header):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO hsts_results (url, status, header)
        VALUES (?, ?, ?)
    ''', (url, status, header))
    conn.commit()
    conn.close()


# Save Forward Secrecy result to the database
def save_forward_secrecy_result(hostname, status, error_message):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forward_secrecy_results (hostname, status, error_message)
        VALUES (?, ?, ?)
    ''', (hostname, status, error_message))
    conn.commit()
    conn.close()


# Save MTBF result to the database
def save_mtbf_result(url, mtbf, failures):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO mtbf_results (url, mtbf, failures)
        VALUES (?, ?, ?)
    ''', (url, mtbf, failures))
    conn.commit()
    conn.close()


# Function to check if HSTS is enabled
def check_hsts(url):
    global stop_thread
    while not stop_thread:
        print(datetime.now())
        try:
            response = requests.get(url)
            if 'Strict-Transport-Security' in response.headers:
                status = "1"
                header = response.headers['Strict-Transport-Security']
                print(f"HSTS is enabled. Header: {header}")
            else:
                status = "0"
                header = None
                print("HSTS is not enabled.")
            save_hsts_result(url, status, header)
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            save_hsts_result(url, "error", str(e))
        time.sleep(10)


# Function to test Forward Secrecy
def test_forward_secrecy(hostname, port=443):
    global stop_thread
    while not stop_thread:
        print(datetime.now())
        forward_secrecy_ciphers = [
            'ECDHE-RSA-AES128-GCM-SHA256',
            'ECDHE-RSA-AES256-GCM-SHA384',
            'ECDHE-RSA-AES128-SHA256',
            'ECDHE-RSA-AES256-SHA384',
            'DHE-RSA-AES128-GCM-SHA256',
            'DHE-RSA-AES256-GCM-SHA384',
            'DHE-RSA-AES128-SHA256',
            'DHE-RSA-AES256-SHA256'
        ]

        context = ssl.create_default_context()
        context.set_ciphers(':'.join(forward_secrecy_ciphers))

        try:
            with socket.create_connection((hostname, port)) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    status = "1"
                    print(f"Forward Secrecy is supported by {hostname}.")
            save_forward_secrecy_result(hostname, status, None)
        except ssl.SSLError as e:
            status = "0"
            error_message = str(e)
            print(f"Forward Secrecy is NOT supported by {hostname}. Error: {error_message}")
            save_forward_secrecy_result(hostname, status, error_message)
        except Exception as e:
            status = "error"
            error_message = str(e)
            print(f"An error occurred: {error_message}")
            save_forward_secrecy_result(hostname, status, error_message)

        time.sleep(10)


# Function to send a request and check if it fails
def send_request(url):
    try:
        response = requests.get(url)
        print(response)
        if response.status_code >= 400:
            return False
    except requests.RequestException:
        return False
    return True


# Function to calculate MTBF
def calculate_mtbf(failure_times):
    if len(failure_times) < 2:
        return None  # Not enough data to calculate MTBF
    intervals = [failure_times[i] - failure_times[i - 1] for i in range(1, len(failure_times))]
    return sum(intervals) / len(intervals)


def mtbf():
    global stop_thread
    while not stop_thread:
        print(datetime.now())
        failure_times = []
        start_time = time.time()
        end_time = start_time + measurement_duration
        while time.time() < end_time:
            if not send_request(url):
                failure_times.append(time.time())
                print(f"Failure detected at {datetime.fromtimestamp(failure_times[-1])}")
            time.sleep(request_interval)

        if failure_times:
            mtbf = calculate_mtbf(failure_times)
            failures = len(failure_times)
            if mtbf is not None:
                # failures = len(failure_times)
                print(f"Mean Time Between Failures (MTBF): {mtbf:.2f} seconds")
                save_mtbf_result(url, mtbf, failures)
            else:
                print("Not enough failure data to calculate MTBF.")
                save_mtbf_result(url, 0, failures)
        else:
            print("No failures occurred during the measurement period.")
            save_mtbf_result(url, 0, 0)
        time.sleep(3601)


#### ping process start

def ping(host):
    try:
        if platform.system() == "Windows":
            command = ["ping", "-n", "1", host]
        else:
            command = ["ping", "-c", "1", host]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            if platform.system() == "Windows":
                time_ms_match = re.search(r'time=(\d+)ms', stdout)
            else:
                time_ms_match = re.search(r'time=(\d+\.?\d*) ms', stdout)

            if time_ms_match:
                return 1, int(time_ms_match.group(1))
            else:
                return 0, 0
        else:
            print(f"Ping failed: {stderr}")
            return 0, 0
    except Exception as e:
        print(f"Error pinging {host}: {e}")
        return 0, 0

def save_to_db(host, status, time_ms, db_name):
    try:
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO ping_results (host, status, time_ms, timestamp) VALUES (?, ?, ?, ?)",
                    (host, status, time_ms, datetime.now()))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
def continuous_ping(hosts, db_name):
    global stop_thread
    while not stop_thread:
        for host in hosts:
            print(f"Pinging {host}...")
            status, time_ms = ping(host)
            print(f"Result: Status={status}, Time={time_ms} ms")
            save_to_db(host, status, time_ms, db_name)
        time.sleep(10)


def main():
    init_db()

    # Correct the thread initialization by removing the parentheses
    ping_thread = threading.Thread(target=continuous_ping, args=(hosts, db_name))
    test_forward_secrecy_thread = threading.Thread(target=test_forward_secrecy, args=(hostname,))
    hsts_thread = threading.Thread(target=check_hsts, args=(url,))
    mtbf_thread = threading.Thread(target=mtbf)

    # Start the threads
    ping_thread.start()
    test_forward_secrecy_thread.start()
    hsts_thread.start()
    mtbf_thread.start()

    # Wait for the threads to complete
    ping_thread.join()
    test_forward_secrecy_thread.join()
    hsts_thread.join()
    mtbf_thread.join()

if __name__ == "__main__":
    main()
