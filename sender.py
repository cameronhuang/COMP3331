#!/usr/bin/python3

# COMP3331 21T2 Assignment 
# Padawan Transport Protocol
# Sender
# Implemented in python3
# By Cameron Huang
# z5251618

from os import sync
import sys
import pickle
import time
import random
import threading
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
        self.pdrop = float(pdrop)
        self.seed = int(seed)

    socket = socket(AF_INET, SOCK_DGRAM)
    time_last_pkt_sent = 0
    

    def receive_packet(self):
        data, client_address = self.socket.recvfrom(2048)
        packet = pickle.loads(data)
        return packet, client_address

    def create_syn_packet(self, sequence_num, ack_num):
        syn_packet = Packet(sequence_num, ack_num, None, None, syn=True, ack=False, fin=False)
        return syn_packet

    def create_data_packet(self, sequence_num, ack_num, data):
        data_packet = Packet(sequence_num, ack_num, data, None, syn=False, ack=False, fin=False)
        return data_packet

    def create_ack_packet(self, sequence_num, ack_num):
        ack_packet = Packet(sequence_num, ack_num, None, None, syn=False, ack=True, fin=False)
        return ack_packet

    def create_fin_packet(self, sequence_num, ack_num):
        fin_packet = Packet(sequence_num, ack_num, None, None, syn=False, ack=False, fin=True)
        return fin_packet

    def send_packet(self, packet):
        self.socket.sendto(pickle.dumps(packet), (self.receiver_host_ip, self.receiver_port))
        self.time_last_pkt_sent = time.time()

    def retransmit(self, buffer, seq_num):
        for packet in buffer.packets:
            if packet.sequence_num == seq_num:
                packet.time_sent = time.time()
                self.send_packet(packet)
                self.log(f, packet, "snd")

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
    def split_payload(self, data):
        global index
        data_length = len(data)
        end_segment = index + self.MSS
        if (end_segment > data_length):
            payload = data[index:data_length]
        else:
            payload = data[index:end_segment]
        index += self.MSS
        return payload

    def check_timeout(self, buffer):
        global retransmitted_packets
        if (buffer.size() > 0):
            # Retransmit due to timeout
            curr_time = time.time()
            time_since_sent = (curr_time - buffer.packets[0].time_sent) * 1000
            if time_since_sent > self.timeout:
                sender.retransmit(buffer, last_ack_num)
                retransmitted_packets += 1

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
    def __init__(self, sequence_num, ack_num, data, time_sent, syn=False, ack=False, fin=False):
        self.sequence_num = sequence_num
        self.ack_num = ack_num
        self.data = data
        self.time_sent = time_sent
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


def send_handler():
    global t_lock
    global connected
    global syn_sent
    global synack_received
    global seq_num
    global ack_num
    global index
    global sender
    global data
    global buffer
    global expected_ack_num
    global last_byte_sent
    global last_byte_acked
    global f
    global data_packets_sent
    global packets_dropped

    while(1):
        with t_lock:
            sender.check_timeout(buffer)
            ############################################################################
            # No connection yet with receiver, so we'll commence 3 way handshake
            if connected == False and syn_sent == False:
                syn_packet = Packet(seq_num, ack_num, None, time.time(), syn=True, ack=False, fin=False)
                sender.send_packet(syn_packet)
                sender.log(f, syn_packet, "snd")
                syn_sent = True
                seq_num += 1
                # Wait for SYNACK from receiver
            ############################################################################
            # Connected, commence transmission of data
            if connected == True:
                # If file completely sent, teardown connection
                if index >= len(data):
                    if buffer.size() > 0:
                        continue
                    teardown = True
                    seq_num += 1
                    fin_packet = sender.create_fin_packet(seq_num, ack_num)
                    sender.send_packet(fin_packet)
                    sender.log(f, fin_packet, "snd")
                    connected = False
                    sys.exit()

                # Sliding Window Protocol
                last_byte_sent = expected_ack_num
                last_byte_acked = last_ack_num
                if last_byte_sent - last_byte_acked <= MWS:
                    # Send packet 
                    packet_data = sender.split_payload(data)
                    packet = Packet(seq_num, ack_num, packet_data, None, syn=False, ack=False, fin=False)
                    # Add packet to buffer
                    buffer.add_packet(packet)

                    expected_ack_num = seq_num + len(packet_data)
                    seq_num += len(packet_data)

                    # Pass through module that emulates packet drop
                    # need to move/change last packet sent time variable
                    # to account for timeout of dropped packets
                    packet.time_sent = time.time()
                    if sender.PLD() == True:
                        sender.log(f, packet, "drop")
                        packets_dropped += 1
                    else:
                        sender.send_packet(packet)
                        sender.log(f, packet, "snd")
                        data_packets_sent += 1
            #notify the thread waiting
            t_lock.notify()
        #sleep for UPDATE_INTERVAL
        time.sleep(UPDATE_INTERVAL)

def recv_handler():
    global t_lock
    global connected
    global seq_num
    global ack_num
    global sender
    global awake
    global buffer
    global data
    global last_ack_num
    global curr_duplicate_acks
    global expected_ack_num
    global f
    global packets_dropped
    global retransmitted_packets
    global total_duplicate_acks

    while(1):
        packet, client_address = sender.receive_packet()
        sender.log(f, packet, "rcv")
        with t_lock:
            if packet.syn == True and packet.ack == True:
                # Check if correct ACK num, then reply with ACK
                if packet.ack_num == seq_num:
                    ack_num += 1
                    ack_packet = Packet(seq_num, ack_num, None, time.time(), syn=False, ack=True, fin=False)
                    sender.send_packet(ack_packet)
                    sender.log(f, ack_packet, "snd")
                    connected = True
            if packet.ack == True:
                # Check if ACK acknowledges last sent packet seq_num
                # Continue sending as per usual if ack_num is as expected
                if packet.ack_num == expected_ack_num:
                    # Remove ACKed packet from buffer
                    for p in buffer.packets:
                        temp = []
                        if (p.sequence_num + len(p.data)) > expected_ack_num:
                            temp.append(p)
                        buffer.packets = temp

                # Duplicate ACK received, count duplicates and retransmit if
                # 3 received
                elif packet.ack_num == last_ack_num:
                    curr_duplicate_acks += 1
                    total_duplicate_acks += 1
                    if curr_duplicate_acks == 3:
                        sender.retransmit(buffer, last_ack_num)
                        retransmitted_packets += 1
                        curr_duplicate_acks = 0
                    
                last_ack_num = packet.ack_num

            # FIN received from receiver, complete teardown and exit
            if packet.fin == True:
                ack_num += 1
                ack_packet = Packet(seq_num, ack_num, None, time.time(), syn=False, ack=True, fin=False)
                sender.send_packet(ack_packet)
                sender.log(f, ack_packet, "snd")
                connected = False

                # Complete log with final statistics and close file
                f.write("--------------------------------------------------------\n")
                f.write("Total Data Transferred: " + str(len(data)) + "\n" + "Data Segments Sent: " 
                + str(data_packets_sent) + "\n" + "Packets Dropped: " + str(packets_dropped) + 
                "\n" "Retransmitted Segments: " + str(retransmitted_packets)
                + "\n" + "Duplicate ACKs Received: " + str(total_duplicate_acks) + "\n")
                f.close()
                awake = False

            t_lock.notify()

################################################################################
################################################################################
# Main program
# Error checking
if len(sys.argv) != 9:
    print("Usage: python3 sender.py <receiver_host_ip> <receiver_port> <FileToSend> <MWS> <MSS> <timeout> <pdrop> <seed>")
    sys.exit()
else:
    # On state
    awake = True
    start_time = time.time()
    
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
    teardown = False
    syn_sent = False
    synack_received = False

    # Packet sequence and ACK numbers
    seq_num = 0
    ack_num = 0
    expected_ack_num = 0
    last_ack_num = 0
    curr_duplicate_acks = 0
    data_packets_sent = 0
    packets_dropped = 0
    retransmitted_packets = 0
    total_duplicate_acks = 0
    # Set seed
    random.seed(seed)

    # Create buffer that holds packets which are waiting to be ACKed
    buffer = Packet_Buffer()

    # Used to calculate MWS
    last_byte_sent = 0
    last_byte_acked = 0
    
    # Create sender object
    sender = Sender(receiver_host_ip, receiver_port, FileToSend, MWS, MSS, timeout, pdrop, seed)

    # Grab data from file
    f = open(FileToSend, "r")
    data = f.read() 
    f.close()

    # Create log file
    f = open("Sender_log.txt", "a+")
    string = '{:<8s}{:<12s}{:<8s}{:<10s}{:<10s}{:<10s}'.format("ACTION", "TIME",
            "FLAGS", "SEQ", "DATA", "ACK")
    f.write(string + "\n")
    f.write("--------------------------------------------------------\n")

    # File index
    index = 0

    # Threading ting
    t_lock = threading.Condition()
    UPDATE_INTERVAL = 1

    recv_thread=threading.Thread(name="RecvHandler", target=recv_handler)
    recv_thread.daemon=True
    recv_thread.start()

    send_thread=threading.Thread(name="SendHandler",target=send_handler)
    send_thread.daemon=True
    send_thread.start()

# Main loop
while awake is True:
    time.sleep(0.1)
    