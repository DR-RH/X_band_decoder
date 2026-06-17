import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# from common.paths import X_BAND_DECODED_DIR

def read_bin(file_path):
    file_path = Path(file_path)
    # Specify the data type and optionally the number of elements to read
    # For example, if the file contains 32-bit floats, you can specify dtype=np.float32
    data_type = np.uint16  # Change this based on your data type

    # Read the binary file into a NumPy array
    with file_path.open("rb") as file:
        array_data = np.fromfile(file, dtype=data_type)
        array_data -= 1024

    # print(array_data.shape)
    image = array_data.reshape(3003, 3008)
    image = image.astype(np.int16)  
    return image

if __name__ == '__main__':
    # plt.ion()
    file_path = "data_sample/decoded_20260616143755.bin"
    image = read_bin(file_path)
    plt.ion()
    plt.imshow(image)
    plt.show()
    input()
