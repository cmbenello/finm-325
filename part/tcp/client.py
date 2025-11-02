import socket 

client = socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM)
client.connect(("localhost", 9000))
client.send(b"Hello from client")
response = client.recv(1024)
curr_average = 0
count = 0
with client.makefile("r") as f:
    for line in f:
        num = int(line)
        curr_average += num
        count += 1
        print("server says:", line.strip())
        print("current average :", curr_average / count)
client.close()