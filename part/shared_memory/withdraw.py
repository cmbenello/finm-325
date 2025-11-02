import posix_ipc
import mmap
import struct

memory = posix_ipc.SharedMemory("/bank_balance")
semaphore = posix_ipc.Semaphore("/bank_lock")

mapfile = mmap.mmap(memory.fd, memory.size)
memory.close_fd() 


add_balance = -1
for _ in range(100_000):
    semaphore.acquire()
    mapfile.seek(0)
    balance_bytes = mapfile.read(4)
    balance = struct.unpack("i", balance_bytes)[0]

    balance += add_balance

    mapfile.seek(0)
    mapfile.write(struct.pack("i", balance))
    semaphore.release()

mapfile.seek(0)
balance_bytes = mapfile.read(4)
balance = struct.unpack("i", balance_bytes)[0]
print(balance)

# Clean up
mapfile.close()