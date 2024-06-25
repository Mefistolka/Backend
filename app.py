from flask import Flask, request, jsonify, session, make_response
from flask_restful import  Api
from flask_sqlalchemy import SQLAlchemy
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import String, ForeignKey, Table, Column, create_engine, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from typing import List
import json, random, uuid, enum
from datetime import datetime
from flask_cors import CORS, cross_origin

app = Flask(__name__)
CORS(app, support_credentials=True)
api = Api(app)
engine = create_engine("sqlite:///database.db", echo=True)



class Base(DeclarativeBase):
    pass

participators_lists = Table(
    "participator_lists",
    Base.metadata,
    Column("user", ForeignKey("user.id"), primary_key=True),
    Column("wishlist", ForeignKey("wishlist.event_id"), primary_key=True),
)

#TODO: запихать базы данных в отдельный файл
class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    # email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    participates: Mapped[List["Wishlist"]] = relationship(
        secondary=participators_lists,
        back_populates="participators",
    )

    def __repr__(self) -> str:
        return f"User(username = {self.username}, password = {self.password}, participates = {self.participates})"

class Wishlist(Base):
    __tablename__ = "wishlist"

    # id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(primary_key=True)
    creator: Mapped[int] = mapped_column(ForeignKey('user.id'))
    event_invite_code: Mapped[str] = mapped_column(String(20), unique=True)
    type: Mapped[int] = mapped_column(nullable=False)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    event_description: Mapped[str] = mapped_column(String(1000))
    max_number_of_people: Mapped[int] = mapped_column(nullable=False)
    # cur_number_of_people: Mapped[int] = mapped_column(nullable=False)
    wishes: Mapped[List["Wish"]] = relationship(cascade="all, delete")
    date: Mapped[datetime] = mapped_column(nullable=True)
    participators: Mapped[List["User"]] = relationship(
        secondary=participators_lists,
        back_populates="participates",
    )


    def __repr__(self) -> str:
        return f"Wishlist(event_id = {self.event_id},\n\
                       creator = {self.creator}, \n\
                       event_name = {self.event_name},\n\
                       event_description = {self.event_description},\n\
                       event_invite_code = {self.event_invite_code},\n\
                       type = {self.type},\n\
                       max_number_of_people = {self.max_number_of_people},\n\
                       wishes = {self.wishes},\n\
                       participators = {self.participators})"

class Wish(Base):
    __tablename__ = "wish"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("wishlist.event_id"), nullable=True)
    item: Mapped[str]
    user_who_buy: Mapped[int] = mapped_column(nullable=True)
    user_to_give: Mapped[int] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"Wish(id = {self.id}, item = {self.item})"

class Sessions(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    cookie_session: Mapped[str] = mapped_column(String(200), unique=True)
    # due_to = db.Column(db.Date())

    def __repr__(self) -> str:
        return f"User(user = {self.user_id}, \n\
                      cookie_session = {self.cookie_session}"

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

class WishlistType(enum.Enum):

    personal = 0
    secret_santa = 1



@app.route('/wishlist/type', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def wishlist_types():
    type_ = [x.name for x in WishlistType]

    print(type_)
    return json.dumps(type_, indent=4)

@app.route('/my/wishlist', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def dashboard():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()

    # GetUserBySession
    user_id = GetUserBySession(cookie_session)  
    if user_id == None:
        return jsonify({'message': 'unauthorized'}), 400
    
    with Session(engine) as session:

        user = session.query(User).filter(User.id == user_id).first()

        items = []
        for data in user.participates:
            print("------------------------------")
            for wish in data.wishes:
                print(wish.item)
            print("------------------------------")
            creator = session.query(User).filter(User.id == data.creator).first()
            wishes = []
            for wish in data.wishes:
                wishes.append({"id": wish.id, "item": wish.item})
            new_wishlist = {
                'is_owner': True if creator.id == user.id else False,
                'event_id': str(data.event_id),
                'creator': {"id": creator.id, "username": creator.username},
                'event_invite_code': data.event_invite_code,
                'event_name': data.event_name,  # проверить на отсутствие значения
                'event_description': data.event_description,
                'max_number_of_people': data.max_number_of_people,  # проверить на отсутствие значения
                # 'cur_number_of_people': 1, #y <= x
                'wishes': wishes,
                'date': str(data.date),
            }
            items.append(new_wishlist)
            print(new_wishlist)

    events = {
        'username': user.username,
        'events': items
    }
    events = json.dumps(events, indent=4)

    return events

@app.route('/my/wishlist/show', methods=['GET', 'POST'])
@cross_origin(supports_credentials=True)
def show_list():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()

    # GetUserBySession
    user_id = GetUserBySession(cookie_session)
    if user_id == None:
        return jsonify({'message': 'No such user'}), 400

    with Session(engine) as session:
        wishlist = session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).first()
        user = session.query(User).filter(User.id == user_id).first()

        if user not in wishlist.participators:
            return jsonify({'message': 'Unauthorized'}), 403

        participators_lists = []
        for member in wishlist.participators:
             participators_lists.append({"id": member.id, "username": member.username})
       
        your_gifts = []
        for wish in wishlist.wishes:
            if wish.user_who_buy == user.id:
                your_gifts.append({"item": wish.item,"user_to_give": wish.user_to_give})

        if (user_id == wishlist.creator) and (wishlist.type != 'secret_santa'):
            wishes = []
            for wish in wishlist.wishes:
                wishes.append({"id": wish.id, "item": wish.item})
                
            event_info = {
                'event_id': wishlist.event_id,
                'creator': participators_lists[0],
                'event_invite_code': wishlist.event_invite_code,
                'type': wishlist.type,
                'event_name': wishlist.event_name,  # проверить на отсутствие значения
                'event_description': wishlist.event_description,
                'max_number_of_people': wishlist.max_number_of_people,  # проверить на отсутствие значения
                'wishes':  wishes,
                'date': str(wishlist.date)[:-9],
                'partisipators': participators_lists,
            }
        else:
            wishes = []
            for wish in wishlist.wishes:
                tmp = {
                    'id': wish.id,
                    'wish': wish.item,
                    'taken':  '0' if wish.user_who_buy == None else '1'
                }
                wishes.append(tmp)

            event_info = {
                'event_id': wishlist.event_id,
                'creator': participators_lists[0],
                'type': wishlist.type,
                'event_name': wishlist.event_name,  # проверить на отсутствие значения
                'event_description': wishlist.event_description,
                'max_number_of_people': wishlist.max_number_of_people,  # проверить на отсутствие значения
                'wishes':  wishes,
                'date': str(wishlist.date)[:-9],
                'partisipators': participators_lists,
                'your_presents': your_gifts
            }

        events = json.dumps(event_info, indent=6)

        return events

@app.route('/my/list/create', methods=['POST']) # принимает куки и введённую форму data[]
@cross_origin(supports_credentials=True)
def create_list():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()

    # GetUserBySession
    user_id = GetUserBySession(cookie_session)
    if user_id == None:
        return jsonify({'message': 'No such user'}), 400

    #TODO: Обработать данные
    # Validate data BEGIN
    if data['type']  not in WishlistType._member_names_:
        return jsonify({'message': 'Wrong event type'}), 400
    
    if data.get('date') is not None:
        try:
            date = datetime.strptime(data["date"], '%Y-%m-%d').date()
        except:
            return jsonify({'message': 'Wrong date format'}), 400
    else:
        date = None
    # Validate data END

    with Session(engine) as session:
        while (True):
            event_invite_code = str(secrets.token_hex(3)) + "-" + str(secrets.token_hex(3))
            if session.query(Wishlist).filter(Wishlist.event_invite_code == event_invite_code).first() == None:
                break
    try:
        new_wishlist = {
            'event_id': str(uuid.uuid4()),
            'creator': user_id, # проверить на отсутствие значения
            'event_invite_code': event_invite_code,
            'type': data['type'],  # проверить на отсутствие значения
            'event_name': data['event_name'],  # проверить на отсутствие значения
            'event_description': data['event_description'],
            'max_number_of_people': data['max_number_of_people'],  # проверить на отсутствие значения
            # 'cur_number_of_people': 1, #y <= x
            'participators': user_id,
            'date': date,
        }
    except Exception as e:
        print(e)
        return jsonify({'message': 'Unable to upload list new_wishlist'}), 400

    print(new_wishlist)

    with Session(engine) as session:
        try:
            # new_list = Wishlist()
            # new_list.event_id = new_wishlist["event_id"]
            # new_list.creator = new_wishlist["creator"]
            # new_list.event_invite_code = new_wishlist["event_invite_code"]
            # new_list.type = new_wishlist["type"]
            # new_list.event_name = new_wishlist["event_name"]
            # new_list.event_description = new_wishlist["event_description"]
            # new_list.max_number_of_people = new_wishlist["max_number_of_people"]
            # new_list.cur_number_of_people = new_wishlist["cur_number_of_people"]
            # new_list.date = new_wishlist["date"]
            # new_list.participators.append(session.query(User).filter(User.id == user_id).first())
            new_list = Wishlist(
                event_id = new_wishlist["event_id"],
                creator = new_wishlist["creator"],
                event_invite_code = new_wishlist["event_invite_code"],
                type = new_wishlist["type"],
                event_name = new_wishlist["event_name"],
                event_description = new_wishlist["event_description"],
                max_number_of_people = new_wishlist["max_number_of_people"],
                # cur_number_of_people = new_wishlist["cur_number_of_people"],
                date = new_wishlist["date"])
            new_list.participators.append(session.query(User).filter(User.id == user_id).first())
            
            session.add(new_list)
            session.commit()
        except Exception as e:
            print(e)
            return jsonify({'message': 'Unable to upload list'}), 400

    return jsonify({'message': 'List created successfully'}), 201

@app.route('/my/list/join', methods=['PUT'])
@cross_origin(supports_credentials=True)
def join_list():
    user_session = request.cookies["cookie_session"] # что-то сделать отсюда)
    data = request.get_json()

    # GetUserBySession
    user_id = GetUserBySession(user_session)
    if user_id == None:
        return jsonify({'error': "unauthorized"}), 403

    with Session(engine) as session:
        event = session.query(Wishlist).filter(Wishlist.event_invite_code == data['event_invite_code']).first()
        if not event:
            return jsonify({'error': "No such event"}), 400

        if user_id in [user.id for user in event.participators]:
            return jsonify({'message': 'Already in this room'}), 400

        number_of_people = 0
        for x in event.participators:
            number_of_people += 1

        if (number_of_people + 1) > event.max_number_of_people:
            return jsonify({'message': "No more participants allowed"}), 203

        event.participators.append(session.query(User).filter(User.id == user_id).first())
        session.commit()

    return jsonify({'message': "Successful join"}), 200

@app.route('/my/list/leave', methods=['PUT']) #принимает id комнаты
@cross_origin(supports_credentials=True)
def leave_list():
    user_session = request.cookies["cookie_session"] # что-то сделать отсюда)
    data = request.get_json()

    #TODO: запретить создателю комнаты ливать из неё
    user_id = GetUserBySession(user_session)
    if user_id == None:
        return jsonify({'error': "unauthorized"}), 403


    with Session(engine) as session:
        wishlist = session.query(Wishlist).filter(Wishlist.event_id == data['event_id']).first()
        if not wishlist:
            return jsonify({'error': "No such event"}), 400

        if user_id not in [id.id for id in wishlist.participators]:
            # return jsonify({'message': str(wishlist.participators)}), 403
            return jsonify({'message': 'Unauthorized'}), 403

        wishlist.participators.remove(session.query(User).filter(User.id == user_id).first())

        for wish in wishlist.wishes:
            if wish.user_who_buy == user_id:
                wish.user_who_buy = None
                wish.user_to_give = None
        session.commit()

    return jsonify({'message': "Successful leave"}), 200

@app.route('/my/list/delete', methods=['DELETE']) # принимает event_id
@cross_origin(supports_credentials=True)
def delete_list():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    user_id = GetUserBySession(user_session)

    with Session(engine) as session:
        list_to_del = session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).first()
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
@cross_origin(supports_credentials=True)
def edit_list():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    # GetUserBySession
    user_id = GetUserBySession(user_session)
    if user_id == None:
        return jsonify({'error': "unauthorized"}), 403

    with Session(engine) as session:

        # try: 
        wishlist_from_db = session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).first()

        
        if not wishlist_from_db.creator == user_id:
                    return jsonify({'message': 'You are not owner of this wishlist'}), 400
        
        # Validate data BEGIN
        if data.get('date') is not None:
            try:
                date = datetime.strptime(data["date"], '%d-%m-%Y').date()
            except:
                return jsonify({'message': 'Wrong date format'}), 400
        else:
            date = None

        try:
            item_id = [id.get("id") for id in data['wishes']]
        except:
            pass
        # Validate data END

        session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).update(
            {Wishlist.event_name: data["event_name"],
            Wishlist.event_description: data["event_description"],
            Wishlist.max_number_of_people: data["max_number_of_people"],
            Wishlist.date: date})
        wishlist_from_db = session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).first()

        wishlist_from_db.participators = []
        for participators in data["participators"]:
            wishlist_from_db.participators.append(session.query(User).filter(User.id == participators.get("id")).first())
        
        # Wishes updating START
        # Удаляем все wish, которых нет в json, но есть в wishlist
        for wish in wishlist_from_db.wishes:
            if wish.id not in item_id:
                wish = session.query(Wish).filter(Wish.id == wish.id and Wish.event_id == data['event_id']).first()
                try:
                    session.delete(wish)
                except:
                    pass
        # update все wish, которые изменили, и которые имеют id
        for id in item_id:
            try:
                session.query(Wish).filter(Wish.id == id and Wish.event_id == data['event_id']).update({"item": next(wish["item"] for wish in data['wishes'] if wish["id"] == id)})
                session.commit()
            except:
                pass
        # Добавляем wish без id
        for wish in data["wishes"]:
            if wish.get("id") != None:
                continue
            new_item = Wish(item=wish.get("item"))
            wishlist_from_db.wishes.append(new_item)
        # Wishes updating END

        # wishlist_from_db.wishes = []
        # event.participators.remove(session.query(User).filter(User.id == user_id).first())
        # for participators in data["wishes"]:
        #     wishlist_from_db.wishes.append(session.query(User).filter(User.id == participators.get("id")).first())
            # wishlist_from_requst = Wishlist(
            #         event_id = data["event_id"],
            #         event_invite_code = data["event_invite_code"],
            #         event_name = data["event_name"],
            #         event_description = data["event_description"],
            #         max_number_of_people = data["max_number_of_people"],
            #         date = data["date"],
            #         participators = session.query(User).filter(User.id.in_(user_id)).all())
            
            # wishlist_from_requst = Wishlist(event_id = data["event_id"])
            # for wish in data["wishes"]:
                # print(wish)
                # new_wish = Wish(wish=wish)
                # wishlist_from_requst.wishes.append(new_wish)

        
        # except:
            # return jsonify({'message': 'There is no such event'}), 400

        
        session.commit()

        # wishlist_from_db = session.merge(wishlist_from_requst)
        # try:
        #     wishlist_from_db.event_name = data["event_name"]
        #     wishlist_from_db.event_description = data["event_description"]
        #     wishlist_from_db.max_number_of_people = data["max_number_of_people"]
        #     wishlist_from_db.wishes = []
        #     session.flush()
        #     for wish in data["wishes"]:
        #         new_wish = Wish(wish=wish)
        #         wishlist_from_db.wishes.append(new_wish)
        #         # print("-------------------------------------------------------")
        #         # print(wishlist_from_db.wishes)
        #         # print("-------------------------------------------------------")
        # except:
        #     return jsonify({"message": "/my/list/edit missing data"}), 500

        # try:
        #     session.commit()
        # except:
        #     return jsonify({"message": "Something wrong with editing"}), 500

    return jsonify({"message": "Update succesfull"}), 201

@app.route('/secret/santa', methods=['PUT'] ) #принимает event_id
@cross_origin(supports_credentials=True)
def secret_santa():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    user_id = GetUserBySession(user_session)
    if user_id == None:
        return jsonify({'message': 'unauthorized'}), 403


    with Session(engine) as session:
        santa_wishlist = session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).first()
        if santa_wishlist == None:
            return jsonify({'message': 'There is no such event'}), 400

        if not santa_wishlist.creator == user_id:
            return jsonify({'message': 'You are not owner of this'}), 400

        if len(santa_wishlist.wishes) != len(santa_wishlist.participators):
            return jsonify({'message': 'Not enougth people or presents'}), 400

        participators_lists = [member.id for member in santa_wishlist.participators]

        # print("---------------------------------------------------------------")
        # print(len(santa_list.wishes))
        # print(len(santa_list.participators))
        # print("---------------------------------------------------------------")
        gift_giver = participators_lists.copy()
        gift_receiver = participators_lists.copy()
        random.shuffle(gift_receiver)
        
        while any(gift_giver[i] == gift_receiver[i] for i in range(len(participators_lists))):
            random.shuffle(gift_receiver)

        gift_pairs = [(giver, receiver) for giver, receiver in zip(gift_giver, gift_receiver)]
        for wish, user in zip(santa_wishlist.wishes, gift_pairs):
            # print("---------------------------------------------------------------")
            # print(wishlist)
            # print(user)
            # print("---------------------------------------------------------------")
            wish.user_who_buy = user[0]
            wish.user_to_give = user[1]
        session.commit()
    return jsonify({'message': 'Succesfull shuffle, reload page to see difference'}), 200

@app.route('/take/present', methods=['PUT'] ) #принимает event_id и то что выбрал юзер(wishes)
@cross_origin(supports_credentials=True)
def take_present():
    user_session = request.cookies["cookie_session"]
    data = request.get_json()

    # GetUserBySession
    user_id = GetUserBySession(user_session)
    if user_id == None:
        return jsonify({'error': "unauthorized"}), 403

    with Session(engine) as session:
        wishlist = session.query(Wishlist).filter(Wishlist.event_id == data["event_id"]).first()
        user = session.query(User).filter(User.id == user_id).first()
        if wishlist == None:
            return jsonify({'message': 'There is no such event'}), 400
        # print("-------------------------------------------------------")
        # print(take_present_list.participators)
        # print("-------------------------------------------------------")
        if user not in wishlist.participators:
            return jsonify({'message': 'Unauthorized'}), 403


        wishes_client = data["wish_id"]
        wishes_server = []
        for wish in wishlist.wishes:
            if wish.id in wishes_client and wish.event_id == data["event_id"]:
                wishes_server.append(wish)
        # print("-------------------------------------------------------")
        # print(wishes_server)
        # print("-------------------------------------------------------")

        for wish in wishes_server:
            wish.user_who_buy = user.id if wish.user_who_buy == None else wish.user_who_buy
            wish.user_to_give = wishlist.creator

        session.commit()
        return jsonify({"message": "Successfull choice"}), 201

#TODO:
# запихать аутентификацию и авторизацию в отдельный файл
# сделать исключения для запроса при отсутствии данных или одного из параметров.
#регистрация пользователя
@app.route('/register', methods=['POST'])
@cross_origin(supports_credentials=True)
def register():
    data = request.get_json()

    # Проверка, есть ли уже такой пользователь
    with Session(engine) as session:
        user = session.query(User).filter(User.username == data['username']).first()

    # Фильтры для проверки инпута
    if user is not None:
        return jsonify({'message': 'This username is taken'}), 400

    if len(data["password"]) < 6:
        return jsonify({'error': "Password is too short"}), 400

    if len(data["username"]) < 6:
        return jsonify({'error': "Username is too short"}), 400

    if " " in data["username"]:
        return jsonify({'error': "The username must not contain spaces"}), 400

    new_user = {
        'username': data['username'],
        'password': generate_password_hash(data['password']),
    }
    with Session(engine) as session:
        new_user = User(username=new_user['username'], password=new_user['password'])
        session.add(new_user)
        session.commit()

    return jsonify({'message': 'User successfully registered'}), 201

# аутентификация пользователя
@app.route('/login', methods=['POST'])
@cross_origin(supports_credentials=True)
def login():
    data = request.get_json()

    # Проверка имени пользователя
    with Session(engine) as session:
        user = session.query(User).filter(User.username == data['username']).first()

    try:
        check = check_password_hash(user.password, data['password'])
    except:
        check = False

    if not check:
        return jsonify({'message': 'Wrong username or password'}), 401
    # Проверка, указаны ли логин и пароль

    cookie_session = RefreshToken(user)
    
    response = make_response()
    response.set_cookie("cookie_session", f"{cookie_session}") #пока возвращаю это, потом сделаю нормальный session_id
    # response.headers.add("Access-Control-Allow-Origin", "*")
    return response
    # return jsonify({'message': 'Вход выполнен успешно', 'session_id': f'{username}'}), 200

@app.route('/delete', methods=['POST'])
@cross_origin(supports_credentials=True)
def delete():
    cookie_session = request.cookies["cookie_session"]
    data = request.get_json()
    # username = data['username']
    # password = data['password']

    user_id = GetUserBySession(cookie_session)
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
@cross_origin(supports_credentials=True)
def logout():
    cookie_session = request.cookies["cookie_session"]

    with Session(engine) as session:
        user_session = session.query(Sessions).filter(Sessions.cookie_session == cookie_session).first()
        if user_session == None:
            return jsonify({'message': 'No such user'}), 403

        session.delete(user_session)
        session.commit()
        response = make_response()
        response.set_cookie("cookie_session", '', expires=0)
        return response

def GetUserBySession(cookie_session):
    with Session(engine) as session:
        user_id = session.query(Sessions).filter(Sessions.cookie_session == cookie_session).first().user_id
        try:
            return user_id
        except:
            return None

def GetSessionCookie(user):
    cookie_session = secrets.token_hex(64)

    with Session(engine) as session:
        user_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()

    if (user_session == None):
        new_session = Sessions(user_id=user.id, cookie_session=cookie_session)
        session.add(new_session)
        session.commit()
        return cookie_session

    return user_session

@app.route('/refresh/token', methods=['POST'])
def RefreshToken(user = None):
    cookie_session = secrets.token_hex(64)

    if user != None:
        with Session(engine) as session:
            user_session = session.query(Sessions).filter(Sessions.user_id == user.id).first()

        if (user_session == None):
            new_session = Sessions(user_id=user.id, cookie_session=cookie_session)
            session.add(new_session)
            session.commit()
            return cookie_session

        return user_session.cookie_session
    
    with Session(engine) as session:
        req_cookie_session = request.cookies["cookie_session"]
        query = Sessions(cookie_session=req_cookie_session)
        query.cookie_session = cookie_session
        session.commit()
        response = make_response()
        response.set_cookie("cookie_session", cookie_session)
        return response

if __name__ == '__main__':
    app.run(debug=True)