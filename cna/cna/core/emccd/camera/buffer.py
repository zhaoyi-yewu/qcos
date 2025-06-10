import ctypes


def create_uint32_buffer(size: int) -> ctypes.Array[ctypes.c_uint32]:
    """
    Args:
        size: total number of int32
    """
    return (ctypes.c_uint32 * size)()
