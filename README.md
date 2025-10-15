WEBSITE STATUS CHECKER
In some cases, we have the largest of domains and sub domains which need to be tested for security flaws. the first step is to check the activeness in the domains on the internet. A recce tool is an automated tool that is developed in the Python language which has the potential to scan 11k domains in just 3 minutes and return their status. Recce tool also supports saving the results in text formatted tile. This tool is available on GitHub for free. It's open-source so anyone can contribute to it.
Recce refers to several different tools, so website status checker information depends on which tool is being referenced. The two most relevant are a website/domain status checker for security testing and a data validation tool for data teams. 
Recce (unstabl3/recce)—Website status checker
This is an open-source Python tool for security professionals and ethical hackers. 

•	Primary function: Scans domains and subdomains from a list to check if they are "alive" or active on the internet.
•	Purpose: Primarily used for the initial reconnaissance (or "recce") phase of penetration testing to quickly identify a large number of active domains that need further testing.
•	Key features:
o	High performance: Can scan thousands of domains in minutes.
o	Python-based: Developed in Python, making it accessible for users familiar with scripting.
o	List processing: Takes a list of domains from a text file (domains.txt).
o	Result saving: Saves the output of active domains to a text file (results.txt).

Website status check process:
1.The tool reads a list of domains from a provided text file.
2.It sends automated requests to each domain to determine its live status.
3.The results are then compiled and displayed. 




Note: Make Sure You have Python Installed on your System, as this is a python-based tool.
 <img width="965" height="225" alt="image" src="https://github.com/user-attachments/assets/f3172e94-3335-4857-b8c4-43f17aca60d8" />


Installation of Recce Tool on Kali Linux OS:

Step 1: Use the following command to install the tool in your Kali Linux operating system.
 
<img width="965" height="332" alt="image" src="https://github.com/user-attachments/assets/1ba1f03c-77ff-4573-8f59-51206b888372" />


Step 2: Now use the following command to move into the directory of the tool. You have to move in the directory in order to run the tool.
<img width="969" height="398" alt="image" src="https://github.com/user-attachments/assets/9770c4f6-7ce7-4eb7-b93d-36934640d165" />

 
Step 3: You are in the directory of the recce. Now you have to install a dependency of the recce using the following command.
<img width="973" height="494" alt="image" src="https://github.com/user-attachments/assets/cdeb60b8-166d-4d93-8951-b1343ebd1976" />

 
Step 4: All the dependencies have been installed in your Kali Linux operating system.
 
<img width="971" height="351" alt="image" src="https://github.com/user-attachments/assets/14a52640-349c-4f4e-93aa-6f2233c35fd8" />

We have a list of multiple domains which will be checked for their activeness on the internet.
 <img width="972" height="220" alt="image" src="https://github.com/user-attachments/assets/4ad6f442-9977-4844-a9bc-a9a3668392dc" />


Working with Recce Tool on Kali Linux OS:

Example 1: Scan domains with input as a file
 
<img width="978" height="516" alt="image" src="https://github.com/user-attachments/assets/af6326ec-dafd-453d-8198-5e708fea10fa" />


We have got the live status of each domain that is being fetched from the domains.text file.
 


<img width="975" height="301" alt="image" src="https://github.com/user-attachments/assets/b30fc83f-8373-4460-afc7-29e4f1bb9c6b" />




Example 2: Writing output in a file
Command: python3 recce.py -f domains.txt -o result.text
We will be saving results in result.text file.
 

<img width="997" height="505" alt="image" src="https://github.com/user-attachments/assets/bcc34357-66cb-407f-8bd5-ecb61d8d9ae7" />


We have displayed the results in the text formatted file.
 
<img width="805" height="505" alt="image" src="https://github.com/user-attachments/assets/93300721-aaa6-4c2f-a04d-a99d0efdc597" />



Example 3: Verbose mode(to check the status of the live domain) and a number of threads
Command: python3 recce.py -f domains.txt -o result.txt -t 100 -v
We will be displaying the results in more verbose mode.

 <img width="940" height="385" alt="image" src="https://github.com/user-attachments/assets/34cdfac9-9af3-4c7c-bf9e-019ea6884e08" />



We have got the status and the response code.
 

<img width="999" height="413" alt="image" src="https://github.com/user-attachments/assets/ce3e6a51-4e1c-455e-acf7-cfde83d9813f" />




Key information about website status checkers:
•	HTTP status codes: These three-digit codes are the primary indicator of a website's health.
o	1xx (Informational): The request has been received and the process is continuing.
o	2xx (Success): The request was successfully received and processed. A "200 OK" code is the ideal response.
o	3xx (Redirection): Further action is required to complete the request. A "301 Moved Permanently" is a common example.
o	4xx (Client error): The request could not be fulfilled due to a client-side issue, such as a "404 Not Found" error.
o	5xx (Server error): The server failed to fulfill a valid request due to an internal server issue, such as a "500 Internal Server Error" or "503 Service Unavailable".

We are also trying some basic commands to check website status using below commands
Primarily a download tool, wget can also check for a website's availability without downloading the page's content. 
•	Command: wget --spider -S https://example.com
•	Output: The --spider option tells wget not to download anything but to display the server's headers and the HTTP status code. Look for a 200 OK status in the output. 

           

        <img width="855" height="638" alt="image" src="https://github.com/user-attachments/assets/2fe22616-2c4d-435c-9a39-c0608b1520ee" />
      
<img width="825" height="686" alt="image" src="https://github.com/user-attachments/assets/3d2dc484-a207-417c-b6de-5d5a7b135de5" />

             
Nikto is an open-source web server scanner that tests for common vulnerabilities and server misconfigurations. 
•	Command: nikto -h https://example.com
•	Use case: Scans a web server for security issues that could compromise its status. 
 <img width="940" height="404" alt="image" src="https://github.com/user-attachments/assets/21bbaa37-f037-4d0c-a169-963b3ca16ba3" />





WhatWeb
This advanced tool is a fingerprinting scanner that identifies web technologies used by a website, including its content management system (CMS), server, and JavaScript libraries. 
•	Command: whatweb https://example.com
•	Use case: Helps identify outdated software versions, which can be a security risk. 
<img width="940" height="300" alt="image" src="https://github.com/user-attachments/assets/586215e3-6eac-4213-bf36-8fd10d41881c" />

 
