# monitor-connection-speeds
monitor ISP connection speeds, output to sqlite db. w/ util file for output to csv.

This script periodically checks the SSL connectivity to https://1.1.1.1 and then performs a speed test using the speedtest-cli package.
The default connection check is every 10 minutes unless the SSL connectivity fails, at which point it will recheck the connection every 3 seconds until it can re-establish.

https://github.com/sivel/speedtest-cli

```
  pip install speedtest-cli
```


Status Line while running:
```
Total rows: 4, Last Down:896.61, Avg Down: 878.485, Last Ping: 9.588, Avg Ping: 12.3625, Last Up: 581.78, Avg Up: 593.855, Problems: 0
```


Outputting to CSV from Sqlite
```
$ python speedb2csv.py
+ Connecting to DB...
+ Querying...
+ Writing...
- Done!
$ cat speeds.csv
TYPE,DATETIME,STATUS,DOMAIN,CERT_SUBJECT,CERT_ISSUER,ERROR_MSG,PING,DOWNLOAD_SPEED_MB,UPLOAD_SPEED_MB
status,2020-05-23 19:16:15.469598,successful connection,1.1.1.1,cloudflare-dns.com,DigiCert ECC Secure Server CA,,,,
speed,2020-05-23 19:16:22.031896,,speedtest,,,,9.395,887.03,689.84
```
