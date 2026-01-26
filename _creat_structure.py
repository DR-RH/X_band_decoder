import os

PROJECT_STRUCTURE = {
    "app": [
        "main.py",
        "decode_controller.py",
        "diagnosis.py"
    ],
    "common": [
        "decode_utils.py",
        "constants.py",
        "file_io.py"
    ],
    "tests": [
        "test_decode_utils.py",
        "test_diagnosis.py",
        "test_main_flow.py"
    ],
    "data": [
        "raw_data_unprocessed/.gitkeep",
        "raw_data_processed/.gitkeep",
        "loss_packet_group/.gitkeep"
    ],
    "output": [
        "report/.gitkeep",
        "X_band_decoded/.gitkeep"
    ]
}


def create_project_structure(base_path="."):
    for directory, files in PROJECT_STRUCTURE.items():
        dir_path = os.path.join(base_path, directory)
        os.makedirs(dir_path, exist_ok=True)

        for file in files:
            file_path = os.path.join(base_path, directory, file)
            # create subdirectories if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # only create file if it doesn't exist
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    pass

    print("Project structure created successfully.")


if __name__ == "__main__":
    create_project_structure()