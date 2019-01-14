from peewee import *


db = MySQLDatabase('wangsy', user='wangsy', password='13470303',host='wangsy.cd4ysiffzsz0.us-east-2.rds.amazonaws.com', port=3306)

class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()


class Invitation(BaseModel):
    inviter = ForeignKeyField(User, on_delete='CASCADE')
    invitee = ForeignKeyField(User, on_delete='CASCADE')


class Friend(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE')
    friend = ForeignKeyField(User, on_delete='CASCADE')


class Post(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE')
    message = CharField()


class Follow(BaseModel):
    follower = ForeignKeyField(User, on_delete='CASCADE')
    followee = ForeignKeyField(User, on_delete='CASCADE')


class Token(BaseModel):
    token = CharField(unique=True)
    owner = ForeignKeyField(User, on_delete='CASCADE')

class Group(BaseModel):
    group_name = CharField(unique=False)
    member = ForeignKeyField(User, on_delete='CASCADE')

class Server(BaseModel):
    user = ForeignKeyField(User, on_delete='CASCADE')
    server_ip = CharField(unique=False)
    instance_id = CharField(unique=False)

if __name__ == '__main__':
    db.connect()
    db.create_tables([User, Invitation, Friend, Post, Follow, Token, Group, Server])
