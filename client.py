# -*- coding:utf8 -*-
import sys
import socket
import json
import os
import stomp

class MyListener(stomp.ConnectionListener):
    def on_error(self, headers, message):
        print('received an error "%s"' % message)
    def on_message(self, headers, message):
        print(message)


class Client(object):
    def __init__(self, ip, port):
        try:
            socket.inet_aton(ip)
            if 0 < int(port) < 65535:
                self.ip = ip
                self.port = int(port)
            else:
                raise Exception('Port value should between 1~65535')
            self.cookie = {}
            self.server = {}
            self.conn = stomp.Connection([('18.221.0.251', 61613)])
            self.conn.set_listener('', MyListener())
            self.conn.start()
            self.conn.connect('admin', 'password', wait=True)

        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def run(self):
        while True:
            cmd = sys.stdin.readline()
            cmd = str(cmd)
            if cmd == 'exit' + os.linesep:
                return
            if cmd != os.linesep:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        
                        command = cmd.split()
                        # which server we need to go to
                        # with command register/login/logout/delete in login_server
                        if len(command) > 2:
                            if((command[0] == "register") or (command[0] == "login") or (command[0] == "logout") or (command[0] == "delete") or (self.cookie[command[1]] == "")):
                                s.connect((self.ip, self.port))
                            # with other command in app_server
                            else :
                                s.connect((self.ip, 8000))
                        else:
                            s.connect((self.ip, self.port))
                        
                        cmd = self.__attach_token(cmd)
                        s.send(cmd.encode())
                        resp = s.recv(4096).decode()
                        self.__show_result(json.loads(resp), cmd)
                except Exception as e:
                    print(e, file=sys.stderr)

    def __show_result(self, resp, cmd=None):
        if 'message' in resp:
            print(resp['message'])

        if 'invite' in resp:
            if len(resp['invite']) > 0:
                for l in resp['invite']:
                    print(l)
            else:
                print('No invitations')

        if 'friend' in resp:
            if len(resp['friend']) > 0:
                for l in resp['friend']:
                    print(l)
            else:
                print('No friends')

        if 'post' in resp:
            if len(resp['post']) > 0:
                for p in resp['post']:
                    print('{}: {}'.format(p['id'], p['message']))
            else:
                print('No posts')

        if 'group' in resp:
            if len(resp['group']) > 0:
                for l in resp['group']:
                    print(l)
            else:
                print('No groups')

        if cmd:
            command = cmd.split()
            if resp['status'] == 0 and command[0] == 'login':
                self.cookie[command[1]] = resp['token']
                self.conn.subscribe(destination="/queue/"+command[1], id=resp['token'], ack="auto")
                if len(resp['login_group']) > 0:
                    for i in resp['login_group']:
                        self.conn.subscribe(destination="/topic/"+i, id=resp['token']+i, ack="auto")

                if command[1] in self.server:
                    if resp['server'] != self.server[command[1]]:
                        self.server[command[1]] = resp['server']
                    else:
                        self.server[command[1]] = resp['server']

            elif resp['status'] == 0 and (command[0] == 'delete' or command[0] == 'logout'):
                self.conn.unsubscribe(destination="/queue/"+str(resp['user']), id=command[1])
                for i in resp['out_group']:
                    # print("out" + " " + command[1] + " " + i)
                    self.conn.unsubscribe(destination="/topic/"+i, id=command[1]+i)

            elif resp['status'] == 'Success' and (command[0] == 'create-group' or command[0] == 'join-group'):
                # print("group" + " " + command[1] + " " + command[2])
                self.conn.subscribe(destination="/topic/"+command[2], id=command[1]+command[2], ack="auto")


    def __attach_token(self, cmd=None):
        if cmd:
            command = cmd.split()
            if len(command) > 1:
                if command[0] != 'register' and command[0] != 'login':
                    if command[1] in self.cookie:
                        command[1] = self.cookie[command[1]]
                    else:
                        command.pop(1)
            return ' '.join(command)
        else:
            return cmd


def launch_client(ip, port):
    c = Client(ip, port)
    c.run()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        launch_client(sys.argv[1], sys.argv[2])
    else:
        print('Usage: python3 {} IP PORT'.format(sys.argv[0]))
