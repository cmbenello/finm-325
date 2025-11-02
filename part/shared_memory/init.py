import posix_ipc
import mmap 
import struct

try:
    memory = posix_ipc.SharedMemory("/bank_balance", flags=posix_ipc.O_CREX, size=4)
except posix_ipc.ExistentialError:
    posix_ipc.unlink_shared_memory("/bank_balance")
    memory = posix_ipc.SharedMemory("/bank_balance", flags=posix_ipc.O_CREX, size=4)

try:
    semaphore = posix_ipc.Semaphore("/bank_lock", flags=posix_ipc.O_CREX, initial_value=1)
except posix_ipc.ExistentialError:
    posix_ipc.unlink_Semaphore("/bank_lock")
    memory = posix_ipc.Semaphore("/bank_lock", flags=posix_ipc.O_CREX, size=4)
    

mapfile = mmap.mmap(memory.fd, memory.size)
memory.close_fd()
mapfile.write(struct.pack("i", 0))
mapfile.close()