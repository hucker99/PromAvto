from email import message
from enum import unique
from fileinput import filename
import os

from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
from flask.templating import render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import csv

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')

db = SQLAlchemy(app)

# Models
class Profile(db.Model):
    __tablename__ = "profile"
    id = db.Column(db.Integer, primary_key=True, nullable = False)
    name = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.Integer, nullable=False)
    custom_hashtag = db.Column(db.String(70))
    email_address = db.Column(db.String(70), nullable=False)
    photo_path = db.Column(db.String(120))
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    card_rl = relationship("Card", backref="profile", uselist=False)
    record_rl = relationship("Record")

    def __repr__(self):
        return f'<Worker {self.name} ID {self.id}>'

class Card(db.Model): 
    __table_args__ = (
        db.UniqueConstraint('serial_number'),
    )
    __tablename__ = "card" 
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.Integer, unique_key=True)
    id_person = db.Column(db.Integer, ForeignKey("profile.id"))
    card_sak = db.Column(db.String(20))
    card_type = db.Column(db.String(20))
    firmware = db.Column(db.String(20))
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    time_updated = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    

    def __repr__(self):
        return f'<Card {self.id} type {self.card_type} serial: {self.serial_number}>'   

class Record(db.Model):
    __tablename__ = "record"
    id = db.Column(db.Integer, primary_key=True)
    id_person = db.Column(db.Integer, ForeignKey("profile.id"), nullable = False)
    time_created = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable = False)
    in_or_out = db.Column(db.Boolean)

    def __repr__(self):
        return f"Record : {self.id}, created at: {self.time_created}"


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = db.session.query(Record.id, Record.time_created,Profile.name, Record.id_person, Record.in_or_out).join(Profile, isouter=True).paginate(
        page, per_page=25)
    return render_template('index.html', pagination=pagination)

@app.route('/profiles')
def profiles():
    page = request.args.get('page', 1, type=int)
    pagination = Profile.query.paginate(page, per_page=24)
    return render_template('profiles.html', pagination=pagination)        

@app.route('/profiles/<int:profile_id>/')
def profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    return render_template('profile.html', profile=profile)


@app.route('/get-csv/<string:filename>', methods=['GET', 'POST'])
def download(filename):
    directory = app.root_path
    outfile = open(f'csv/{filename}', 'w')
    outcsv = csv.writer(outfile)
    if filename == 'Record.csv':
        records = db.session.query(Record).all()
        [outcsv.writerow([getattr(curr, column.name) for column in Record.__mapper__.columns]) for curr in records]
    if filename == 'Profile.csv':
        records = db.session.query(Profile).all()
        [outcsv.writerow([getattr(curr, column.name) for column in Profile.__mapper__.columns]) for curr in records]
    if filename == 'Card.csv':
        records = db.session.query(Card).all()
        [outcsv.writerow([getattr(curr, column.name) for column in Card.__mapper__.columns]) for curr in records]

    outfile.close()
    return send_from_directory(directory=directory, path=f'csv/{filename}')

@app.route('/system-json/post-record', methods=['POST'])
def passlog():
    auth_key = 'ff0x77d02'
    person_id =None
    card_sak=None
    card_type=None
    firmware=None
    serial_number=None
    in_or_out=None
    request_data = request.get_json()

    if bool(request_data):
        if (request_data['auth_key']==auth_key):
            if('serial_number' in request_data):
                serial_number = request_data['serial_number']
            # if('user_id' in request_data):
            #     person_id = request_data['user_id']
            # if('card_sak' in request_data):
            #     card_sak = request_data['card_sak']
            # if('card_type' in request_data):
            #     card_type = request_data['card_type']
            # if('firmware' in request_data):
            #     firmware = request_data['firmware']
            # if('in_or_out'):
            #     in_or_out = bool(int(request_data['in_or_out']))

            acc_test = db.session.query(Card.serial_number).filter_by(serial_number = serial_number).all()
            person_id = int(db.session.query(Card.id_person).filter_by(serial_number = serial_number).all()[0][0])
            
            if bool(acc_test):
                record = Record(id_person = person_id)
                db.session.add(record)
                db.session.commit()
                return "1"
            else:
                return "0"
    else:
        return jsonify(error='No data recieved', message = 'Can\'t find JSON data') 

@app.route('/system-json/post-profile', methods=['POST'])
def write_profile():

    auth_key = 'ff0x77d02'
    name = None
    phone_number = None
    custom_hashtag = None
    email_address = None
    photo_path = None
    request_data = request.get_json()

    if bool(request_data):
        if('name' in request_data)&('phone_number' in request_data)&('custom_hashtag' in request_data)\
        &('email_address' in request_data)&('photo_path' in request_data):                                                              
            if(request_data['auth_key']==auth_key):
                name = request_data['name']
                phone_number = request_data['phone_number']
                custom_hashtag = request_data['custom_hashtag']
                email_address = request_data['email_address']
                photo_path = request_data['photo_path']
                profile1 = Profile(name=name, phone_number=phone_number, custom_hashtag=custom_hashtag,email_address = email_address, photo_path=photo_path)
                db.session.add(profile1)
                db.session.commit()
                return jsonify(info='JSON parsing success', message = 'Data written in DB')
            else:
                return jsonify(error='JSON parsing error', message = 'Something wrong with data')
        else:
            return jsonify(error='JSON parsing error', message = 'Something wrong with data')
    else:
        return jsonify(error='No data recieved', message = 'Can\'t find JSON data')


@app.route('/system-json/post-card', methods=['POST'])
def write_card():

    auth_key = 'ff0x77d02'
    person_id =None
    card_sak=None
    card_type=None
    firmware=None
    serial_number=None
    
    request_data = request.get_json()

    if bool(request_data):
        if (request_data['auth_key']==auth_key):
            if('serial_number' in request_data)&('user_id' in request_data)\
            &('card_sak' in request_data)&('card_type' in request_data)\
            &('firmware' in request_data):
                serial_number = request_data['serial_number']
                card_sak = request_data['card_sak']
                person_id = request_data['user_id']
                card_type = request_data['card_type']
                firmware = request_data['firmware']
                card = Card(serial_number=serial_number, card_sak=card_sak, id_person=person_id,card_type=card_type, firmware=firmware)
                db.session.add(card)
                db.session.commit()
                return jsonify(info='JSON parsing success', message = 'Data written in DB')
            else:
                return jsonify(error='JSON parsing error', message = 'Something wrong with data')
        else:
            return jsonify(error='Wrong auth key', message = 'Please enter proper key') 
    else:
        return jsonify(error='No data recieved', message = 'Can\'t find JSON data')
  

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000)

