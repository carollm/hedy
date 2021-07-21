from website.auth import requires_login, is_teacher, current_user
import utils
import uuid
from flask import request, jsonify, redirect
from flask_helpers import render_template
import os
import hedyweb
TRANSLATIONS = hedyweb.Translations ()
from config import config
cookie_name     = config ['session'] ['cookie_name']

def routes (app, database, requested_lang):
    global DATABASE
    DATABASE = database

    from app import render_main_menu

    @app.route('/class/<class_id>', methods=['GET'])
    @requires_login
    def get_class (user, class_id):
        if not is_teacher (request):
            return 'Only teachers can retrieve classes', 403
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return 'No such class', 404
        students = []
        for student_username in Class.get ('students'):
            student = DATABASE.user_by_username (student_username)
            programs = DATABASE.programs_for_user(student_username)
            highest_level = 0
            latest_shared = None
            for program in programs:
                if program ['level'] > highest_level:
                    highest_level = program ['level']
                if not program.get ('public'):
                    continue
                if not latest_shared or latest_shared ['date'] < program ['date']:
                    latest_shared = os.getenv ('BASE_URL') + '/hedy/' + str (program ['level']) + '/' + program ['id'] + '?lang=' + requested_lang ()
            students.append ({'username': student_username, 'last_login': utils.mstoisostring (student ['last_login']), 'programs': len (programs), 'highest_level': highest_level, 'latest_shared': latest_shared})

        if utils.is_testing_request (request):
            return jsonify ({'students': students, 'link': Class ['link'], 'name': Class ['name'], 'id': Class ['id']})
        return render_template ('class-overview.html', lang=requested_lang (), auth=TRANSLATIONS.data [requested_lang ()] ['Auth'], menu=render_main_menu('my-profile'), username=current_user (request) ['username'], current_page='my-profile', class_info={'students': students, 'link': os.getenv ('BASE_URL') + '/class/' + Class ['id'] + '/prejoin/' + Class ['link'], 'name': Class ['name'], 'id': Class ['id']})

    @app.route('/class', methods=['POST'])
    @requires_login
    def create_class (user):
        if not is_teacher (request):
            return 'Only teachers can create classes', 403

        body = request.json
        # Validations
        if not isinstance(body, dict):
            return 'body must be an object', 400
        if not isinstance(body.get('name'), str):
            return 'name must be a string', 400

        Class = {
            'id': uuid.uuid4().hex,
            'date': utils.timems (),
            'teacher': user ['username'],
            'link': uuid.uuid4().hex,
            'name': body ['name'],
            'students': [],
        }

        DATABASE.store_class (Class)

        return {}, 200

    @app.route('/class/<class_id>', methods=['PUT'])
    @requires_login
    def update_class (user, class_id):
        if not is_teacher (request):
            return 'Only teachers can update classes', 403

        body = request.json
        # Validations
        if not isinstance(body, dict):
            return 'body must be an object', 400
        if not isinstance(body.get('name'), str):
            return 'name must be a string', 400

        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return 'No such class', 404

        Class = DATABASE.update_class (class_id, body ['name'])

        return {}, 200

    @app.route('/class/<class_id>', methods=['DELETE'])
    @requires_login
    def delete_class (user, class_id):
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return 'No such class', 404

        DATABASE.delete_class (Class)

        return {}, 200

    @app.route('/class/<class_id>/prejoin/<link>', methods=['GET'])
    def prejoin_class (class_id, link):
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['link'] != link:
            return 'No such class', 404
        user = {}
        if request.cookies.get (cookie_name):
            token = DATABASE.get_token(request.cookies.get (cookie_name))
            if token:
                user = DATABASE.user_by_username(token ['username'])

        return render_template ('class-prejoin.html', lang=requested_lang (), auth=TRANSLATIONS.data [requested_lang ()] ['Auth'], menu=render_main_menu('my-profile'), username=current_user (request) ['username'], current_page='my-profile', class_info={'link': os.getenv ('BASE_URL') + '/class/' + Class ['id'] + '/join/' + Class ['link'] + '?lang=' + requested_lang (), 'name': Class ['name']})

    @app.route('/class/<class_id>/join/<link>', methods=['GET'])
    @requires_login
    def join_class (user, class_id, link):
        Class = DATABASE.get_class (class_id)
        if not Class or Class ['link'] != link:
            return 'No such class', 404

        DATABASE.add_student_to_class (Class, user ['username'])

        return redirect(request.url.replace('/class/' + class_id + '/join/' + link, '/my-profile'), code=302)

    @app.route('/class/<class_id>/student/<student_id>', methods=['DELETE'])
    @requires_login
    def leave_class (user, class_id, student_id):

        Class = DATABASE.get_class (class_id)
        if not Class or Class ['teacher'] != user ['username']:
            return 'No such class', 404

        DATABASE.remove_student_from_class (Class, student_id)

        return {}, 200
