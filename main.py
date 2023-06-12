import socket
import argparse
from struct import pack

DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'netascii'

OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
MODE = {'netascii': 0, 'octet': 1, 'mail': 2}

ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}

def send_rrq(filename, mode):
    rrq_message = pack(f'>h{len(filename)}sB{len(mode)}sB', OPCODE['RRQ'], filename.encode(), 0, mode.encode(), 0)
    sock.sendto(rrq_message, server_address)

def send_wrq(filename, mode):
    wrq_message = pack(f'>h{len(filename)}sB{len(mode)}sB', OPCODE['WRQ'], filename.encode(), 0, mode.encode(), 0)
    sock.sendto(wrq_message, server_address)

def send_ack(seq_num, server):
    ack_message = pack('>hh', OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server)

def receive_data(sock, file):
    seq_number = 1
    while True:
        data, server = sock.recvfrom(516)
        opcode = int.from_bytes(data[:2], 'big')
        if opcode == OPCODE['DATA']:
            seq_num = int.from_bytes(data[2:4], 'big')
            if seq_num == seq_number:
                send_ack(seq_num, server)
                file_block = data[4:]
                file.write(file_block)
                seq_number += 1
                if len(file_block) < BLOCK_SIZE:
                    break
        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')
            error_msg = data[4:].decode()
            raise Exception(f"TFTP Error {error_code}: {error_msg}")
        else:
            raise Exception("Unexpected response from the server")

def send_data(sock, file):
    seq_number = 1
    while True:
        data = file.read(BLOCK_SIZE)
        data_length = len(data)
        if data_length == 0:
            break
        data_packet = pack(f'>hh{data_length}s', OPCODE['DATA'], seq_number, data)
        sock.sendto(data_packet, server_address)
        while True:
            try:
                ack, server = sock.recvfrom(4)
                ack_opcode = int.from_bytes(ack[:2], 'big')
                ack_seq_num = int.from_bytes(ack[2:4], 'big')
                if ack_opcode == OPCODE['ACK'] and ack_seq_num == seq_number:
                    seq_number += 1
                    break
            except socket.timeout:
                sock.sendto(data_packet, server_address)

# Parse command line arguments
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument(dest="host", help="Server IP address", type=str)
parser.add_argument(dest="action", help="get or put a file", type=str)
parser.add_argument(dest="filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", dest="port", action="store", type=int)
args = parser.parse_args()

# Set server IP and port
server_ip = args.host
server_port = args.port if args.port else DEFAULT_PORT
server_address = (server_ip, server_port)

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)

try:
    # Send RRQ or WRQ message based on action
    mode = DEFAULT_TRANSFER_MODE
    filename = args.filename

    if args.action == 'get':
        send_rrq(filename, mode)
        file = open(filename, 'wb')
        receive_data(sock, file)
        file.close()
        print(f"File '{filename}' downloaded successfully.")

    elif args.action == 'put':
        send_wrq(filename, mode)
        file = open(filename, 'rb')
        send_data(sock, file)
        file.close()
        print(f"File '{filename}' uploaded successfully.")

except Exception as e:
    print(f"Error: {str(e)}")

finally:
    sock.close()
