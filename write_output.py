import ctypes
import sys
import cdio

def list_devices():
    devices = []
    index = 0
    err_str = ctypes.create_string_buffer(256)

    while True:
        dev_name = ctypes.create_string_buffer(256)
        dev = ctypes.create_string_buffer(256)
        
        lret = cdio.DioQueryDeviceName(ctypes.c_short(index), dev_name, dev)
        if lret != cdio.DIO_ERR_SUCCESS:
            cdio.DioGetErrorString(lret, err_str)
            print(f"DioQueryDeviceName = {lret}: {err_str.value.decode('sjis')}")
            break

        devices.append(dev_name.value.decode('sjis'))
        index += 1

    return devices

def main():
    dio_id = ctypes.c_short()
    io_data = ctypes.c_ubyte()
    err_str = ctypes.create_string_buffer(256)

    # List available devices and ask the user to select one
    devices = list_devices()
    if not devices:
        print("No devices found.")
        sys.exit()

    print("Available devices:")
    for idx, dev in enumerate(devices):
        print(f"{idx + 1}: {dev}")

    try:
        dev_index = int(input(f"Select device (1-{len(devices)}): ")) - 1
        if dev_index < 0 or dev_index >= len(devices):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        sys.exit()

    dev_name = devices[dev_index]
    print(f"Selected device: {dev_name}")

    # Initialization
    lret = cdio.DioInit(dev_name.encode(), ctypes.byref(dio_id))
    if lret != cdio.DIO_ERR_SUCCESS:
        cdio.DioGetErrorString(lret, err_str)
        print(f"DioInit = {lret}: {err_str.value.decode('sjis')}")
        print("Possible causes:")
        print("1. Incorrect device name.")
        print("2. Driver not installed or not loaded.")
        print("3. Insufficient permissions.")
        print("4. Device file not found or inaccessible.")
        print("Try running the script with 'sudo' or check the device name and driver installation.")
        sys.exit()

    try:
        while True:
            # Get user input for bit number and value
            user_input = input("Enter bit number and value (e.g., '10 1'), or 'quit' to exit: ")
            if user_input.lower() == 'quit':
                break

            try:
                bit_no, bit_val = map(int, user_input.split())
                if bit_no < 0 or bit_no > 31 or bit_val not in [0, 1]:
                    raise ValueError
            except ValueError:
                print("Invalid input. Please enter a valid bit number (0-31) and value (0 or 1).")
                continue

            # Set the specified bit to the specified value
            io_data = ctypes.c_ubyte(bit_val)
            bit_no = ctypes.c_short(bit_no)

            # Write the value to the specified bit
            lret = cdio.DioOutBit(dio_id, bit_no, io_data)
            if lret != cdio.DIO_ERR_SUCCESS:
                cdio.DioGetErrorString(lret, err_str)
                print(f"Write error for Bit {bit_no.value} = {lret}: {err_str.value.decode('sjis')}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")

    # Cleanup
    lret = cdio.DioExit(dio_id)
    if lret != cdio.DIO_ERR_SUCCESS:
        cdio.DioGetErrorString(lret, err_str)
        print(f"DioExit = {lret}: {err_str.value.decode('sjis')}")

# Call main function
if __name__ == "__main__":
    main()

