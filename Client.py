# The client side of the peer-to-peer network. 

import sys
from socket import *
import threading
import time

connected = True

# This will become initialised after client queries server for a tcp port
tcpPeerPort = 0
# This will become initialised from the very beginning, as soon as 
# the client starts listening as a tcp socket.
tcpServerPort = 0
serverTcpSocket = None


# Heartbeat thread
def heartbeat(message, clientSocket):
    global connected
    time.sleep(2)
    while connected:
        try:
            clientSocket.sendto(message, ('localhost', port))
            time.sleep(2)
        except Exception:
            connected = False
            break


# This is the client side of the TCP Connection 
def downloadFile(senderIp, filename):
    tcpClientSocket = socket(AF_INET, SOCK_STREAM)
    # Connect to TCP socket
    tcpClientSocket.connect(('localhost', tcpPeerPort))
    tcpClientSocket.send(filename.encode('utf-8'))

    with open(filename, 'wb') as file:
        while 1:
            data = tcpClientSocket.recv(1024)  
            if not data:
                break
            file.write(data)
    print(f"{filename} downloaded successfully")

# This is the server side of the TCP Connection
def tcpListenFunc():
    global connected, serverTcpSocket, tcpServerPort
    serverTcpSocket = socket(AF_INET, SOCK_STREAM)
    serverTcpSocket.bind(('localhost', tcpServerPort))
    tcpServerPort = serverTcpSocket.getsockname()[1]
    
    serverTcpSocket.listen(5)
    
    while connected:
        try: 
            connectionSocket, addr = serverTcpSocket.accept()
            filename = connectionSocket.recv(1024).decode('utf-8')
            tcpConnection = threading.Thread(target=tcpDownload, args=(connectionSocket, filename))
            tcpConnection.start()
        except Exception as e:
            break
        
# This is being handled in a thread so the server side of the client
# can go do other things such as download a file as well. 
def tcpDownload(connectionSocket, filename):
    try:
        with open(filename, 'rb') as file:
            while 1:
                bytesData = file.read(1024)
                if not bytesData:
                    break
                
                connectionSocket.sendall(bytesData)
    finally:
        connectionSocket.close()


if __name__ == "__main__":
    port = int(sys.argv[1])

    clientSocket = socket(AF_INET, SOCK_DGRAM)

    # Begin the TCP server listen for the server side here. 
    tcpListen = threading.Thread(target=tcpListenFunc)
    tcpListen.start()

    while 1:
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()

        details = f"AUTH {username} {password} {tcpServerPort}"
        clientSocket.sendto(details.encode('utf-8'), ('localhost', port))
        
        response, serverAddress = clientSocket.recvfrom(2048)
        response = response.decode('utf-8')
        if response == 'Success':
            message = "HBT".encode('utf-8')
            # Begin heartbeat thread here
            heartbeat = threading.Thread(target=heartbeat, args=(message, clientSocket))
            heartbeat.start()
            break
        else: 
            print("Authentication failed. Please Try again.")

   
    print("Welcome to BitTrickle!")
    print("Available commands are: get, lap, lpf, pub, sch, unp, xit")

    while 1:
        command = input("> ")
        # LAP command
        if command == "lap":
            clientSocket.sendto('lap'.encode('utf-8)'), ('localhost', port))
            response, serverAddress = clientSocket.recvfrom(2048)
            response = response.decode('utf-8').split()

            if len(response) == 0:
                print("No active peers")
            elif len(response) == 1:
                print(f"1 active peer:\n{response[0]}")
            else: 
                print(f"{len(response)} active peers:")
                for peer in response:
                    print(peer)

        # LPF command
        elif command == "lpf":
            clientSocket.sendto('lpf'.encode('utf-8)'), ('localhost', port))
            response, serverAddress = clientSocket.recvfrom(2048)
            response = response.decode('utf-8').split()
        
            if len(response) == 0:
                print("No files published")
            elif len(response) == 1:
                print(f"{len(response)} file published:\n{response[0]}")
            else:
                print(f"{len(response)} files published:") 
                for filename in response:
                    print(filename)

        # XIT command
        elif command == "xit":
            print("Goodbye")
            connected = False
            serverTcpSocket.close()
            heartbeat.join()
            clientSocket.close()
            tcpListen.join()
            sys.exit()

        command = command.strip().split()
        # Pub command 
        if command[0] == "pub":
            command = f"{command[0]} {command[1]}"
            clientSocket.sendto(command.encode('utf-8)'), ('localhost', port))

            response, serverAddress = clientSocket.recvfrom(2048)
            response = response.decode('utf-8')
            
            print("File published successfully")

        # SCH command
        elif command[0] == "sch":
            command = f"{command[0]} {command[1]}"
            clientSocket.sendto(command.encode('utf-8)'), ('localhost', port))

            response, serverAddress = clientSocket.recvfrom(2048)
            response = response.decode('utf-8').split()

            if len(response) == 0:
                print("No files found")
            elif len(response) == 1:
                print(f"1 file found:\n{response[0]}")
            else:
                print(f"{len(response)} files found:")
                for file in response:
                    print(file)

        # UNP command
        elif command[0] == "unp":
            command = f"{command[0]} {command[1]}"
            clientSocket.sendto(command.encode('utf-8)'), ('localhost', port))

            response, serverAddress = clientSocket.recvfrom(2048)
            response = response.decode('utf-8')

            if response == "Success":
                print("File unpublished successfully")
            else:
                print("File unpublication failed")

        # GET command
        elif command[0] == "get":
            filename = command[1]
            command = f"{command[0]} {command[1]}"
            clientSocket.sendto(command.encode('utf-8)'), ('localhost', port))

            response, serverAddress = clientSocket.recvfrom(2048)
            response = response.decode('utf-8').split()
            if response[0] == "None":
                print("File not found")
                continue
            
            senderIp = response[0]
            tcpPeerPort = int(response[1])
            downloadFile(str(senderIp), filename)
