import datetime
import os
import sqlite3
import time
from datetime import date
import itertools
from flask import Flask, render_template, request

UPLOAD_FOLDER = './static/post_photos'

app = Flask(__name__)


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

outer_scope_connection = sqlite3.connect('database.db')
outer_scope_cursor = outer_scope_connection.cursor()
outer_scope_cursor.execute('''
CREATE TABLE IF NOT EXISTS Users(
id INTEGER PRIMARY KEY,
last_name TEXT NOT NULL,
first_name TEXT NOT NULL,
patronymic TEXT,
email TEXT NOT NULL,
password INTEGER NOT NULL,
date_of_birthday TEXT NOT NULL,
is_authorized INTEGER NOT NULL
);
''')

outer_scope_cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON Users (email)")
outer_scope_connection.commit()
outer_scope_connection.close()

outer_scope_connection = sqlite3.connect('database.db')
outer_scope_cursor = outer_scope_connection.cursor()

outer_scope_cursor.execute('''
CREATE TABLE IF NOT EXISTS Posts(
id INTEGER PRIMARY KEY,
note_header TEXT NOT NULL,
note_description TEXT NOT NULL,
note_photo TEXT,
note_date TEXT NOT NULL,
note_user_email TEXT NOT NULL
);
''')

outer_scope_connection.commit()
outer_scope_connection.close()


@app.route('/')
def home():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute("SELECT is_authorized FROM Users WHERE is_authorized = ?", (1,))
    result = cursor.fetchone()
    if result:
        wish = ''
        now_hour = datetime.datetime.now().hour
        if 0 < now_hour < 10:
            wish = 'Продуктивного вам утра'
        elif 10 < now_hour < 17:
            wish = 'Хорошего вам дня'
        elif 17 < now_hour < 24:
            wish = 'Доброго вам вечера'
        cursor.execute("SELECT * FROM Users WHERE is_authorized = ?", (1,))
        result = cursor.fetchall()
        messages = {'hello': f'Здравствуйте, {result[0][2]} {result[0][3]}',
                    'date': f'Сегодня {date.today()}',
                    'wish': wish}
        connection.close()
        return render_template('home.html', messages=messages, auth_user=True)
    return render_template('home.html', auth_user=False)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        last_name = request.form['last_name']
        first_name = request.form['first_name']
        patronymic = request.form['patronymic']
        email = request.form['email']
        password = request.form['password']
        password_confirmation = request.form['password_confirmation']
        date_of_birthday = request.form['date_of_birthday']
        if password != password_confirmation:
            some_error = 'Пароли не совпадают'
            return render_template('unsuccessful_page.html', some_error=some_error)
        else:
            connection = sqlite3.connect('database.db')
            cursor = connection.cursor()
            cursor.execute("SELECT email FROM Users WHERE email = ?", (email,))
            result = cursor.fetchone()
            if result:
                if result[0] == email:
                    some_error = f'Пользователь с таким e-mail уже существует'
                    connection.close()
                    return render_template('unsuccessful_page.html', some_error=some_error)
            connection = sqlite3.connect('database.db')
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO Users (last_name, first_name, patronymic, email, password, date_of_birthday, "
                "is_authorized) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f'{last_name}', f'{first_name}', f'{patronymic}', f'{email}', f'{password}', f'{date_of_birthday}', 1))
            connection.commit()
            connection.close()
            redirect_time = 0.5
            redirect_url = '/'
            return render_template('redirect.html', redirect_time=redirect_time, redirect_url=redirect_url)
    else:
        return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute("SELECT email FROM Users WHERE email = ?", (email,))
        result = cursor.fetchone()
        if result:
            if result[0] == email:
                cursor.execute("SELECT password FROM Users WHERE email = ?", (email,))
                result = cursor.fetchone()
                if result[0] == password:
                    cursor.execute('UPDATE Users SET is_authorized = ? WHERE email = ?', (1, email))
                    connection.commit()
                    connection.close()
                    redirect_time = 0.5
                    redirect_url = '/'
                    return render_template('redirect.html', redirect_time=redirect_time, redirect_url=redirect_url)
                else:
                    some_error = f'Пароль не подходит'
                    connection.close()
                    return render_template('unsuccessful_page.html', some_error=some_error)
        else:
            some_error = f'Пользователя с таким e-mail не существует'
            connection.close()
            return render_template('unsuccessful_page.html', some_error=some_error)

    else:
        return render_template('login.html')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute('UPDATE Users SET is_authorized = ? WHERE is_authorized = ?', (0, 1))
        connection.commit()
        connection.close()
        redirect_time = 0.5
        redirect_url = '/'
        return render_template('redirect.html', redirect_time=redirect_time, redirect_url=redirect_url)

    else:
        return render_template('logout.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    uniq_name = f'{time.time()}'
    hash_name = hash(uniq_name)
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM Users WHERE is_authorized = ?", (1,))
    note_user_email = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM Posts WHERE note_user_email = ?", (note_user_email,))
    all_data = cursor.fetchall()
    num = 0
    posts = {}
    while num < len(all_data):
        posts.update({
            all_data[num][0]: [all_data[num][1], all_data[num][2], all_data[num][3], all_data[num][4]]
        })
        num += 1
    connection.close()
    page = request.args.get('page', 1, type=int)
    per_page = 6
    total_items = len(posts)
    total_pages = (total_items + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    current_posts = dict(itertools.islice(posts.items(), start, end))
    if request.method == 'POST':
        if f'delete_note' in request.form:
            note_pic = request.form['note_pic']
            note_id = request.form['note_id']
            connection = sqlite3.connect('database.db')
            cursor = connection.cursor()
            cursor.execute("SELECT email FROM Users WHERE is_authorized = ?", (1,))
            note_user_email = cursor.fetchone()[0]
            cursor.execute('DELETE FROM Posts WHERE note_user_email  = ? AND id = ?', (note_user_email, note_id,))
            connection.commit()
            connection.close()
            if os.path.isfile(note_pic):
                os.remove(note_pic)
            redirect_time = 0.5
            redirect_url = '/dashboard'
            return render_template('redirect.html', redirect_time=redirect_time, redirect_url=redirect_url, posts=posts)
        if 'add_note' in request.form:
            connection = sqlite3.connect('database.db')
            cursor = connection.cursor()
            note_header = request.form['note_header']
            note_description = request.form['note_description']
            note_photo = request.files['note_photo']
            note_photo_name = ''
            if note_photo:
                file = note_photo
                file.filename = f'{hash_name}.jpg'
                path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(path)
                note_photo_name = hash_name
            date_today = datetime.datetime.now().replace(microsecond=0)
            day_ = date_today.date()
            time_ = date_today.time()
            note_date = f'{day_} | {time_}'
            cursor.execute("SELECT email FROM Users WHERE is_authorized = ?", (1,))
            note_user_email = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO Posts (note_header, note_description, note_photo, note_date, note_user_email) VALUES ("
                "?, ?, ?, ?, ?)",
                (f'{note_header}', f'{note_description}', f'{note_photo_name}', f'{note_date}', f'{note_user_email}'))
            connection.commit()
            connection.close()
            redirect_time = 0.5
            redirect_url = '/dashboard'
            return render_template('redirect.html', redirect_time=redirect_time, redirect_url=redirect_url, current_posts=current_posts, posts=posts)
    else:
        return render_template('dashboard.html', posts=posts, current_posts=current_posts, page=page, total_pages=total_pages)


if __name__ == '__main__':
    app.run()
