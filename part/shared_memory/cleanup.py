import posix_ipc

posix_ipc.unlink_shared_memory("/bank_balance")
posix_ipc.unlink_semaphore("/bank_lock")
print("Cleaned up shared memory and semaphore.")
