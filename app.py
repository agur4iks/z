import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Секретный ключ нужен для работы сессий
app.config['SECRET_KEY'] = 'flower-power-9'
# Указываем путь к файлу базы данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plants.db'
# Папка, куда будут сохраняться загруженные фотографии растений
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Если папки для загрузок нет, создаем её автоматически
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# МОДЕЛИ ДАННЫХ

# Таблица пользователей
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False) # Уникальное имя
    password_hash = db.Column(db.String(200), nullable=False) # Пароль хранится в зашифрованном виде

# Таблица растений
class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False) # Название цветка
    description = db.Column(db.Text) # Краткое описание
    image_name = db.Column(db.String(100), nullable=False) # Имя файла картинки
    author = db.Column(db.String(50), nullable=False) # Имя пользователя, который выставил
    taker_id = db.Column(db.Integer) # ID пользователя, который забрал (None, если свободен)

# Команда для автоматического создания таблиц в plants.db при запуске
with app.app_context():
    db.create_all()

# МАРШРУТЫ (РОУТЫ)

# Главная страница: показывает только доступные (свободные) растения
@app.route('/')
def index():
    # Находим все растения, у которых taker_id пустой
    plants = Plant.query.filter_by(taker_id=None).all()
    return render_template('index.html', plants=plants)

# Личный кабинет: список своих растений и тех, что ты забрал
@app.route('/my_plants')
def my_plants():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Растения, которые забрал текущий пользователь
    taken = Plant.query.filter_by(taker_id=session['user_id']).all()
    # Растения, которые выставил текущий пользователь (по его имени)
    posted = Plant.query.filter_by(author=session['username']).all()
    return render_template('my_plants.html', taken=taken, posted=posted)

# Регистрация нового пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        # Проверяем, не занято ли имя пользователя
        if User.query.filter_by(username=u).first():
            flash('Логин занят!', 'danger')
            return redirect(url_for('register'))
        # Шифруем пароль и сохраняем в базу
        new_user = User(username=u, password_hash=generate_password_hash(p))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Вход в аккаунт
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        # Проверяем наличие пользователя и правильность зашифрованного пароля
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            # Сохраняем данные пользователя в сессию
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')

# Добавление нового растения на сайт
@app.route('/add', methods=['GET', 'POST'])
def add_plant():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')
        if file and title:
            # Делаем имя файла безопасным и сохраняем его
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Записываем информацию о растении в базу данных
            new_p = Plant(title=title,
                          description=request.form.get('description'),
                          image_name=filename,
                          author=session['username'])
            db.session.add(new_p)
            db.session.commit()
            return redirect(url_for('index'))
    return render_template('add.html')

# Кнопка "Забрать", закрепляет растение за пользователем
@app.route('/take/<int:pid>')
def take_plant(pid):
    if 'user_id' not in session: return redirect(url_for('login'))
    p = Plant.query.get(pid)
    # Проверяем, что пользователь не пытается забрать своё собственное растение
    if p and p.author != session['username']:
        p.taker_id = session['user_id']
        db.session.commit()
    return redirect(url_for('my_plants'))

# Выход: очищает сессию
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
