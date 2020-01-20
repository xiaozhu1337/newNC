import argparse
import sys
import socket
import struct
import threading
import subprocess


class MySocket:
    def _recv_len(self, sock, length):
        data = b''
        while len(data) < length:
            more = sock.recv(length - len(data))
            if not more:
                break
            data += more
        return data

    def send_data_with_header(self, sock, data):
        sock.send(struct.pack('q', len(data)))
        sock.sendall(data.encode())

    def recv_data_with_header(self, sock):
        response_len = struct.unpack('q', sock.recv(8))[0]
        response = self._recv_len(sock, response_len).decode()
        return response


class ClientNC(MySocket):
    def __init__(self, args):
        self.target = args.target
        self.port = args.port
        self.upload_src = args.upload_src
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.target, self.port))

    def deal_upload(self):
        self.buffer = open(self.upload_src).read()
        self.send_data_with_header(self.client, self.buffer)
        data = self.recv_data_with_header(self.client)
        print(data)


    def deal_shell(self):
        try:
            print('<cat:#> ', end="")
            self.buffer = input()
            self.send_data_with_header(self.client, self.buffer)
            while True:
                response = self.recv_data_with_header(self.client)
                print(response)
                print('<cat:#> ', end="")
                self.buffer = input()

                self.send_data_with_header(self.client, self.buffer)
        except Exception as e:
            print(e)
            print('in interact_with_server')


class ServerNC(MySocket):
    def __init__(self, args):
        if not args.target:
            self.target = '0.0.0.0'
        else:
            self.target = args.target
        self.port = args.port
        self.upload = args.upload_dst
        self.command = args.commandshell

    def server_loop(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.target, self.port))
        self.server_socket.listen(5)

        while True:
            client_socket, _ = self.server_socket.accept()
            client_thread = threading.Thread(target=self.client_handler, args=(client_socket,))
            client_thread.start()

    def client_handler(self, client_socket):

        # check for upload
        if self.upload:
            self.deal_upload(client_socket)

        # command shell
        if self.command:
            self.deal_shell(client_socket)

    def deal_shell(self, client_socket):
        while True:
            # self.send_data_with_header(client_socket, '<cat:#> ')
            cmd = self.recv_data_with_header(client_socket)
            response = self._deal_execute(cmd)
            self.send_data_with_header(client_socket, response)

    def _deal_execute(self, cmd):
        try:
            cmd = cmd.rstrip()
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode()
        except:
            output = "Failed to execute comamnd.\r\n"
        return output

    def deal_upload(self, client_socket):
        try:
            data = self.recv_data_with_header(client_socket)
            with open(self.upload, 'wb') as f:
                f.write(data.encode())
                f.close()
            self.send_data_with_header(client_socket, "Successfully saved file to %s\r\n" % self.upload)
        except Exception as e:
            print(e)
            print('in deal_upload')

def usage():
    print('''
    usage:

    1 cmd shell
    python new_nc.py -l -t 127.0.0.1 -p 9999 -c
    python new_nc.py -t 127.0.0.1 -p 9999

    2 upload file
    python new_nc.py -l -t 127.0.0.1 -p 9999 --upload_dst=2.txt
    python new_nc.py -t 127.0.0.1 -p 9999 --upload_src=1.txt
    
    ''')
def main():
    if len(sys.argv) == 1:
        usage()
        sys.exit(1)

    parser = argparse.ArgumentParser(description="new NC")
    parser.add_argument('-l', '--listen', action='store_true')
    parser.add_argument('-c', '--commandshell', action='store_true')
    parser.add_argument('--upload_src')
    parser.add_argument('--upload_dst')
    parser.add_argument('-t', '--target')
    parser.add_argument('-p', '--port', type=int, required=True)
    args = parser.parse_args()

    if not args.listen and args.target and args.port:
        c = ClientNC(args)
        if args.upload_src:
            c.deal_upload()
        else:
            c.deal_shell()
    
    if args.listen:
        s = ServerNC(args)
        s.server_loop()

if __name__ == "__main__":
    main()