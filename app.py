from flask import Flask, request, jsonify, session, make_response
from flask_restful import  Api
from flask_sqlalchemy import SQLAlchemy
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from validate_email import validate_email
from sqlalchemy import String, ForeignKey, Table, Column, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from typing import List
import json
from datetime import datetime
import random

app = Flask(__name__)
api = Api(app)
engine = create_engine("sqlite:///database.db", echo=True)


class Base(DeclarativeBase):
    pass

participators_lists = Table(
    "participator_lists",
    Base.metadata,
    Column("user", ForeignKey("user.id"), primary_key=True),
    Column("lists", ForeignKey("lists.id"), primary_key=True),
)

#TODO: запихать базы данных в отдельный файл
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    participates: Mapped[List["Lists"]] = relationship(
        secondary=participators_lists,
        back_populates="participators",
    )

    def __repr__(self) -> str:
        return f"User(username = {self.username}, password = {self.password}, email = {self.email}, participates = {self.participates})"

class Lists(Base):
    __tablename__ = "lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    creator: Mapped[int] = mapped_column(ForeignKey('user.id'))
    event_invite_code: Mapped[str] = mapped_column(String(20), unique=True)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    event_description: Mapped[str] = mapped_column(String(1000))
    max_number_of_people: Mapped[int] = mapped_column(nullable=False)
    cur_number_of_people: Mapped[int] = mapped_column(nullable=False)
    current_wishlist: Mapped[List["Wishlist"]] = relationship(cascade="all, delete")
    date: Mapped[datetime] = mapped_column(nullable=False)
    participators: Mapped[List["User"]] = relationship(
        secondary=participators_lists,
        back_populates="participates",
    )
    

    def __repr__(self) -> str:
        return f"Lists(event_id = {self.event_id},\n\
                       creator = {self.creator}, \n\
                       event_name = {self.event_name},\n\
                       event_description = {self.event_description},\n\
                       event_invite_code = {self.event_invite_code},\n\
                       max_number_of_people = {self.max_number_of_people},\n\
                       cur_number_of_people = {self.cur_number_of_people},\n\
                       current_wishlist = {self.current_wishlist},\n\
                       participators = {self.participators})"

class Wishlist(Base):
    __tablename__ = "wishlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("lists.event_id"), nullable=True)
    wish: Mapped[str] 
    user_who_buy: Mapped[int] = mapped_column(nullable=True)


    def __repr__(self) -> str:
        return f"Wishlist(id = {self.id}, wish = {self.wish})"


class Sessions(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    cookie_session: Mapped[str] = mapped_column(String(200), unique=True)
    server_session: Mapped[str] = mapped_column(String(200), unique=True)
    # due_to = db.Column(db.Date())

    def __repr__(self) -> str:
        return f"User(user = {self.user_id}, \n\
                      cookie_session = {self.cookie_session}, \n\
                      server_session = {self.server_session}, \n\
                      due_to = {self.due_to})"

Base.metadata.create_all(engine)

# @app.after_request()
# def check_and_change_cookie(response):
    


#     # TODO:
#     # получить от user session_id
#     # сравнить её с той, что храниться на сервере
#     # Если не она, то чистим и редиректим на /login
#     # Если она, то генерим новую
#     # Даём серверу новую куку
#     # Возвращаем юзеру новую куку

#     return {'username': 'AMOGUS'}

@app.route('/my/lists/show', methods=['GET', 'POST'])
def show_list():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()
    user_id = find_user(cookie_session)
    if user_id == None:
        return jsonify({'message': 'No such user'}), 400
    
    with Session(engine) as session:
        list = session.query(Lists).filter(Lists.event_id == data["event_id"]).first()
        user = session.query(User).filter(User.id == user_id).first()

        if user not in list.participators:
            return jsonify({'message': 'Unauthorized'}), 403
        
        participators_lists = [member.username for member in list.participators]
        your_presents = []
        for wish in list.current_wishlist:
            if wish.user_who_buy == user.id:
                your_presents.append(wish.wish)
        # print("-------------------------------------------------------")
        # print(wishes)
        # print("-------------------------------------------------------")
        if (user_id == list.creator) and (list.event_name != 'Secret Santa'):
            wishes = []
            for wish in list.current_wishlist:
                wishes.append(wish.wish)
            event_info = {
                'event_id': list.event_id,
                'event_invite_code': list.event_invite_code,
                'event_name': list.event_name,  # проверить на отсутствие значения
                'event_description': list.event_description,
                'max_number_of_people': list.max_number_of_people,  # проверить на отсутствие значения
                'cur_number_of_people': 1, #y <= x
                'current_wishlist':  wishes,
                # 'current_wishlist':  [wish.wish for wish in list.current_wishlist],
                'date': str(list.date)[:-9],
                'partisipators': participators_lists,
                # 'your_presents': next((wish.wish for wish in list.current_wishlist if wish.user_who_buy == username), None)
            }
        else:
            wishes = []
            for wish in list.current_wishlist:
                tmp = {
                    'wish': wish.wish,
                    'taken':  '0' if wish.user_who_buy == None else '1'
                }
                wishes.append(tmp)
            event_info = {
                'event_id': list.event_id,
                'event_invite_code': list.event_invite_code,
                'event_name': list.event_name,  # проверить на отсутствие значения
                'event_description': list.event_description,
                'max_number_of_people': list.max_number_of_people,  # проверить на отсутствие значения
                'cur_number_of_people': 1, #y <= x
                'current_wishlist':  wishes,
                # 'current_wishlist':  [wish.wish for wish in list.current_wishlist],
                'date': str(list.date)[:-9],
                'partisipators': participators_lists,
                'your_presents': your_presents
                # 'your_presents': next((wish.wish for wish in list.current_wishlist if wish.user_who_buy == username), None)
            }
        



        events = json.dumps(event_info, indent=6)

        # return jsonify(events), 200 
        return events


@app.route('/my/lists', methods=['GET', 'POST'])
def dashboard():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()

    with Session(engine) as session:
        user_id = find_user(cookie_session)
        if user_id == None:
            return jsonify({'message': 'No such user'}), 400

        user = session.query(User).filter(User.id == user_id).first()

        items = []
        for data in user.participates:
            print("------------------------------")
            for wish in data.current_wishlist:
                print(wish.wish)
            print("------------------------------")
            new_list_json = {
                'event_id': data.event_id,
                'event_invite_code': data.event_invite_code,
                'event_name': data.event_name,  # проверить на отсутствие значения
                'event_description': data.event_description,
                'max_number_of_people': data.max_number_of_people,  # проверить на отсутствие значения
                'cur_number_of_people': 1, #y <= x
                'current_wishlist': [wish.wish for wish in data.current_wishlist],
                'date': str(data.date),
            }
            items.append(new_list_json)
            print(new_list_json)

    events = {
        'username': user.username,
        'events': items
    }
    events = json.dumps(events, indent=4)

    return events

@app.route('/my/list/create', methods=['POST']) # принимает куки и введённую форму data[]
def create_list():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()
    with Session(engine) as session:
        while (True):
            event_id = secrets.token_hex(20)
            if session.query(Lists).filter(Lists.event_id == event_id).first() == None:
                break

        while (True):
            event_invite_code = str(secrets.token_hex(3)) + "-" + str(secrets.token_hex(3))
            if session.query(Lists).filter(Lists.event_invite_code == event_invite_code).first() == None:
                break

        user_id = find_user(cookie_session)
        if user_id == None:
            return jsonify({'message': 'No such user'}), 400

    try:
        new_list_json = {
            'event_id': event_id,
            'creator': user_id, # проверить на отсутствие значения
            'event_invite_code': event_invite_code,
            'event_name': data['event_name'],  # проверить на отсутствие значения
            'event_description': data['event_description'],
            'max_number_of_people': data['max_number_of_people'],  # проверить на отсутствие значения
            'cur_number_of_people': 1, #y <= x
            'current_wishlist': '',
            'participators': user_id,
            'date': datetime.strptime(data["date"], '%d-%m-%Y').date(),
            # 'date': datetime.strptime(data["date"], '%m-%d-%y').date(),
        }
    except:
        return jsonify({'message': 'Unable to upload list new_list_json'}), 400

    print(new_list_json)

    with Session(engine) as session:
        try:     
            new_list = Lists()
            new_list.event_id = new_list_json["event_id"]
            new_list.creator=new_list_json["creator"]
            new_list.event_invite_code=new_list_json["event_invite_code"]
            new_list.event_name=new_list_json["event_name"]
            new_list.event_description=new_list_json["event_description"]
            new_list.max_number_of_people=new_list_json["max_number_of_people"]
            new_list.cur_number_of_people=new_list_json["cur_number_of_people"]
            # new_list.current_wishlist=new_list_json["current_wishlist"]
            new_list.date=new_list_json["date"]
            new_list.participators.append(session.query(User).filter(User.id == user_id).first())
            session.add(new_list)
            session.commit()
        except:
            return jsonify({'message': 'Unable to upload list'}), 400

    return jsonify({'message': 'List created successfully'}), 201


@app.route('/my/list/join', methods=['PUT'])
def join_list():
    user_session = request.cookies["cookie_session"] # что-то сделать отсюда)
    data = request.get_json()

    user_id = find_user(user_session)
    if user_id == None:
        return jsonify({'error': "unauthorized"}), 403

    with Session(engine) as session:
        event = session.query(Lists).filter(Lists.event_invite_code == data['event_invite_code']).first()
        if not event:
            return jsonify({'error': "No such event"}), 400

        if user_id in [user.id for user in event.participators]:
            return jsonify({'message': 'Already in this room'}), 400

        event.cur_number_of_people += 1
        if event.cur_number_of_people > event.max_number_of_people:
            return jsonify({'message': "No more participants allowed"}), 203
        
        event.participators.append(session.query(User).filter(User.id == user_id).first())    
        session.commit()

    return jsonify({'message': "Successful join"}), 200

@app.route('/my/list/leave', methods=['PUT']) #принимает id комнаты
def leave_list():
    user_session = request.cookies["cookie_session"] # что-то сделать отсюда)
    data = request.get_json()

    #TODO: запретить создателю комнаты ливать из неё
    user_id = find_user(user_session)
    if user_id == None:
        return jsonify({'error': "unauthorized"}), 403


    with Session(engine) as session:
        event = session.query(Lists).filter(Lists.event_id == data['event_id']).first()
        if not event:
            return jsonify({'error': "No such event"}), 400
        
        if user_id not in event.participators:
            return jsonify({'message': 'Unauthorized'}), 403
        
        event.participators.remove(session.query(User).filter(User.id == user_id).first())    
        session.commit()

    return jsonify({'message': "Successful leave"}), 200

@app.route('/my/list/delete', methods=['DELETE']) # принимает event_id и cur_number_of_people
def delete_list():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    user_id = find_user(user_session)

    with Session(engine) as session:
        list_to_del = session.query(Lists).filter(Lists.event_id == data["event_id"]).first()
        if list_to_del == None:
            return jsonify({'message': 'There is no such event'}), 400

        if not list_to_del.creator == user_id:
            return jsonify({'message': 'You are not owner of this'}), 400

        try:
            session.delete(list_to_del)
            session.commit()
        except:
            return jsonify({'message': 'Unable to delete list'}), 400

    return jsonify({'message': 'List deleted successfully'}), 200

@app.route('/my/list/edit', methods=['PUT'])
def edit_list():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    user_id = find_user(user_session)

    with Session(engine) as session:
        list_to_update = session.query(Lists).filter(Lists.event_id == data["event_id"]).first()
        if list_to_update == None:
            return jsonify({'message': 'There is no such event'}), 400

        if not list_to_update.creator == user_id:
            return jsonify({'message': 'You are not owner of this'}), 400
        
        try:
            list_to_update.event_name = data["event_name"]
            list_to_update.event_description = data["event_description"]
            list_to_update.max_number_of_people = data["max_number_of_people"]
            list_to_update.current_wishlist = []
            session.flush()
            for wish in data["current_wishlist"]:
                new_wish = Wishlist(wish=wish)
                list_to_update.current_wishlist.append(new_wish)
                # print("-------------------------------------------------------")
                # print(list_to_update.current_wishlist)  
                # print("-------------------------------------------------------")
        except:
            return jsonify({"message": "/my/list/edit missing data"}), 500
        
        try:
            session.commit()    
        except:
            return jsonify({"message": "Something wrong with editing"}), 500

    return jsonify({"message": "Update succesfull"}), 201


@app.route('/secret/santa', methods=['PUT'] ) #принимает event_id
def secret_santa():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    user_id = find_user(user_session)
    if user_id == None:
        return jsonify({'message': 'No such user'}), 403


    with Session(engine) as session:
        santa_list = session.query(Lists).filter(Lists.event_id == data["event_id"]).first()
        if santa_list == None:
            return jsonify({'message': 'There is no such event'}), 400

        if not santa_list.creator == user_id:
            return jsonify({'message': 'You are not owner of this'}), 400
        
        if len(santa_list.current_wishlist) != len(santa_list.participators):
            return jsonify({'message': 'Not enougth people or presents'}), 400

        participators_lists = [member.id for member in santa_list.participators]
        
        print("---------------------------------------------------------------")
        print(len(santa_list.current_wishlist))
        print(len(santa_list.participators))
        print("---------------------------------------------------------------")

        random.shuffle(participators_lists)
        for wish, user in zip(santa_list.current_wishlist, participators_lists):
            print("---------------------------------------------------------------")
            print(wish)
            print(user)
            print("---------------------------------------------------------------")
            wish.user_who_buy = user
        session.commit()
    return jsonify({'message': 'Succesfull shuffle, reload page to see difference'}), 200

@app.route('/take/present', methods=['PUT'] ) #принимает event_id и то что выбрал юзер(wishes)
def take_present():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    user_id = find_user(user_session)

    with Session(engine) as session:
        take_present_list = session.query(Lists).filter(Lists.event_id == data["event_id"]).first()
        user = session.query(User).filter(User.id == user_id).first()
        if take_present_list == None:
            return jsonify({'message': 'There is no such event'}), 400
        # print("-------------------------------------------------------")
        # print(take_present_list.participators)
        # print("-------------------------------------------------------")
        if user not in take_present_list.participators:
            return jsonify({'message': 'Unauthorized'}), 403
        

        wishes_client = data["wishes"]
        wishes_server = []
        for wish in take_present_list.current_wishlist:
            if wish.wish in wishes_client:
                wishes_server.append(wish)
        # print("-------------------------------------------------------")
        # print(wishes_server)
        # print("-------------------------------------------------------")
         
        for wish in wishes_server:
            wish.user_who_buy = user.id if wish.user_who_buy == None else wish.user_who_buy

        session.commit()
        return jsonify({"message": "Successfull choice"}), 201

#TODO:
# запихать аутентификацию и авторизацию в отдельный файл
# сделать исключения для запроса при отсутствии данных или одного из параметров.
#регистрация пользователя
@app.route('/register', methods=['POST'])
def register():
    data = request.json

    # Проверка, есть ли уже такой пользователь
    with Session(engine) as session:
        user = session.query(User).filter(User.email == data['email']).first()

    # Фильтры для проверки инпута
    if user is not None:
        return jsonify({'message': 'Only one account peer email!'}), 400

    if len(data["password"]) < 6:
        return jsonify({'error': "Password is too short"}), 400

    if len(data["username"]) < 3:
        return jsonify({'error': "Username is too short"}), 400

    # if " " in data["username"]:
    #     return jsonify({'error': "Имя пользователя не должно содержать пробелов"}), 400

    if not validate_email(data["email"]):
        return jsonify({'error': "Wrong email format"}), 400



    new_user = {
        'username': data['username'],
        'password': generate_password_hash(data['password']),
        'email': data['email']
    }
    with Session(engine) as session:
        new_user = User(username=new_user['username'], password=new_user['password'], email=new_user['email'])
        session.add(new_user)
        session.commit()

    return jsonify({'message': 'User successfully registered'}), 201

# аутентификация пользователя
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    # username = data['username']
    # password = data['password']


    # Проверка имени пользователя
    with Session(engine) as session:
        user = session.query(User).filter(User.email == data['email']).first()

    try:
        check = check_password_hash(user.password, data['password'])
    except:
        check = False

    if not check:
        return jsonify({'message': 'Неверное имя пользователя или пароль'}), 401
    # Проверка, указаны ли логин и пароль
    response = make_response()

    #TODO:
    # Назначить переменный session_id
    cookie_session = generate_session_id(user)
    response.set_cookie("cookie_session", f"{cookie_session}") #пока возвращаю это, потом сделаю нормальный session_id
    return response
    # return jsonify({'message': 'Вход выполнен успешно', 'session_id': f'{username}'}), 200

@app.route('/delete', methods=['POST'])
def delete():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()
    # username = data['username']
    # password = data['password']

    user_id = find_user(cookie_session)
    # Проверка имени пользователя
    with Session(engine) as session:
        user = session.query(User).filter(User.id == user_id).first()

    try:
        check = check_password_hash(user.password, data['password'])
    except:
        check = False

    if not check:
        return jsonify({'message': 'Неверный пароль'}), 401
    # Проверка, указаны ли логин и пароль

    with Session(engine) as session:
        session.delete(user)
        session.commit()
    return jsonify({'message': 'User deleted'}), 201

@app.route('/logout', methods=['POST'])
def logout():
    cookie_session = request.cookies["cookie_session"]
    
    with Session(engine) as session:
        user_session = session.query(Sessions).filter(Sessions.server_session == cookie_session).first()
        if user_session == None:
            return jsonify({'message': 'No such user'}), 403
        
        session.delete(user_session)
        session.commit()
        response = make_response()
        response.set_cookie("cookie_session", '', expires=0)  
        return response

def find_user(cookie_session):
    with Session(engine) as session:
        user_id = session.query(Sessions).filter(Sessions.server_session == cookie_session).first().user_id
        try:
            return user_id
        except:
            return None

def generate_session_id(user):
    cookie_session = secrets.token_hex(64)

    with Session(engine) as session:
        user_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()

    if (user_session == None):
        new_session = Sessions(user_id=user.id, cookie_session=cookie_session, server_session=cookie_session)
        session.add(new_session)
        session.commit()
        return cookie_session

    return user_session.server_session


if __name__ == '__main__':
    app.run(debug=True)