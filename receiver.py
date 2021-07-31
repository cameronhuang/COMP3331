#!/usr/bin/python3

# COMP3331 21T2 Assignment 
# Padawan Transport Protocol
# Receiver
# Implemented in python3
# By Cameron Huang
# z5251618

import sys
import pickle
from socket import *
import time

class Receiver:
    def __init__(self, receiver_port, FileReceived):
        self.receiver_port = int(receiver_port)
        self.FileReceived = FileReceived

    socket = socket(AF_INET, SOCK_DGRAM)

    def receive_packet(self):
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

    def log(self, file, packet, action):
        time_since_start = round(time.time() - start_time, 2)
        packet_data_size = 0
        packet_flag = ""
        if packet.syn == True:
            packet_flag += "S"
        if packet.ack == True:
            packet_flag += "A"
        if packet.fin == True:
            packet_flag += "F"
        if packet.data != None:
            packet_flag += "D"
            packet_data_size = len(packet.data)
        string = '{:<8s}{:<12s}{:<8s}{:<10s}{:<10s}{:<10s}'.format(str(action), 
                  str(time_since_start), str(packet_flag), str(packet.sequence_num), 
                  str(packet_data_size), str(packet.ack_num))
        file.write(string + "\n")

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
    start_time = time.time()

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

    # Statistics
    data_received = 0
    data_packets_received = 0
    duplicate_packets_received = 0

    # Create buffer that holds packets which are received out of order
    buffer = Packet_Buffer()

    # Create log file
    l = open("Receiver_log.txt", "a+")
    string = '{:<8s}{:<12s}{:<8s}{:<10s}{:<10s}{:<10s}'.format("ACTION", "TIME",
            "FLAGS", "SEQ", "DATA", "ACK")
    l.write(string + "\n")
    l.write("--------------------------------------------------------\n")


    while True:
        ########################################################################
        # No connection with sender yet, wait for SYN
        while(connected == False): # Change to if statement?
            syn_packet, sender_address = receiver.receive_packet()
            receiver.log(l, syn_packet, "rcv")
            if syn_packet.syn == True:
                # Reply with SYNACK
                ack_num += 1
                synack_packet = Packet(seq_num, ack_num, None, syn=True, ack=True, fin=False)
                receiver.send_packet(synack_packet, sender_address)
                receiver.log(l, synack_packet, "snd")
                seq_num += 1
                # Wait for ACK before establising connection
                while(ack_received == False):
                    ack_packet, sender_address = receiver.receive_packet()
                    receiver.log(l, ack_packet, "rcv")
                    if ack_packet.ack == True:
                        ack_received = True
                        connected = True
        
        ########################################################################
        # Connected, commence receiving of data
        f = open(FileReceived, "a+")
        while(connected == True):
            # Receive packet
            packet, sender_address = receiver.receive_packet()
            receiver.log(l, packet, "rcv")
            # Discard duplicate packets
            if packet.sequence_num == last_received_seq_num:
                duplicate_packets_received += 1
                continue
            last_received_seq_num = packet.sequence_num
            # If FIN packet, start connection teardown
            if packet.fin == True:
                ack_num += 1
                ack_packet = receiver.create_ack_packet(seq_num, ack_num)
                receiver.send_packet(ack_packet, sender_address)
                receiver.log(l, ack_packet, "snd")
                teardown = True
                break
            
            # Process packet (get data)
            if packet.data != None:
                data_packets_received += 1
                # If packet received in correct order
                if packet.sequence_num == expected_seq_num:
                    f.write(packet.data)
                    data_received += len(packet.data)
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
                                ack_packet = receiver.create_ack_packet(seq_num, ack_num)
                                receiver.send_packet(ack_packet, sender_address)
                                receiver.log(l, ack_packet, "snd")
                                expected_seq_num = ack_num
                            # If packets still not all in order, send more duplicate
                            # ACKs with next expected sequence number
                            # NOTE: turn into function due to repeated code
                            else:
                                expected_seq_num += len(packet.data)
                                out_of_order = True
                                ack_packet = receiver.create_ack_packet(seq_num, expected_seq_num)
                                receiver.send_packet(ack_packet, sender_address)
                                receiver.log(l, ack_packet, "snd")
                    # Else if packets in order, just reply with ACK
                    else:
                        # Reply with ACK
                        ack_packet = receiver.create_ack_packet(seq_num, ack_num)
                        receiver.send_packet(ack_packet, sender_address)
                        receiver.log(l, ack_packet, "snd")
                        expected_seq_num = ack_num
                # Packet received out of order, send duplicate ACK
                else:
                    buffer.add_packet(packet)
                    ack_num += len(packet.data)
                    data_received += len(packet.data)
                    out_of_order = True
                    ack_packet = receiver.create_ack_packet(seq_num, expected_seq_num)
                    receiver.send_packet(ack_packet, sender_address)
                    receiver.log(l, ack_packet, "snd")


        f.close()

        # Connection teardown
        if teardown == True:
            seq_num += 1
            fin_packet = receiver.create_fin_packet(seq_num, ack_num)
            receiver.send_packet(fin_packet, sender_address)
            receiver.log(l, fin_packet, "snd")
            # Complete log with final statistics and close file
            l.write("--------------------------------------------------------\n")
            l.write("Total Data Received: " + str(data_received) + "\n" + "Data Segments Received: "
            + str(data_packets_received) + "\n" + "Duplicate Segments Received: " + str(duplicate_packets_received) + "\n")
            l.close()
            sys.exit()