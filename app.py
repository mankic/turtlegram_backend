from datetime import datetime, timedelta
from functools import wraps
import json
from urllib import request
from flask import Flask, jsonify, request, Response, abort    # 클래스 가져오기
from flask_cors import CORS
from pymongo import MongoClient
import hashlib
from bson import ObjectId
import jwt

app = Flask(__name__)   # 플라스크 객체를 생성한다. __name__은 현재 실행 중인 모듈 이름을 전달.
cors = CORS(app, resources={r'*': {'origins': '*'}})    # *는 모든 origin허용, 원하는 프론트엔드에서만 받도록 수정

client = MongoClient('localhost', 27017)
db = client.turtlegram

SECRET_KEY = 'turtle'


def authorize(f):
    @wraps(f)   # 한가지 함수를 여러가지 함수에 적용시킬때 나는 에러를 방지. import 해줘야함.
    def decorated_function():
        if not 'Authorization' in request.headers:   # 헤더에 Authorization 없으면 abort
            abort(401)
        token = request.headers['Authorization']    # 헤더에 Authorization token에 저장
        try:
            user = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])  # 토큰 디코딩
        except:
            abort(401) 
        return f(user)  # user 값이 function 안에 들어가서 실행된다.

    return decorated_function

@app.route('/')     # 기본서버 127.0.0.1:5000 뒤에 붙는 주소를 적어준다.
@authorize
def hello_world(user):  # 위의 주소를 호출 시 보여 줄 것을 함수로 작성
    print(user)
    return jsonify({'message': 'success'})

# @app.route("/signup", methods=['POST'])
# def sign_up():
#     print(request)  # <Request 'http://127.0.0.1:5002/signup' [POST]>
#     print(request.form)   # ImmutableMultiDict([('id', 'minki'), ('password', '1234')])
#     print(request.form['id'])   # minki  # key 값이 존재하지 않으면 에러
#     print(request.form.get('id'))   # minki # key 값이 존재하지 않아도 None 출력하고 서버 돌아감
#     return jsonify({'message': 'success2'})

@app.route("/signup", methods=['POST'])
def sign_up():
    # print(request.data)     # b'{\r\n    "id":"minki2",\r\n    "password":"1234"\r\n}'
    # data = json.loads(request.data)     # json으로 꺼내와야 딕셔너리형태로 나온다.
    # print(data)             # {'id': 'minki2', 'password': '1234'}
    # print(data.get('id'))   # minki2
    # print(data['password']) # 1234

    signup_info = json.loads(request.data)     # json으로 꺼내와야 딕셔너리형태로 나온다.

    id_receive = signup_info.get('email')
    pw_receive = signup_info.get('password')

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()    # 패스워드 해싱처리

    if db.users.find_one({'user_id':id_receive}):
        return jsonify({'msg':'중복된 이메일 입니다.'}), 401

    else:
        doc = {'user_id': id_receive, 'hashed_pw': pw_hash}

        user = db.users.insert_one(doc)     # turtlegram DB의 users collection에 저장
        
        return jsonify({'result': 'success', 'msg': '회원가입성공'})


@app.route("/signin", methods=['POST'])
def sign_in():

    # print(request)
    signin_info = json.loads(request.data)     # json으로 꺼내와야 딕셔너리형태로 나온다.

    id_receive = signin_info.get('email')
    pw_receive = signin_info.get('password')

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()    # 패스워드 해싱처리

    # 가입된 정보 찾기
    result = db.users.find_one({
        'user_id': id_receive,
        'hashed_pw': pw_hash
    })
    # print(result)

    # 정보 없으면 바로 리턴
    if result is None:
        return jsonify({'msg': '아이디나 비밀번호가 틀립니다.'}), 401

    #정보있으면 payload에 아이디와 시간 저장
    payload = {
        'id': str(result['_id']),   # str 안붙이면 ObjectId()까지 같이나옴
        'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
    }   
    # print(payload)

    # 토큰 생성
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    print(token)
    return jsonify({'msg': '로그인 완료', 'token':token})   # token 반환!!!


@app.route("/getuserinfo", methods=['GET'])
@authorize  # 인증이 된 사람만.
def get_user_info(user):    # authorize 유저 추가

    result = db.users.find_one({
        '_id': ObjectId(user['id'])     # ObjectId 붙여야 DB에서 찾을수있다.
    })
    print(result)
    return jsonify({'msg':'success', 'email':result['user_id']})    # 아이디값 뽑아서 반환  

# decorate 함수 쓰기 전 getuserinfo-------
# @app.route("/getuserinfo", methods=['GET'])
# def get_user_info():
#     token = request.headers.get('Authorization')     # 로컬스토리지는 http 헤더로 들어가기때문.   

#     if not token:
#         return jsonify({"message":"no token"}), 402

#     user = jwt.decode(token, SECRET_KEY, algorithms='HS256')

#     result = db.users.find_one({
#         '_id': ObjectId(user['id'])     # ObjectId 붙여야 DB에서 찾을수있다.
#     })
#     return jsonify({'msg':'success', 'email':result['user_id']})    # 아이디값 뽑아서 반환  
 
    
@app.route('/article', methods=['POST'])
@authorize  # 인증이 된 사람만.
def post_article(user):     # authorize 유저 추가
    data = json.loads(request.data)
    print(data)

    # user의 id값을 가져와서 옵젝화 시켜주고 그값을 db에서 찾아서 저장
    db_user = db.users.find_one({'_id': ObjectId(user.get('id'))})

    # 현재 시간
    now = datetime.now().strftime("%H:%M:%S")
    # 게시글달기에 필요한 데이터
    doc = {
        'title': data.get('title', None),   # 값이 없어도 None값으로 저장한다.
        'content': data.get('content', None),
        'user': user['id'],     # _id 값
        'user_email': db_user['user_id'],
        'time': now,
    }
    print(doc)

    db.article.insert_one(doc)

    return jsonify({'message': 'success'})


if __name__ == '__main__':  # 직접 부를때만 실행

    # debug=True를 하면 고칠 때마다 자동으로 실행한다.
    app.run('0.0.0.0', port=5002, debug=True)
