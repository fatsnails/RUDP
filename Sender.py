import sys
import getopt
import base64

import Checksum
import BasicSender
import time

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        self.buff = []
        self.sack = False
        self.res = ""
        self.time_start = []
        self.end = False
        self.offset = 0
        if sackMode:
            self.sack = True

    def handle_response(self,response_packet):
        if Checksum.validate_checksum(response_packet):
            print("recv: %s" % response_packet)
        else:
            print("recv: %s <--- CHECKSUM FAILED" % response_packet)

    # Main sending loop.
    def start(self):
        self.seqno = 0
        self.msg = None
        self.msg_type = ""
        self.window_f = 0 #??????????????????????????????/??????
        self.window_a = 5 #?????????????????????????????????????????????????
        #self.buff = []#?????????????????????????????????????
        self.next_msg = self.infile.read(500)
        self.next_msg = base64.b64encode(self.next_msg).decode()
        while self.offset < self.window_a and not self.msg_type == 'end':
            self.msg = self.next_msg
            self.next_msg = self.infile.read(500)
            self.next_msg = base64.b64encode(self.next_msg).decode()            
            if self.seqno == 0:
                self.msg_type = 'start'
            elif (self.next_msg == '' or self.msg == ""):
                self.msg_type = "end"
            else:
                self.msg_type = 'data'
            packet = self.make_packet(self.msg_type,self.seqno,self.msg)
            self.send("{}".format(packet))
            time_start = time.time()
            self.time_start.append(time_start)
            print("sent: %s" % packet[:20])
            self.buff.append(packet)#to save the sent item in the buffer
            self.seqno += 1
            self.offset+=1
        while not self.end:
            response = self.receive(0.5)#500毫秒超时    
            if response is not None:      
                response = response.decode()
                self.handle_response(response)         
                res = self.split_packet(response)
                self.res = res[1];#??????????????????????????????
                if int(res[1].split(';')[0]) > self.window_f:
                    self.handle_new_ack(int(res[1].split(';')[0]))
                else:
                    self.handle_dup_ack(int(res[1].split(';')[0]))
            else:
                self.handle_timeout()


    def handle_timeout(self):
        if self.sack == False:
            for j in range(self.window_f,min(self.window_a,len(self.buff))):
                packet = self.buff[j]
                self.send("{}".format(packet))   
                time_start = time.time()
                self.time_start[j] = time_start
                print("sent: %s" % packet[:20])
        else:
            time_end = time.time()
            already = self.res[2:].split(',')
            for j in range(self.window_f,min(self.window_a,len(self.buff))):
                if str(j) not in already and time_end - self.time_start[j]>=0.5:
                    packet = self.buff[j]
                    self.send("{}".format(packet))
                    time_start = time.time()
                    self.time_start[j] = time_start
                    print("sent: %s" % packet[:20])           


    def handle_new_ack(self, ack):
        self.window_f = ack
        self.window_a = self.window_f + 5
        res = self.split_packet(self.buff[ack - 1])
        if res[0] == "end":
            self.end = True
            return
        while self.offset < self.window_a and not self.msg_type == 'end':
            self.msg = self.next_msg
            self.next_msg = self.infile.read(500)
            self.next_msg = base64.b64encode(self.next_msg).decode()
            if self.seqno == 0:
                self.msg_type = 'start'
            elif (self.next_msg == '' or self.msg == ""):
                self.msg_type = "end"
            else:
                self.msg_type = 'data'
            packet = self.make_packet(self.msg_type,self.seqno,self.msg)
            self.send("{}".format(packet))
            time_start = time.time()
            self.time_start.append(time_start)
            print("sent: %s" % packet[:20])
            self.buff.append(packet)#to save the sent item in the buffer
            self.seqno += 1
            self.offset+=1

    def handle_dup_ack(self, ack):
        time_end = time.time()
        res = self.split_packet(self.buff[ack - 1])
        if time_end - self.time_start[ack] >= 0.5 and res[0]!="end":
            self.handle_timeout() 
        elif res[0] == "end":
            self.end = True           

    def log(self, msg):
        if self.debug:
            print(msg)


'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print("RUDP Sender")
        print("-f FILE | --file=FILE The file to transfer; if empty reads from STDIN")
        print("-p PORT | --port=PORT The destination port, defaults to 33122")
        print("-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost")
        print("-d | --debug Print debug messages")
        print("-h | --help Print this usage message")
        print("-k | --sack Enable selective acknowledgement mode")

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
