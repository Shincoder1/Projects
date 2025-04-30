from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from custom_bloom_filter import BloomFilter
import pickle
from bitarray import bitarray

if __name__ == '__main__':
    PORT = 51001
    storedCBF = []
    try:
        serverSocket = socket(AF_INET, SOCK_STREAM)
        # # allow quick restart
        # serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        serverSocket.bind(('localhost', PORT))
        serverSocket.listen(5)
        print(f"[Server] Listening on port {PORT}...")

        while True:
            conn, addr = serverSocket.accept()
            print(f"[Server] Connection from {addr}")

            data = b""
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk


            receivedFilter = pickle.loads(data)
            tagType, receivedBF = receivedFilter


            print(f"[Server] Received tag='{tagType}', BloomFilter={receivedBF}")


            if tagType == "CBF":
                storedCBF.append(receivedBF)
                CBF_length = len(storedCBF)
                print(f"Stored {CBF_length} CBF in total")
                conn.sendall(b"CBF upload successful.")

            elif tagType == "QBF":
                print("[Server] Recieveing QBF from client")

                # bitarray_in_bits = receivedBF.backend.array_
                # bitarray_in_bytes = bitarray_in_bits.tobytes()
                # tempBF = bitarray()
                # tempBF.frombytes(bitarray_in_bytes)
                qbf_bits = bitarray()
                qbf_bits.frombytes(receivedBF.backend.array_.tobytes())


                if not storedCBF:
                    conn.sendall("Not close contact".encode('utf-8'))
                else:
                    match = False
                    for cbf in storedCBF:
                        # CBF_bitarray = cbf.backend.array_
                        # CBF_bytes = CBF_bitarray.tobytes()
                        # tempCBF = bitarray()
                        # tempCBF.frombytes(CBF_bitarray)
                        # CBF_matching = (tempBF & tempCBF).any()
                        cbf_bits = bitarray()
                        cbf_bits.frombytes(cbf.backend.array_.tobytes())
                        

                        CBF_matching = (qbf_bits & cbf_bits).any()
                        if CBF_matching:
                            match = True
                            break

                    if match:
                        reply = "\nCLOSE CONTACT\n" + "!" * 60
                        conn.sendall(reply.encode('utf-8'))
                    else:
                        conn.sendall("Not a close contact\n".encode('utf-8'))
    finally:
        conn.close()
