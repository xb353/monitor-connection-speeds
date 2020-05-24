import speedtest as st
import sqlite3
from datetime import datetime
import socket
import ssl
import time
from dataclasses import dataclass
import sys
import OpenSSL.crypto as crypto

@dataclass
class ConnectionTesting:
    # How often to check connection in seconds
    CHECK_DELAY: int = 5

    # How often to check speed
    SPEED_INTERVAL: int = CHECK_DELAY * 10

    # Domain and port for initial connection check
    CHECK_DOMAIN:   str = '1.1.1.1'
    CHECK_CN:       str = 'sni.cloudflaressl.com'
    CHECK_PORT:     int = 443

    # Trackers for status tracking
    TOTAL_ROWS_WRITTEN: int = 0
    LAST_DOWN: int = 0
    LAST_PING: int = 0
    LAST_UP:   int = 0
    AVG_DOWN:  int = 0
    AVG_PING:  int = 0
    AVG_UP:    int = 0
    PROBLEMS:  int = 0

    # Full Sqlite database path
    DB_PATH: str = 'speeds.db'
    
    # Sqlite table name
    DB_TABLE_NAME: str = "speed"

    # Sqlite DB connection and cursor
    conn: sqlite3.Connection = sqlite3.connect(DB_PATH)
    curs: sqlite3.Cursor = conn.cursor()

    # After dataclass init, this post_init method gets called
    # I'll use it to init the actual sqlite table if it doesn't exist
    def __post_init__(self):
        self.curs.execute(f'''CREATE TABLE IF NOT EXISTS {self.DB_TABLE_NAME}(  TYPE TEXT,                  DATETIME TIMESTAMP, \
                                                                                STATUS TEXT,                DOMAIN TEXT, \
                                                                                CERT_SUBJECT TEXT,          CERT_ISSUER TEXT, \
                                                                                ERROR_MSG TEXT,             PING INTEGER, \
                                                                                DOWNLOAD_SPEED_MB REAL,     UPLOAD_SPEED_MB REAL)''')
    
    def _insert_status(self, status, subj, issuer, error=''):
        sql = f'INSERT INTO {self.DB_TABLE_NAME} VALUES(\'status\', \'{datetime.now()}\', \'{status}\', \'{self.CHECK_DOMAIN}\', \'{subj}\', \'{issuer}\', \'{error}\', \'\', \'\', \'\')'
        self.curs.execute(sql)
        self.conn.commit()
        self.TOTAL_ROWS_WRITTEN+=1

    def _insert_speed(self, ping, download, upload, error=''):
        sql = f'INSERT INTO {self.DB_TABLE_NAME} VALUES(\'speed\', \'{datetime.now()}\', \'{error}\', \'speedtest\', \'\', \'\', \'{error}\', \'{ping}\', \'{download}\', \'{upload}\')'
        self.curs.execute(sql)
        self.conn.commit()
        self.TOTAL_ROWS_WRITTEN+=1

    # Adding some logic for tracking subject and issuer CNs to better track cert verification problems I saw a few times
    def ssl_check_connection(self):
        context = ssl.create_default_context()
        try:

            cert        = ssl.get_server_certificate(addr=(self.CHECK_DOMAIN, self.CHECK_PORT))
            x509        = crypto.load_certificate(crypto.FILETYPE_PEM, cert)

            cert_subj   = x509.get_subject().CN
            cert_issuer = x509.get_issuer().CN

            with socket.create_connection((self.CHECK_DOMAIN, self.CHECK_PORT)) as sock:
                with context.wrap_socket(sock, server_hostname=self.CHECK_DOMAIN) as ssock:
                    peer_address, _ = ssock.getpeername()
                    self._insert_status('successful connection', cert_subj, cert_issuer)
                    return True
        
        except ssl.SSLCertVerificationError:
            print("\n! Certification Verification Error")
            self._insert_status("certificate verification error", cert_subj, cert_issuer, "certificate verification")
            self.PROBLEMS+=1
            return False
 
        except socket.timeout:
            print("\n! Connection timeout")
            self._insert_status("no connection", "", "", error="timeout")
            self.PROBLEMS+=1
            return False

        except Exception as e:
            print(f"\n! {e}")
            self._insert_status('other error with connection', '', '', error=str(e))
            self.PROBLEMS+=1
            return False

    # Requires speedtest library
    def get_new_speeds(self):
        try:
            speed_test = st.Speedtest()
            speed_test.get_best_server()

            # Get ping (miliseconds)
            ping = speed_test.results.ping
            # Perform download and upload speed tests (bits per second)
            download = speed_test.download()
            upload   = speed_test.upload()
        except Exception as e:
            print("\n! Problem with speed test")
            print(e)
            self._insert_speed(-1, 0, 0, str(e))
            self.PROBLEMS+=1
            return False
        # Convert download and upload speeds to megabits per second
        download_mbs = round(download / (10**6), 2)
        upload_mbs = round(upload / (10**6), 2)
        self._insert_speed(ping, download_mbs, upload_mbs)
        self.LAST_DOWN = download_mbs
        self.LAST_PING = ping
        self.LAST_UP   = upload_mbs
        self.AVG_DOWN  = (self.LAST_DOWN + self.AVG_DOWN)/2 if self.AVG_DOWN else self.LAST_DOWN
        self.AVG_PING  = (self.LAST_PING + self.AVG_PING)/2 if self.AVG_PING else self.LAST_PING
        self.AVG_UP    = (self.LAST_UP + self.AVG_UP)/2 if self.AVG_UP else self.LAST_UP
        self.summary()
        return True
    
    def summary(self):
        print(f"""\rTotal rows: {self.TOTAL_ROWS_WRITTEN:.2f}, Last Down: {self.LAST_DOWN:.2f}, Avg Down: {self.AVG_DOWN:.2f}, Last Ping: {self.LAST_PING:.2f}, Avg Ping: {self.AVG_PING:.2f}, Last Up: {self.LAST_UP:.2f}, Avg Up: {self.AVG_UP:.2f}, Problems: {self.PROBLEMS}""", 
                          end='', flush=True)
    
    # Close connection to db and exit
    def _exit(self, c=0):
        print("\n+ Attempting Graceful Exit")
        self.curs.close()
        self.conn.close()
        print("- Goodbye!")
        sys.exit(c)

# Main function loop
def main():
    # init connection testing obj as test which will initialize our DB if it doesn't exist
    print("+ Initializing")
    test = ConnectionTesting()
    # We'll start it high to force a check at beginning
    interval_num = test.SPEED_INTERVAL
    while True:
        try:
            test.summary()
            
            # Keep checking connection every CHECK_DELAY seconds
            # test speed intervals every SPEED_INTERVAL interval

            # If we don't have a connection, don't bother thinking about checking the speed
            while not test.ssl_check_connection():
                time.sleep(test.CHECK_DELAY)
            
            interval_num+=test.CHECK_DELAY
            if interval_num>=test.SPEED_INTERVAL:
                # If it worked, reset interval number
                if test.get_new_speeds():
                    interval_num=0
                # Otherwise, start the loop over to check our connection
                # Keep interval high so we're forced to re-check our speed
                else:
                    continue
            
            time.sleep(test.CHECK_DELAY)
            
        except KeyboardInterrupt:
            test._exit()
        # Otherwise let me know theres an issue and print it out and exit
        except Exception as e:
            print("! Something went wrong!")
            print(e)
            test._exit(1)

if __name__ == '__main__':
    main()
        
