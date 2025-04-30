import sys
import time
import threading
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives import serialization, hashes
import random
from socket import *
from decimal import Decimal
import ast
from subrosa import split_secret, recover_secret, Share
from custom_bloom_filter import BloomFilter
import datetime
from socket import socket, AF_INET, SOCK_DGRAM
import copy
import base64
import pickle

"""
pip install:
cryptography
bloom-filter
subrosa
copy
"""


generateQBFs = True
recentENCId = None
myChunks = []
DBF = BloomFilter(size_bits=819200, num_hashes=3)
QBF = BloomFilter(size_bits=819200, num_hashes=3)
CBF = BloomFilter(size_bits=819200, num_hashes=3)
programStartTime = datetime.datetime.now()
# A Dict which stores the current (max 6) bloom filters and their corresponding make times.
# Key: time of DBF creation
# Value: the DBF 
currDBFs = {}
currDBFs[programStartTime] = DBF
# A list which includes all encIDs in the DBF.
DBFlist = []
DBFTimeStamp = []
localNodeID = str(random.randint(1, 1000000))
encidList = []
allDBFs = []
encodeIDFound = False
covid = False

def reconstructedSecret(shares):
    secret = recover_secret(shares)
    return int.from_bytes(secret, byteorder='big')



def listenShares(k):
    global myChunks

    # Keys: SenderID.
    # Values: An array of chunks collected from a sender.
    # Array needs to be reset if a new hash is received from a sender.
    collectedChunks = {}

    # Keys: SenderID.
    # Values: The most recent hash received from a sender.
    prevHash = {}


    nodeSocket = socket(AF_INET, SOCK_DGRAM)
    nodeSocket.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
    nodeSocket.bind(("", 50000))

    while True:
        data, address = nodeSocket.recvfrom(1024)
        chunk = data.decode('utf-8').split("||")


        chunkRecv = eval(chunk[0])
        hashRecv = eval(chunk[1])
        senderID = chunk[2].strip()
        chunksNeeded = int(chunk[3].strip())

        # Ignoring chunks received from self. 
        if chunkRecv in myChunks:
            continue
        
        sendProbability = random.random()
        # if sendProbability < 0.5:
        #     continue
        
        if senderID not in collectedChunks:
            collectedChunks[senderID] = []

        if senderID not in prevHash:
            prevHash[senderID] = hashRecv

        elif prevHash[senderID] != hashRecv:
            # New hash means they are being received from a new secret.
            collectedChunks[senderID] = []
        
        prevHash[senderID] = hashRecv
        collectedChunks[senderID].append(chunkRecv)
        
        # Add the chunks received to the chunks array.
        print(f"[>] Received Chunk {len(collectedChunks[senderID])} out of {chunksNeeded}: {chunkRecv} from client number {senderID}")

        shares = [Share.from_bytes(share) for share in collectedChunks[senderID]]

        if len(collectedChunks[senderID]) == chunksNeeded:
            print(f"{chunksNeeded} out of {chunksNeeded} received. Now reconstructing EphID.")
            try:
                shares = [Share.from_bytes(share) for share in collectedChunks[senderID]]
                secretRecv = reconstructedSecret(shares)
                if hashRecv == hash(secretRecv):
                    print(f"Correct secret has been found. EncID will now be made with client number {senderID}")
                    secretRecvBytes = secretRecv.to_bytes((secretRecv.bit_length() + 7) // 8, byteorder='big')
                    handle_diffie_hellman_exchange(ephIDprivKey, secretRecvBytes, senderID)
                collectedChunks[senderID] = []
                
            except Exception as e:
                print(f"Error processing chunks: {e}")
                collectedChunks[senderID] = []

    
    nodeSocket.close()



def broadcastShares(chunks, ephIDhash, k):
    length = len(chunks)

    # Setup UDP connection
    nodeSocket = socket(AF_INET, SOCK_DGRAM)
    nodeSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    for i in range(0, length):
        print(f"[>] Broadcasting: {str(chunks[i])}")

        message = str(chunks[i]) + "||" 
        message += str(ephIDhash) + "||"
        message += localNodeID + "||"
        message += str(k)
        nodeSocket.sendto(message.encode('utf-8'), ("255.255.255.255", 50000))

        time.sleep(3)
    
    nodeSocket.close()
        

def generateEphemeral(t, k, n):
    while True:
        global myChunks, ephIDBytes, ephIDprivKey

        ephIDprivKey = X25519PrivateKey.generate()
        EphID = ephIDprivKey.public_key()

        ephIDBytes = EphID.public_bytes(
            encoding=serialization.Encoding.Raw, 
            format=serialization.PublicFormat.Raw 
        )
        ephIDInt = int.from_bytes(ephIDBytes, byteorder='big')
        ephIDhash = hash(ephIDInt)
        print("=" * 60)
        print(f"New EphIDInt generated: {ephIDInt}")

        chunks = split_secret(ephIDBytes, k, n)
        print(f"{n} chunks creted.")
        for i in range (0, n):
            print(f"Chunk #{i}: {chunks[i]}")

        myChunks = [bytes(chunk) for chunk in chunks]

        broadcastShares(myChunks, ephIDhash, k)

        time.sleep(t)

def generateEncid(privateKey, nodeEphID):
    try:
        # Calculate the node pk with ephIDBytes
        nodePublicKey = X25519PublicKey.from_public_bytes(nodeEphID)
        shareKey = privateKey.exchange(nodePublicKey)
        digest = hashes.Hash(hashes.SHA256())
        digest.update(shareKey)
        encid = digest.finalize()
        print("computing the shared secret EncID by using Diffie Hellman key exchange mechanism.")
        print(f"$$ EncID Created: {encid.hex()}\n")
        return encid
    
    
    except Exception as e:
        print(f"Failed to generate DHKE: {e}")

def handle_diffie_hellman_exchange(private_key, nodeEphID, sender_id):  
    try:
        encid = generateEncid(private_key, nodeEphID)
        
        if encid:
            print(f"LocalNode {localNodeID} and remoteNode {sender_id} have arrived at the same EncID value. ")

            
            # encoding the generated EncID to DBF
            encodingAndDeletingEncID(encid)
    except Exception as e:
        print(f"Error in Diffie-Hellman exchange: {e}")





# Add the encoded EncID to the Daily Bloom Filter
def encodingAndDeletingEncID(encid):
    global DBF
    encid_hex = encid.hex()

    print("[>] Encoding to DBF")
    print(f"[>] EncID {encid_hex} deleted after adding to Bloom Filter.\n")
    addEncIDToDBF(encid_hex)
    print(f"[>] EncID {encid_hex} added to Daily Bloom Filter.\n")





def addEncIDToDBF(encid_hex):
    global DBFlist, DBFTimeStamp, recentENCId
    
    current_time = datetime.datetime.now()
    
    # initialize timestamp
    if not DBFTimeStamp:
        DBFTimeStamp.append(current_time)
        DBFlist = []
    
    DBFlist.append(encid_hex)
    
    print(f"[>][{DBFTimeStamp[0].strftime('%Y-%m-%d %H:%M:%S')}] Current DBF has: {len(DBFlist)} EncIDs stored")
    
    DBF.add(encid_hex)
    recentENCId = encid_hex


def DBF_manager(t):
    global DBF, DBFlist, DBFTimeStamp, allDBFs, currDBFs, programStartTime
    
    # time duration for QBF
    delete_duration = t * 6 * 6
    
    while True:
        time.sleep(t * 6) 
        
        current_time = datetime.datetime.now()  

        DBF = BloomFilter(size_bits=819200, num_hashes=3)
        currDBFs[current_time] = DBF

        copyDBFs = currDBFs.copy()
        for ct in copyDBFs:
            if (current_time - ct).total_seconds() >= delete_duration: 
                currDBFs.pop(ct)

        # Showing DBF infos
        print("\n[>] All stored DBFs.")
        for tm, dbf in currDBFs.items():
            age_seconds = (current_time - tm).total_seconds()
            print(f"\n    DBF {dbf}: Created at {tm.strftime('%Y-%m-%d %H:%M:%S')} ({age_seconds} seconds ago)")

        print("\n")



def combineDBFtoQBF(t):
    global allDBFs, currDBFs, generateQBFs
    QBF = BloomFilter(size_bits=819200, num_hashes=3)
    Dt = t * 6 * 6

    while generateQBFs:
        time.sleep(Dt)  # Sleep for Dt minutes (converted to seconds)
        # Meaning node has covid and no longer generates QBFs.
        if covid:
            print("[>>] Covid detected. Terminating QBF generation.")
            break

        if len(currDBFs) == 0:
            continue

        current_time = datetime.datetime.now()
        print(f"[>] Combining DBFs into QBF at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        copyDbfs = currDBFs.copy()
        for dbf in copyDbfs.values():
            QBF.union(dbf)

        sendQBFToBackend(QBF)


def sendQBFToBackend(QBF):
    global recentENCId
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect(('localhost', 51001))

        message = ("QBF", QBF)
        serialized = pickle.dumps(message)

        clientSocket.sendall(serialized)
        # tell the server we're done writing
        clientSocket.shutdown(SHUT_WR)

        # read and print the server’s reply
        response = clientSocket.recv(30).decode('utf-8')
        print(f"[Client] QBF match result: {response}")
        print("!" * 100)
    finally:
        clientSocket.close()



def combineDBFtoCBF():
    global allDBFs, CBF, DBFlist, currDBFs

    added = False
    current_time = datetime.datetime.now()
    print(f"[>] Combining DBFs into CBF at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Verifies if the last key, value pair in the dictionary is the same, if not the same as the current DBF being edited,
    # then needs to be added into the dictionary to be sent to the backend.
    lkey = list(currDBFs.items())[-1][1]
    if len(currDBFs) < 6 and lkey.backend.array_ != DBF.backend.array_:
        current_time = datetime.datetime.now()
        currDBFs[current_time] = DBF
        added = True

    # Combine all DBFs into a single CBF.
    for dbf in currDBFs.values():
        CBF.union(dbf)

    
    print("[>] Sending CBFs to backend.")
    
    tcp_sendCBF = threading.Thread(target=sendCBF, args=(CBF, added), daemon=True)  
    tcp_sendCBF.start()

def sendCBF(CBF, added):
    global localNodeID, generateQBFs, currDBFs
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect(('localhost', 51001))

        message = ("CBF", CBF)
        serialize = pickle.dumps(message)
        clientSocket.send(serialize)
        clientSocket.shutdown(SHUT_WR)
        
        print(clientSocket.recv(30).decode('utf-8'))
        print(f"Node #{localNodeID} will now terminate QBF generation.")
        generateQBFs = False
        if added: 
            currDBFs.popitem()
    finally:
        clientSocket.close()



def main():
    global localNodeID, ephIDprivKey, ephIDBytes, t, k, n, covid
    tSet = {15, 18, 21, 24, 27, 30}

    if len(sys.argv) != 4:
        print("This programs expects 4 arguments: t, k, n")
        sys.exit(1)
    
    t = int(sys.argv[1])
    k = int(sys.argv[2])
    n = int(sys.argv[3])

    if t not in tSet:
        print(f"t value must be an element of the set {tSet}")
        print("Usage: python3 Dimpy.py [t] [k] [n]")
        sys.exit(1)
    elif k < 3:
        print("k must be greater than or equal to 3")
        print("Usage: python3 Dimpy.py [t] [k] [n]")
        sys.exit(1)
    elif n < 5: 
        print("n must be greater than or equal to 5")
        print("Usage: python3 Dimpy.py [t] [k] [n]")
        sys.exit(1)
    elif k >= n:
        print("k must be less than n")
        print("Usage: python3 Dimpy.py [t] [k] [n]")
        sys.exit(1)
    print("=" * 60)
    print(f"DIMY Client starting")
    print(f"Local_Node_ID: {localNodeID}")
    print("=" * 60)
    print("If covid positive please press [y] at any given time.")
    print("Do you have covid?")
    time.sleep(1)


    dbf_thread = threading.Thread(target=DBF_manager, args=(t,))
    dbf_thread.daemon = True
    dbf_thread.start()
    # Start listening for broadcasts.
    chunkListen = threading.Thread(target=listenShares, args=(k,), daemon=True)  
    chunkListen.start()

    ephid_thread = threading.Thread(target=generateEphemeral, args=(t, k, n), daemon=True)
    ephid_thread.start()

    qbf_thread = threading.Thread(target=combineDBFtoQBF, args=(t,), daemon=True)
    qbf_thread.start()


    while True:
        i = input()
        
        covid = not covid 

        cbf_thread = threading.Thread(target=combineDBFtoCBF, daemon=True)
        cbf_thread.start()



if __name__ == "__main__":
    main()
