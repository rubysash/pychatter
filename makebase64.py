import argparse
import base64
import os
import sys

def convert_to_base64(input_file, output_file):
    """
    Converts a binary file to a Base64-encoded file.

    :param input_file: Path to the input binary file.
    :param output_file: Path to the output Base64 file.
    """
    try:
        # Read the binary data
        with open(input_file, "rb") as infile:
            binary_data = infile.read()

        # Encode to Base64
        base64_data = base64.b64encode(binary_data)

        # Write the Base64 data to the output file
        with open(output_file, "wb") as outfile:
            outfile.write(base64_data)
        
        print(f"Successfully converted '{input_file}' to Base64 and saved it as '{output_file}'.")
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' does not exist.")
    except PermissionError:
        print(f"Error: Permission denied while accessing '{input_file}' or '{output_file}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Convert a binary file to a Base64-encoded file.",
        usage="python makebase64file.py -i <input_file> -o <output_file>"
    )
    parser.add_argument("-i", "--input", required=True, help="Path to the input binary file.")
    parser.add_argument("-o", "--output", required=True, help="Path to the output Base64 file.")

    # Parse arguments
    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.input):
        print(f"Error: The input file '{args.input}' does not exist or is not a file.")
        sys.exit(1)

    # Call the conversion function
    convert_to_base64(args.input, args.output)

if __name__ == "__main__":
    main()
