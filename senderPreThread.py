#!/usr/bin/python3

# COMP3331 21T2 Assignment 
# Padawan Transport Protocol
# Implemented in Python 3
# By Cameron Huang
# z5251618

from os import sync
import sys
import pickle
import time
import random
from socket import *

class Sender:
    # Constructor
    def __init__(self, receiver_host_ip, receiver_port, FileToSend, MWS, MSS, timeout, pdrop, seed):
        self.receiver_host_ip = receiver_host_ip
        self.receiver_port = int(receiver_port)
        self.FileToSend = FileToSend
        self.MWS = int(MWS)
        self.MSS = int(MSS)
        self.timeout = int(timeout)
        self.pdrop = int(pdrop)
        self.seed = int(seed)

    socket = socket(AF_INET, SOCK_DGRAM)
    time_last_pkt_sent = 0
    

    def receive_packet(self):
        print("Waiting...")
        data, client_address = self.socket.recvfrom(2048)
        packet = pickle.loads(data)
        return packet, client_address

    def create_syn_packet(self, sequence_num, ack_num):
        syn_packet = Packet(sequence_num, ack_num, None, syn=True, ack=False, fin=False)
        return syn_packet

    def create_data_packet(self, sequence_num, ack_num, data):
        data_packet = Packet(sequence_num, ack_num, data, syn=False, ack=False, fin=False)
        return data_packet

    def create_ack_packet(self, sequence_num, ack_num):
        ack_packet = Packet(sequence_num, ack_num, None, syn=False, ack=False, fin=False)
        return ack_packet

    def send_packet(self, packet):
        self.socket.sendto(pickle.dumps(packet), (self.receiver_host_ip, self.receiver_port))
        self.time_last_pkt_sent = time.time()

    # This function emulates packet drop by generating a random float in the range
    # [0, 1] and drops the packet if it is less than or equal to pdrop
    # Seed initialised at start of program
    def PLD(self):
        r = random.random()
        if (r > self.pdrop):
            return False
        else:
            return True

    # This function splits the data into packet playloads of size equal to the given MSS
    # It takes in the data and the index of where to start creating the payload
    def split_payload(self, data, index):
        data_length = len(data)
        end_segment = index + self.MSS
        if (end_segment > data_length):
            payload = data[index:data_length]
        else:
            payload = data[index:end_segment]


class Packet:
    # Constructor
    def __init__(self, sequence_num, ack_num, data, syn=False, ack=False, fin=False):
        self.sequence_num = sequence_num
        self.ack_num = ack_num
        self.data = data
        self.syn = syn
        self.ack = ack
        self.fin = fin

# Buffer to hold packets where maximum size of the buffer is MWS
class Packet_Buffer:
    # Constructor
    def __init__(self):
        self.packets = []

    def add_packet(self, packet):
        self.packets.append(packet)

    def remove_packet(self, packet):
        self.packets.remove(packet)

    def buffer_is_empty(self):
        if len(self.packets == 0):
            return True
        else:
            return False

    def size(self):
        return len(self.packets)


# Error checking
if len(sys.argv) != 9:
    print("Usage: python3 sender.py <receiver_host_ip> <receiver_port> <FileToSend> <MWS> <MSS> <timeout> <pdrop> <seed>")
    sys.exit()
else:
    # Grab args and place in variables
    receiver_host_ip = sys.argv[1]
    receiver_port = sys.argv[2]
    FileToSend = sys.argv[3]
    MWS = int(sys.argv[4])
    MSS = sys.argv[5]
    timeout = int(sys.argv[6])
    pdrop = sys.argv[7]
    seed = int(sys.argv[8])

    # Set connection states
    connected = False
    ack_received = False
    num_duplicate_acks = 0

    # Packet sequence and ACK numbers
    seq_num = 0
    ack_num = 0

    # Set seed
    random.seed(seed)

    # Holds packets which are waiting to be ACKed
    packet_buffer = Packet_Buffer()
    
    # Create sender object
    sender = Sender(receiver_host_ip, receiver_port, FileToSend, MWS, MSS, timeout, pdrop, seed)

# Main loop
while True:
    ############################################################################
    # No connection yet with receiver, so we'll commence 3 way handshake
    if connected == False:
        print("Sending SYN packet!")
        syn_packet = Packet(seq_num, ack_num, None, syn=True, ack=False, fin=False)
        sender.send_packet(syn_packet)
        seq_num += 1
        # Wait for SYNACK from receiver
        while(connected == False):
            synack_packet, client_address = sender.receive_packet()
            if synack_packet.syn == True and synack_packet.ack == True:
                print("SYNACK received!")
                ack_received = True
                # Check if correct ACK num, then reply with ACK
                if synack_packet.ack_num == seq_num:
                    print ("Replying with ACK!")
                    ack_packet = Packet(seq_num, synack_packet.sequence_num + 1, None, syn=False, ack=True, fin=False)
                    sender.send_packet(ack_packet)
                    print ("Connection established!")
                    connected = True
            # Retransmit SYN due to timeout
            time_since_sent = (time.time() - sender.time_last_pkt_sent)
            if time_since_sent > timeout:
                print("Retransmitting SYN due to timeout")
                sender.send_packet(syn_packet)
    ############################################################################
    # Connected, commence transmission of data

# starting MWS implementation
################################################################################
    # Initialise buffer
    buffer = Packet_Buffer()
    # Keep sending packets until number of unACKed packets equals MWS
    oldest_packet_ACKed = True
    # Assume MWS of size 1`initially
    while(buffer.size <= MWS):
        # Only need to maintain timer for oldest unACKed packet
        if (oldest_packet_ACKed == True):
            # Start timer?
            print("How the fuck does multithreading work?")
################################################################################


    if ack_received == True:
        print("Commencing sending of data")
        # Send packet 
        print("Sending...")
        f = open(FileToSend, "r")
        data = f.read(1024) #change to buffer size
        packet = Packet(seq_num, ack_num, data, syn=False, ack=False, fin=False)
        sender.send_packet(packet)
        seq_num += len(packet.data)
        ack_received = False

    # Wait for ACK, retransmit if not received by timeout
    while(ack_received == False):
        print("Waiting for ACK...")
        ack_packet, client_address = sender.receive_packet()
        if ack_packet.ack == True: 
            # Check if ACK acknowledges last sent packet seq_num
            # print(str(ack_packet.ack_num))
            # print(str(seq_num))
            if ack_packet.ack_num == seq_num:
                print("ACK received!")
                ack_received = True
        # Retransmit due to timeout
        curr_time = time.time()
        time_since_sent = (curr_time - sender.time_last_pkt_sent)
        # print("Current time is: " + str(curr_time))
        # print("Time last packet sent: " + str(sender.time_last_pkt_sent))
        # print("Timeout is: " + str(timeout))
        # print("Time since last packet is: " + str(time_since_sent))
        if time_since_sent > timeout:
            print("Retransmitting due to timeout")
            sender.send_packet(packet)

    ############################################################################
    # Connection tear down


    # Remove this eventually, we are exiting early for now since were only sending
    # one packet
    print("File transfer complete, exiting!")
    sys.exit()