import numpy as np
import matplotlib.pyplot as plt

def read_bin(file_path):
    # Specify the data type and optionally the number of elements to read
    # For example, if the file contains 32-bit floats, you can specify dtype=np.float32
    data_type = np.uint16  # Change this based on your data type

    # Read the binary file into a NumPy array
    with open(file_path, 'rb') as file:
        array_data = np.fromfile(file, dtype=data_type)
        array_data -= 1024

    # print(array_data.shape)
    image = array_data.reshape(3003, 3008)
    image = image.astype(np.int16)  
    return image

if __name__ == '__main__':
    plt.ion()
    file_path = 'output/X_band_decoded/decoded_20260107091356_20260126113939.bin'
    # file_path = '/Users/rh/Desktop/vertecs/experiment/focus_test/20240923_KG_line_30/NIR_Filter/data/20240923155834_0.bin'
    image = read_bin(file_path)
    plt.imshow(image)
    plt.show()
    input()