from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
from sqlalchemy import text

app = Flask(__name__)
# Ma clé secrète pour sécuriser les sessions et les messages flash [cite: 17]
app.secret_key = 'ma_cle_secrete_astro_expert'

# Configuration de la connexion à ma base de données MariaDB (TP Étape 4) [cite: 32, 35]
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/astronomie_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation des extensions pour la BDD et le temps réel (Bonus WebSockets) [cite: 32, 45]
db = SQLAlchemy(app)
socketio = SocketIO(app)

# --- MES MODÈLES DE DONNÉES ---

# Table pour stocker les informations des utilisateurs [cite: 33]
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False) # Mots de passe hashés [cite: 19]

# Table unique pour les appareils photos et les téléscopes [cite: 34]
class Equipement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type_equip = db.Column(db.String(50), nullable=False) # 'photo' ou 'telescope'
    categorie = db.Column(db.String(100), nullable=False)
    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    date_sortie = db.Column(db.String(50))
    score = db.Column(db.Integer)
    resume = db.Column(db.Text) # Colonne Bonus : Page de détails 
    image_path = db.Column(db.String(255)) # Chemin vers mes images locales importées

# Table pour la galerie de photographies [cite: 28]
class Photographie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(100), nullable=False)
    url_image = db.Column(db.String(255), nullable=False)

# Table pour le bonus Actualités (WebSockets) [cite: 44]
class Actualite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)

# Tables pour le bonus Forum [cite: 46, 47]
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# --- INITIALISATION ET INJECTION DE DONNÉES ---

with app.app_context():
    # Création de la BDD et des tables si nécessaire [cite: 35, 38]
    engine_init = sqlalchemy.create_engine('mysql+pymysql://root:root@localhost/')
    with engine_init.connect() as conn:
        conn.execute(text("CREATE DATABASE IF NOT EXISTS astronomie_db"))
    db.create_all()

    # J'ajoute mes données réelles et mes images locales au premier lancement
    if Equipement.query.count() == 0:
        db.session.add_all([
            # Mes Appareils Photo (catégories Amateur, Amateur sérieux, Professionnel) [cite: 26]
            Equipement(type_equip='photo', categorie='Amateur', marque='Canon', modele='EOS R50', date_sortie='2023', score=4, image_path='camera debutant.jpg', resume='Un appareil léger parfait pour s\'initier.'),
            Equipement(type_equip='photo', categorie='Amateur sérieux', marque='Nikon', modele='D3400', date_sortie='2020', score=5, image_path='nikon-d3400-camera-for-amateur-photographer.jpg', resume='Idéal pour capturer la Voie Lactée avec précision.'),
            Equipement(type_equip='photo', categorie='Professionnel', marque='Sony', modele='A7R V', date_sortie='2022', score=5, image_path='pro.jpg', resume='La référence pour les photographies de ciel profond.'),
            # Mes Téléscopes (catégories Enfants, Automatisés, Complets) [cite: 27]
            Equipement(type_equip='telescope', categorie='Téléscopes pour enfants', marque='Celestron', modele='FirstScope', date_sortie='2019', score=3, image_path='telescop enfant.jpg', resume='Idéal pour une première approche de la Lune.'),
            Equipement(type_equip='telescope', categorie='Automatisés', marque='Sky-Watcher', modele='GoTo Wifi', date_sortie='2021', score=5, image_path='telescopio-automatico.jpg', resume='Recherche automatique des objets célestes via smartphone.'),
            Equipement(type_equip='telescope', categorie='Téléscopes complets', marque='Orion', modele='SkyQuest 254', date_sortie='2020', score=5, image_path='telescop_pro.jpg', resume='Un instrument complet pour voir les nébuleuses en détail.')
        ])
    
    if Photographie.query.count() == 0:
        db.session.add_all([
            Photographie(titre='L\'Univers Quantique', url_image='univers quantique.jpg'),
            Photographie(titre='Ma Station de Contrôle', url_image='telescopio-automatico.jpg')
        ])
    db.session.commit()

# --- ROUTES D'AUTHENTIFICATION (10 points) --- [cite: 16]

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Je hache le mot de passe avant de l'enregistrer [cite: 19]
        hashed = generate_password_hash(request.form['password'])
        nouveau_user = User(username=request.form['username'], password_hash=hashed)
        db.session.add(nouveau_user)
        db.session.commit()
        flash('Inscription réussie !')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
        flash('Identifiants incorrects.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ROUTES DE CONTENU (10 points) --- [cite: 23, 24]

@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    return redirect(url_for('appareils_photo'))

@app.route('/appareils_photo')
def appareils_photo():
    if 'user_id' not in session: return redirect(url_for('login'))
    data = Equipement.query.filter_by(type_equip='photo').all()
    return render_template('appareils.html', equipements=data)

@app.route('/telescopes')
def telescopes():
    if 'user_id' not in session: return redirect(url_for('login'))
    data = Equipement.query.filter_by(type_equip='telescope').all()
    return render_template('telescopes.html', equipements=data)

@app.route('/photographies')
def photographies():
    if 'user_id' not in session: return redirect(url_for('login'))
    photos_galerie = Photographie.query.all()
    return render_template('photographies.html', photos=photos_galerie)

# Route Bonus : Détails techniques 
@app.route('/equipement/<int:id>')
def detail_equipement(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    mon_item = Equipement.query.get_or_404(id)
    return render_template('detail.html', item=mon_item)

# --- ROUTES BONUS (Actualités & Forum) --- [cite: 44, 46]

@app.route('/actualites')
def actualites():
    if 'user_id' not in session: return redirect(url_for('login'))
    actus = Actualite.query.all()
    return render_template('actualites.html', actus=actus)

@app.route('/ajouter_actu', methods=['POST'])
def ajouter_actu():
    msg = request.form.get('message')
    nouvelle_actu = Actualite(message=msg)
    db.session.add(nouvelle_actu)
    db.session.commit()
    # Envoi en temps réel via WebSockets 
    socketio.emit('nouvelle_actu_event', {'msg': msg})
    return redirect(url_for('actualites'))

@app.route('/forum')
def forum():
    if 'user_id' not in session: return redirect(url_for('login'))
    topics = Topic.query.all()
    return render_template('forum.html', topics=topics)

# Lancement de l'application avec support WebSocket 
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')