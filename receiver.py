#!/usr/bin/python3

# COMP3331 21T2 Assignment 
# Padawan Transport Protocol
# Implemented in python3
# By Cameron Huang
# z5251618

import sys
import pickle
from socket import *

class Receiver:
    def __init__(self, receiver_port, FileReceived):
        self.receiver_port = int(receiver_port)
        self.FileReceived = FileReceived

    socket = socket(AF_INET, SOCK_DGRAM)

    def receive_packet(self):
        print("Waiting...")
        data, client_address = self.socket.recvfrom(2048)
        packet = pickle.loads(data)
        return packet, client_address

    def create_ack_packet(self, sequence_num, ack_num):
        ack_packet = Packet(sequence_num, ack_num, None, syn=False, ack=True, fin=False)
        return ack_packet

    def create_fin_packet(self, sequence_num, ack_num):
        fin_packet = Packet(sequence_num, ack_num, None, syn=False, ack=False, fin=True)
        return fin_packet

    def send_packet(self, packet, client_address):
        self.socket.sendto(pickle.dumps(packet), client_address)

class Packet:
    # Constructor
    def __init__(self, sequence_num, ack_num, data, syn=False, ack=False, fin=False):
        self.sequence_num = sequence_num
        self.ack_num = ack_num
        self.data = data
        self.syn = syn
        self.ack = ack
        self.fin = fin

# Buffer to hold packets
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

    def empty_buffer(self):
        temp = []
        self.packets = temp

# Error checking
if len(sys.argv) != 3:
    print("Usage: python3 receiver.py <receiver_port> <FileReceived.txt>")
    sys.exit()
else:
    # Grab args and place in variables
    receiver_port = int(sys.argv[1])
    FileReceived = sys.argv[2]
    receiver = Receiver(receiver_port, FileReceived)
    receiver.socket.bind(('', receiver_port))

    # Set connection states
    connected = False
    teardown = False
    ack_received = False
    out_of_order = False

    # Packet sequence and ACK numbers
    seq_num = 0
    ack_num = 0
    expected_seq_num = 1
    last_received_seq_num = 0

    # Create buffer that holds packets which are received out of order
    buffer = Packet_Buffer()


    while True:
        ########################################################################
        # No connection with sender yet, wait for SYN
        print("Listening...")
        while(connected == False): # Change to if statement?
            syn_packet, sender_address = receiver.receive_packet()
            if syn_packet.syn == True:
                print("SYN received!")
                # Reply with SYNACK
                print("Replying with SYNACK!")
                ack_num += 1
                synack_packet = Packet(seq_num, ack_num, None, syn=True, ack=True, fin=False)
                receiver.send_packet(synack_packet, sender_address)
                seq_num += 1
                # Wait for ACK before establising connection
                while(ack_received == False):
                    ack_packet, sender_adrress = receiver.receive_packet()
                    if ack_packet.ack == True:
                        print("ACK received, connection established!")
                        ack_received = True
                        connected = True
        
        ########################################################################
        # Connected, commence receiving of data
        f = open(FileReceived, "a+")
        while(connected == True):
            for p in buffer.packets:
                print(p.sequence_num)
            # Receive packet
            packet, sender_address = receiver.receive_packet()
            # Discard duplicate packets
            if packet.sequence_num == last_received_seq_num:
                continue
            last_received_seq_num = packet.sequence_num
            # If FIN packet, start connection teardown
            if packet.fin == True:
                ack_num += 1
                print("FIN packet received, sending ACK, commence teardown")
                receiver.send_packet(receiver.create_ack_packet(seq_num, ack_num), sender_address)
                teardown = True
                break
            
            # Process packet (get data)
            if packet.data != None:
                print("Packet received with sequence number: " + str(packet.sequence_num))
                print("Expected sequence number is: " + str(expected_seq_num))
                # If packet received in correct order
                if packet.sequence_num == expected_seq_num:
                    f.write(packet.data)
                    ack_num += len(packet.data)
                    # If out of order
                    if out_of_order is True:
                        if buffer.size() > 0:
                            # If packets in buffer, and we have all packets in order
                            # write data of all packets to file and empty buffer
                            # send a cumulative ACK
                            if buffer.packets[0].sequence_num == (packet.sequence_num + len(packet.data)):
                                for p in buffer.packets:
                                    f.write(p.data)
                                buffer.empty_buffer()
                                out_of_order = False
                                print("Out of order packet received. Sending ACK with number: " + str(ack_num))
                                receiver.send_packet(receiver.create_ack_packet(seq_num, ack_num), sender_address)
                                expected_seq_num = ack_num
                            # If packets still not all in order, send more duplicate
                            # ACKs with next expected sequence number
                            # NOTE: turn into function due to repeated code
                            else:
                                expected_seq_num += len(packet.data)
                                print("Out of order packet received, but packets still out of order!")
                                print("Sending duplicate ACK with number: " + str(expected_seq_num))
                                out_of_order = True
                                receiver.send_packet(receiver.create_ack_packet(seq_num, expected_seq_num), sender_address)
                    # Else if packets in order, just reply with ACK
                    else:
                        # Reply with ACK
                        print("Sending ACK with number: " + str(ack_num))
                        receiver.send_packet(receiver.create_ack_packet(seq_num, ack_num), sender_address)
                        expected_seq_num = ack_num
                # Packet received out of order, send duplicate ACK
                else:
                    print("Packet out of order, sending duplicate ACK with number: " + str(expected_seq_num))
                    buffer.add_packet(packet)
                    ack_num += len(packet.data)
                    out_of_order = True
                    receiver.send_packet(receiver.create_ack_packet(seq_num, expected_seq_num), sender_address)


        f.close()

        # Connection teardown
        if teardown == True:
            seq_num += 1
            fin_packet = receiver.create_fin_packet(seq_num, ack_num)
            receiver.send_packet(fin_packet, sender_address)
            print("FIN packet sent! Exiting...")
            sys.exit()