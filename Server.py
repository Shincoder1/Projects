import sys
from socket import *
from datetime import datetime
import re

# Key = client address
# Value = their corresponding username 
loggedInUsers = {}
# Key = client address
# Value = last heartbeat 
activeUsers = {}
# Key = client address
# Value = tcp listening port
tcpPorts = {}

# Key = the filename
# Value = An array of usernames who have published said file
publishedFiles = {}


# Initially reading all users into a dict
def readUsers():
    users = {}
    with open('credentials.txt', 'r') as file: 
        for line in file:
            username = line.strip().split()[0]
            password = line.strip().split()[1]
            users[username] = password
    return users 



def authenticate(details, users, clientAddress, port):
    now = datetime.now()
    username = details.split()[0]
    password = details.split()[1]

    print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress} Received AUTH from {username}")

    # Checking if a client is already logged in with the same user.
    if username in loggedInUsers.values():
        print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress} Sent ERR {username}")
        return False

    # Going through dict of users from credentials.txt (or where ever username/password 
    # is being kept)
    for registeredUsername in users:
        if registeredUsername == username and users[registeredUsername] == password:
            print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress} Sent OK to {username}")
            loggedInUsers[clientAddress] = username
            activeUsers[clientAddress] = now
            tcpPorts[clientAddress] = port
            return True

    print(f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress} Sent ERR {username}")
    return False 

# LPF function
def lpf():
    files = ""
    # Goes through publishedFiles dict. Each filename (key) has a list of 
    # usernames
    for filename, usernames in publishedFiles.items():
        # Going through the list of usernames
        for user in usernames:
            if user in loggedInUsers.values(): 
                files += f"{filename} "

    return files


# Given a username, find its corresponding client address it is logged in as
def getClientAddress(usernames, currentAddress):
    for user in usernames: 
        for clientAddress, clientUser in loggedInUsers.items():
            if clientUser == user and clientAddress != currentAddress:
                return clientAddress
    return None 
    
# Function which checks for inactive users and removes them from the activeUsers 
# and loggedInUsers dict
def removeInactiveUsers():
    global activeUsers, loggedInUsers
    deleteUsers = []
    for user in activeUsers:
        now = datetime.now()
        if (now - activeUsers[user]).total_seconds() >= 3:
            deleteUsers.append(user)

    for user in deleteUsers:
        del loggedInUsers[user]
        del activeUsers[user]


if __name__ == '__main__':
    port = int(sys.argv[1])
  
    users = readUsers()

    serverSocket = socket(AF_INET, SOCK_DGRAM)
    serverSocket.bind(('localhost', port))

    while 1:
        # Checking for inactive users
        removeInactiveUsers()

        message, clientAddress = serverSocket.recvfrom(2048)
        text = message.decode('utf-8').split()

        # Might get caught at the recvfrom line, and thus might not update active
        # users dict; so updating activeUsers and loggedInUsers dict here.
        removeInactiveUsers()

        if text[0] == 'AUTH':
            newText = f"{text[1]} {text[2]}"
            if authenticate(newText, users, clientAddress, int(text[3])):
                serverSocket.sendto('Success'.encode('utf-8'), clientAddress)
            else:
                serverSocket.sendto('Failure'.encode('utf-8'), clientAddress)

        elif text[0] == 'HBT':
            if clientAddress in loggedInUsers:
                now = datetime.now()
                print(
                    f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                    f"Received HBT from {loggedInUsers[clientAddress]}"
                )
                activeUsers[clientAddress] = now

        elif text[0] == 'lap':
            now = datetime.now()
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Received LAP from {loggedInUsers[clientAddress]}"
            )
            if len(activeUsers) == 0:
                serverSocket.sendto('No active peers'.encode('utf-8'), clientAddress)

            activeUserList = ""
            tempDict = {}
            
            for user in activeUsers:
                # If users are the same then skip
                if clientAddress == user:
                    tempDict[clientAddress] = activeUsers[clientAddress]
                    continue
                elif (now - activeUsers[user]).total_seconds() < 3:
                    tempDict[clientAddress] = activeUsers[clientAddress]
                    activeUserList += f"{loggedInUsers[user]} "
                # If user is no longer active
                else:
                    del loggedInUsers[user]
            activeUsers = tempDict
            serverSocket.sendto(activeUserList.encode('utf-8'), clientAddress)
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Sent OK to {loggedInUsers[clientAddress]}"
            )
       
        elif text[0] == 'pub':
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Received PUB from {loggedInUsers[clientAddress]}"
            )
            
            filename = text[1]
            if filename not in publishedFiles:
                publishedFiles[filename] = []
            
            username = loggedInUsers[clientAddress]

            if username not in publishedFiles[filename]:
                publishedFiles[filename].append(username)

            serverSocket.sendto('Success'.encode('utf-8'), clientAddress)
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Sent OK to {loggedInUsers[clientAddress]}"
            )

        elif text[0] == 'lpf':
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Received LPF from {loggedInUsers[clientAddress]}"
            )
            
            # Set removes any duplicates found
            files = lpf().split()
            files = set(files)
            f = ""
            for file in files:
                f += f"{file} "

            serverSocket.sendto(f.encode('utf-8'), clientAddress)
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Sent OK to {loggedInUsers[clientAddress]}"
            )

        elif text[0] == "sch":
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Received SCH from {loggedInUsers[clientAddress]}"
            )

            substring = text[1]
            userOwnsFile = False
            existingFiles = ""
    
            for filename, usernames in publishedFiles.items():
                if re.search(substring, filename):
                    # Now check if the user who requested file is in list of users
                    # who have published said file. 
                    for username in usernames:
                        loggedinUser = loggedInUsers[clientAddress]
                        if username == loggedinUser:
                            userOwnsFile = True
                            break
                    if not userOwnsFile:
                        existingFiles += f"{filename} "
                    else:
                        userOwnsFile = False

            serverSocket.sendto(existingFiles.encode('utf-8'), clientAddress)
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                f"Sent OK to {loggedInUsers[clientAddress]}"
            )

        elif text[0] == "unp":
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}"
                f"Received UNP from {loggedInUsers[clientAddress]}"
            ) 

            filename = text[1]
            username = loggedInUsers[clientAddress]
            
            if filename in publishedFiles and username in publishedFiles[filename]:
                publishedFiles[filename].remove(username)
                # Delete the list of client usernames correlated with a file if it is 
                if len(publishedFiles[filename]) == 0:
                    del publishedFiles[filename]
                serverSocket.sendto('Success'.encode('utf-8'), clientAddress)
                print(
                    f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                    f"Sent OK to {loggedInUsers[clientAddress]}"
                )

            else: 
                serverSocket.sendto('Error'.encode('utf-8'), clientAddress)
                print(
                    f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                    f"Sent ERR to {loggedInUsers[clientAddress]}"
                )

        elif text[0] == "get":
            print(
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}"
                f"Received GET from {loggedInUsers[clientAddress]}"
            ) 

            requestedFile = text[1]
            userOwns = False

            availableFiles = lpf().split()
            
            cA = None
            for filename in availableFiles:
                if filename == requestedFile:
                    cA = getClientAddress(publishedFiles[filename], clientAddress)
                    port = tcpPorts[cA]
                    

                    message = f"{cA[0]} {port}"
                    if cA is not None: 
                        serverSocket.sendto(message.encode('utf-8'), clientAddress)
                        print(
                            f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                            f"Sent OK to {loggedInUsers[clientAddress]}"
                        )

            if cA is None:
                cA = "None"
                serverSocket.sendto(cA.encode('utf-8'), clientAddress)
                print(
                    f"{now.strftime('%Y-%m-%d %H:%M:%S')} {clientAddress}" 
                    f"Sent ERR to {loggedInUsers[clientAddress]}"
                )    
