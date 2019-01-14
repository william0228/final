# -*- coding:utf8 -*-
import sys
import socket
from model import *
import json
import uuid
import time
import stomp
import boto3

conn_mq = stomp.Connection()
conn_mq.start()
conn_mq.connect('admin', 'password', wait=True)

ec2 = boto3.resource('ec2', region_name='us-east-2')

def Create_instance():
    instance = ec2.create_instances(
        ImageId = 'ami-0bb4c03e5d990c0ce',
        SecurityGroupIds=['launch-wizard-2'],
        MinCount = 1,
        MaxCount = 1,
        InstanceType = 't2.micro',
        KeyName='MyKeyPair.pem'
    )
    instance[0].wait_until_running()
    instance_collection = ec2.instances.filter(InstanceIds=[instance[0].instance_id])
    for i in instance_collection:
        return (i.public_ip_address, instance[0].instance_id)


class DBControl(object):
    def __auth(func):
        def validate_token(self, token=None, *args):
            if token:
                t = Token.get_or_none(Token.token == token)
                if t:
                    return func(self, t, *args)
            return {
                'status': 1,
                'message': 'Not login yet'
            }
        return validate_token

    def __auth2(func):
        def validate_token2(self, token=None, *args):
            if token:
                t = Token.get_or_none(Token.token == token)
                if t:
                    return func(self, t, *args)
            return {
                'status': 'Fail-A',
                'message': 'Not login yet'
            }
        return validate_token2

    def register(self, username=None, password=None, *args):
        if not username or not password or args:
            return {
                'status': 1,
                'message': 'Usage: register <username> <password>'
            }
        if User.get_or_none(User.username == username):
            return {
                'status': 1,
                'message': '{} is already used'.format(username)
            }
        res = User.create(username=username, password=password)
        if res:
            return {
                'status': 0,
                'message': 'Success!'
            }
        else:
            return {
                'status': 1,
                'message': 'Register failed due to unknown reason'
            }

    @__auth
    def delete(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: delete <user>'
            }

        res = Group.select().where(Group.member == token.owner)
        arr = []
        for i in res:
            arr.append(i.group_name)
        
        find_ip = Server_connect.get_or_none(Server_connect.user == token.owner)
        query_server = Server_connect.select(Server_connect.server_ip, Server_connect.instance_id).where(Server_connect.server_ip == find_ip.server_ip).having(fn.Count(Server_connect.user) < 2)
        if (len(query_server) > 0):
            ec2.instances.filter(InstanceIds=[query_server[0].instance_id]).terminate()
        
        token.owner.delete_instance()
        return {
            'status': 0,
            'message': 'Success!',
            'out_group': arr,
            'user': token.owner.username
        }

    def login(self, username=None, password=None, *args):
        if not username or not password or args:
            return {
                'status': 1,
                'message': 'Usage: login <id> <password>'
            }
        res = User.get_or_none((User.username == username) & (User.password == password))
        if res:
            t = Token.get_or_none(Token.owner == res)
            if not t:
                t = Token.create(token=str(uuid.uuid4()), owner=res)
            res1 = Group.select(Group.group_name).where(Group.member == t.owner)
            arr = []
            for i in res1:
                arr.append(i.group_name)
            
            res2 = Server_connect.get_or_none(Server_connect.user == t.owner)
            if res2:
                return {
                    'status': 0,
                    'token': t.token,
                    'message': 'Success!',
                    'login_group': arr,
                    'user': username,
                    'server': res2.server_ip
                }
                    
            instance_id = ""
            server_ip = ""

            query_server = Server_connect.select(Server_connect.server_ip, Server_connect.instance_id).group_by(Server_connect.server_ip).having(fn.Count(Server_connect.user) < 10)
            if (len(query_server) == 0):
                server_ip, instance_id = Create_instance()
            else:
                server_ip = query_server[0].server_ip
                instance_id = query_server[0].instance_id
                print(server_ip)
                print(instance_id)
                record = Server_connect.create(user = t.owner, server_ip = server_ip, instance_id = instance_id)
                if record:
                    return {
                        'status': 0,
                        'token': t.token,
                        'message': 'Success!',
                        'login_group': arr,
                        'user': username,
                        'server': res2.server_ip
                    }
                else:
                    return {
                        'status': 1,
                        'message': 'login assign server failed due to unknown reason'
                    }
            
            
        else:
            return {
                'status': 1,
                'message': 'No such user or password error'
            }

    @__auth
    def logout(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: logout <user>'
            }

        res = Group.select().where(Group.member == token.owner)
        arr = []
        for i in res:
            arr.append(i.group_name)
        
        find_ip = Server_connect.get_or_none(Server_connect.user == token.owner)
        query_server = Server_connect.select(Server_connect.server_ip, Server_connect.instance_id).where(Server_connect.server_ip == find_ip.server_ip).having(fn.Count(Server_connect.user) < 2)
        if (len(query_server) > 0):
            ec2.instances.filter(InstanceIds=[query_server[0].instance_id]).terminate()
        
        change = Server_connect.get(user=token.owner)
        change.delete_instance()
        
        token.delete_instance()
        return {
            'status': 0,
            'message': 'Bye!',
            'out_group': arr,
            'user': token.owner.username
        }

    @__auth
    def invite(self, token, username=None, *args):
        if not username or args:
            return {
                'status': 1,
                'message': 'Usage: invite <user> <id>'
            }
        if username == token.owner.username:
            return {
                'status': 1,
                'message': 'You cannot invite yourself'
            }
        friend = User.get_or_none(User.username == username)
        if friend:
            res1 = Friend.get_or_none((Friend.user == token.owner) & (Friend.friend == friend))
            res2 = Friend.get_or_none((Friend.friend == token.owner) & (Friend.user == friend))
            if res1 or res2:
                return {
                    'status': 1,
                    'message': '{} is already your friend'.format(username)
                }
            else:
                invite1 = Invitation.get_or_none((Invitation.inviter == token.owner) & (Invitation.invitee == friend))
                invite2 = Invitation.get_or_none((Invitation.inviter == friend) & (Invitation.invitee == token.owner))
                if invite1:
                    return {
                        'status': 1,
                        'message': 'Already invited'
                    }
                elif invite2:
                    return {
                        'status': 1,
                        'message': '{} has invited you'.format(username)
                    }
                else:
                    Invitation.create(inviter=token.owner, invitee=friend)
                    return {
                        'status': 0,
                        'message': 'Success!'
                    }
        else:
            return {
                'status': 1,
                'message': '{} does not exist'.format(username)
            }
        pass

    @__auth
    def list_invite(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-invite <user>'
            }
        res = Invitation.select().where(Invitation.invitee == token.owner)
        invite = []
        for r in res:
            invite.append(r.inviter.username)
        return {
            'status': 0,
            'invite': invite
        }

    @__auth
    def accept_invite(self, token, username=None, *args):
        if not username or args:
            return {
                'status': 1,
                'message': 'Usage: accept-invite <user> <id>'
            }
        inviter = User.get_or_none(User.username == username)
        invite = Invitation.get_or_none((Invitation.inviter == inviter) & (Invitation.invitee == token.owner))
        if invite:
            Friend.create(user=token.owner, friend=inviter)
            invite.delete_instance()
            return {
                'status': 0,
                'message': 'Success!'
            }
        else:
            return {
                'status': 1,
                'message': '{} did not invite you'.format(username)
            }
        pass

    @__auth
    def list_friend(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: list-friend <user>'
            }
        friends = Friend.select().where((Friend.user == token.owner) | (Friend.friend == token.owner))
        res = []
        for f in friends:
            if f.user == token.owner:
                res.append(f.friend.username)
            else:
                res.append(f.user.username)
        return {
            'status': 0,
            'friend': res
        }

    @__auth
    def post(self, token, *args):
        if len(args) <= 0:
            return {
                'status': 1,
                'message': 'Usage: post <user> <message>'
            }
        Post.create(user=token.owner, message=' '.join(args))
        return {
            'status': 0,
            'message': 'Success!'
        }

    @__auth
    def receive_post(self, token, *args):
        if args:
            return {
                'status': 1,
                'message': 'Usage: receive-post <user>'
            }
        res = Post.select().where(Post.user != token.owner).join(Friend, on=((Post.user == Friend.user) | (Post.user == Friend.friend))).where((Friend.user == token.owner) | (Friend.friend == token.owner))
        post = []
        for r in res:
            post.append({
                'id': r.user.username,
                'message': r.message
            })
        return {
            'status': 0,
            'post': post
        }

    @__auth2
    def send(self, token, username=None, *args):
        if not username or len(args) <= 0:
            return {
                'status': 'Fail-B',
                'message': 'Usage: send <user> <friend> <message>'
            }

        res = User.get_or_none(User.username == username)
        if not res:
            return {
                'status': 'Fail-C',
                'message': 'No such user exist'
            }

        res1 = Friend.get_or_none((Friend.user == token.owner) & (Friend.friend == res))
        res2 = Friend.get_or_none((Friend.friend == token.owner) & (Friend.user == res))
        if not (res1 or res2):
            return {
                'status': 'Fail-D',
                'message': '{} is not your friend'.format(username)
            }

        res3 = Token.get_or_none(Token.owner == res)
        if not res3:
            return {
                'status': 'Fail-E',
                'message': '{} is not online'.format(username)
            }

        message = "<<<" + str(token.owner.username) + "->" + str(username) + ": " +  str(' '.join(args)) + ">>>"
        conn_mq.send(body=message, destination="/queue/"+str(username))
        return {
            'status': 'Success',
            'message': 'Success!'
        }  

    @__auth2
    def create_group(self, token, group=None, *args):
        if not group or args:
            return {
                'status': 'Fail-B',
                'message': 'Usage: create-group <user> <group>'
            }

        res = Group.get_or_none(Group.group_name == group)
        if res:
            return {
                'status': 'Fail-C',
                'message': '{} already exist'.format(group)
            }

        res1 = Group.create(member = token.owner, group_name = group)
        return {
            'status': 'Success',
            'message': 'Success!',
            'user': token.owner.username
        }


    @__auth2
    def list_group(self, token, *args):
        if args:
            return {
                'status': 'Fail-B',
                'message': 'Usage: list-group <user>'
            }

        res = Group.select(Group.group_name).distinct()
        arr = []

        for i in res:
            arr.append(i.group_name)

        return {
            'status': 'Success',
            'group' : arr
        }

    @__auth2
    def list_joined(self, token, *args):
        if args:
            return {
                'status': 'Fail-B',
                'message': 'Usage: list-joined <user>'
            } 

        res = Group.select().where(Group.member == token.owner)
        arr = []

        for i in res:
            arr.append(i.group_name)

        return {
            'status': 'Success',
            'group' : arr
        }

    @__auth2
    def join_group(self, token, group=None, *args):
        if not group or args:
            return {
                'status': 'Fail-B',
                'message': 'Usage: join-group <user> <group>'
            }

        res = Group.get_or_none(Group.group_name == group)
        if not res:
            return {
                'status': 'Fail-C',
                'message': '{} does not exist'.format(group)             
            }

        res1 = Group.get_or_none((Group.group_name == group) & (Group.member == token.owner))
        if res1:
            return {
                'status': 'Fail-D',
                'message': 'Already a member of {}'.format(group)                    
            }

        res2 = Group.create(member = token.owner, group_name = group)
        return {
            'status': 'Success',
            'message': 'Success!',
            'user': token.owner.username
        }

    @__auth2
    def send_group(self, token, group=None, *args):
        if not group or len(args) <= 0:
            return {
                'status': 'Fail-B',
                'message': 'Usage: send-group <user> <group> <message>'
            }

        res = Group.get_or_none(Group.group_name == group)
        if not res:
            return {
                'status': 'Fail-C',
                'message': 'No such group exist'
            }

        res1 = Group.get_or_none((Group.group_name == group) & (Group.member == token.owner))
        if not res1:
            return {
                'status': 'Fail-D',
                'message': 'You are not the member of {}'.format(group)
            }

        message = "<<<" + str(token.owner.username) + "->" + "GROUP<" + str(group) + ">: " +  str(' '.join(args)) + ">>>"
        conn_mq.send(body=message, destination="/topic/"+str(group))
        
        return {
            'status': 'Success',
            'message': 'Success!'      
        }

class Server(object):
    def __init__(self, ip, port):
        try:
            socket.inet_aton(ip)
            if 0 < int(port) < 65535:
                self.ip = ip
                self.port = int(port)
            else:
                raise Exception('Port value should between 1~65535')
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.db = DBControl()
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

    def run(self):
        self.sock.bind((self.ip, self.port))
        self.sock.listen(100)
        # socket.setdefaulttimeout(0.1)
        while True:
            try:
                conn, addr = self.sock.accept()
                with conn:
                    cmd = conn.recv(4096).decode()
                    resp = self.__process_command(cmd)
                    conn.send(resp.encode())
            except Exception as e:
                print(e, file=sys.stderr)

    def __process_command(self, cmd):
        command = cmd.split()
        if len(command) > 0:
            command_exec = getattr(self.db, command[0].replace('-', '_'), None)
            if command_exec:
                return json.dumps(command_exec(*command[1:]))
        return self.__command_not_found(command[0])

    def __command_not_found(self, cmd):
        return json.dumps({
            'status': 1,
            'message': 'Unknown command {}'.format(cmd)
        })


def launch_server(ip, port):
    c = Server(ip, port)
    c.run()

if __name__ == '__main__':
    if sys.argv[1] and sys.argv[2]:
        launch_server(sys.argv[1], sys.argv[2])
