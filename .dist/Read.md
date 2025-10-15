 Step1: Make Sure You have Python Installed on your System, as this is a python-based tool. 
 ```bash
python3 --version
```

Step2: Use the following command to install the Recce tool in your Kali Linux operating system.
```bash
git clone https://github.com/unstabl3/recce
```

Step3: Now use the following command to move into the directory of the tool. You have to move in the directory in order to run the tool.
```bash
cd recce
```

Step4:You are in the directory of the recce. Now you have to install a dependency of the recce using the following command.
```bash
sudo pip install -r requirements.text
```

Step5: All the dependencies have been installed in your Kali Linux operating system.
```bash
python3 recce.py -h
```

Step6:We have a list of multiple domains which will be checked for their activeness on the internet.
```bash
cat> domains.text
```

Step7: Scan domains with input as a file 
```bash
python3 recce.py -f domains.text
```

Step8:  Writing output in a file 
```bash
 python3 recce.py -f domains.txt -o result.text 
 ```

 Step9: Verbose mode(to check the status of the live domain) and a number of threads 
 ```bash
 python3 recce.py -f domains.txt -o result.txt -t 100 -v
 ```

 Step10:We are also trying some basic commands to check website status using below commands 
 ```bash
  wget --spider -S https://example.com 
  nikto -h https://example.com
  whatweb https://example.com
```

Key information about website status checkers: 
• HTTP status codes: These three-digit codes are the primary indicator of a website's health. 
     o 1xx (Informational): The request has been received and the process is continuing. 
     o 2xx (Success): The request was successfully received and processed. A "200 OK" 
       code is the ideal response. 
     o 3xx (Redirection): Further action is required to complete the request. A "301 Moved 
       Permanently" is a common example. 
     o 4xx (Client error): The request could not be fulfilled due to a client-side issue, such 
       as a "404 Not Found" error. 
     o 5xx (Server error): The server failed to fulfill a valid request due to an internal server 
       issue, such as a "500 Internal Server Error" or "503 Service Unavailable".