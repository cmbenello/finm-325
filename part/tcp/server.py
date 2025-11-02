import socket
import time


server = socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("localhost", 9000))
server.listen() 

conn, addr = server.accept()
data = conn.recv(1024)
try:
    for i in range(100):
        conn.sendall(f"{i}\n".encode())
        time.sleep(0.1)
    conn.shutdown(socket.SHUT_WR)
finally:
    conn.close()
    server.close()