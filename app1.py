from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database1 import db, User, Item, Message
import os
@app.route("/ping")
def ping():
    return "OK"
from datetime import datetime

app = Flask(__name__)

# ========== DATABASE CONFIGURATION (WORKS BOTH LOCALLY & ON RENDER) ==========
# Use PostgreSQL on Render (if DATABASE_URL exists), otherwise use SQLite locally
if os.environ.get('DATABASE_URL'):
    database_url = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("Using PostgreSQL database (Render)")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lostfound.db'
    print("Using SQLite database (Local)")
# =============================================================================

app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login1'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created: admin/admin123")

# ==================== PUBLIC ROUTES ====================

@app.route('/landing')
def landing():
    return render_template('landing1.html')

@app.route('/login1', methods=['GET', 'POST'])
def login1():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('choose1'))
        flash('Invalid credentials')
    return render_template('login1.html')

@app.route('/register1', methods=['GET', 'POST'])
def register1():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username exists')
            return redirect(url_for('register1'))
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login1'))
    return render_template('register1.html')

# ==================== PROTECTED ROUTES ====================

@app.route('/')
@login_required
def index1():
    return redirect(url_for('choose1'))

@app.route('/choose1')
@login_required
def choose1():
    return render_template('choose1.html')

@app.route('/my_items1')
@login_required
def my_items1():
    return render_template('my_items1.html')

@app.route('/my_messages1')
@login_required
def my_messages1():
    return render_template('my_messages1.html')

@app.route('/lost_items1')
@login_required
def lost_items1():
    return render_template('lost_items1.html')

@app.route('/found_items1')
@login_required
def found_items1():
    return render_template('found_items1.html')

@app.route('/report_lost1')
@login_required
def report_lost1():
    return render_template('report_lost1.html')

@app.route('/report_found1')
@login_required
def report_found1():
    return render_template('report_found1.html')

@app.route('/item_detail1/<int:item_id>')
@login_required
def item_detail1(item_id):
    return render_template('item_detail1.html', item_id=item_id)

@app.route('/logout1')
@login_required
def logout1():
    logout_user()
    return redirect(url_for('landing'))

# ==================== API ROUTES ====================

@app.route('/api/me')
@login_required
def get_current_user():
    unread_count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role,
        'unread_count': unread_count
    })

@app.route('/api/my_items')
@login_required
def get_my_items():
    items = Item.query.filter_by(user_id=current_user.id).order_by(Item.created_at.desc()).all()
    return jsonify([{
        'id': i.id,
        'title': i.title,
        'description': i.description,
        'location': i.location,
        'type': i.type,
        'date': i.date_occurred,
        'image_path': i.image_path,
        'created_at': i.created_at.isoformat(),
        'message_count': Message.query.filter_by(item_id=i.id).count()
    } for i in items])

@app.route('/api/my_conversations')
@login_required
def get_my_conversations():
    conversations = {}
    
    sent_messages = Message.query.filter_by(sender_id=current_user.id).all()
    for msg in sent_messages:
        key = f"{msg.receiver_id}_{msg.item_id}"
        if key not in conversations:
            item = Item.query.get(msg.item_id)
            other_user = User.query.get(msg.receiver_id)
            conversations[key] = {
                'other_user_id': msg.receiver_id,
                'other_user_name': other_user.username,
                'item_id': msg.item_id,
                'item_title': item.title,
                'last_message': msg.content,
                'last_message_time': msg.created_at.isoformat(),
                'unread_count': 0,
                'is_from_me': True
            }
        else:
            if msg.created_at > datetime.fromisoformat(conversations[key]['last_message_time']):
                conversations[key]['last_message'] = msg.content
                conversations[key]['last_message_time'] = msg.created_at.isoformat()
    
    received_messages = Message.query.filter_by(receiver_id=current_user.id).all()
    for msg in received_messages:
        key = f"{msg.sender_id}_{msg.item_id}"
        if key not in conversations:
            item = Item.query.get(msg.item_id)
            other_user = User.query.get(msg.sender_id)
            conversations[key] = {
                'other_user_id': msg.sender_id,
                'other_user_name': other_user.username,
                'item_id': msg.item_id,
                'item_title': item.title,
                'last_message': msg.content,
                'last_message_time': msg.created_at.isoformat(),
                'unread_count': 1 if not msg.is_read else 0,
                'is_from_me': False
            }
        else:
            conversations[key]['unread_count'] += 1 if not msg.is_read else 0
            if msg.created_at > datetime.fromisoformat(conversations[key]['last_message_time']):
                conversations[key]['last_message'] = msg.content
                conversations[key]['last_message_time'] = msg.created_at.isoformat()
                conversations[key]['is_from_me'] = False
    
    return jsonify(list(conversations.values()))

@app.route('/api/items', methods=['GET', 'POST'])
@login_required
def items():
    if request.method == 'POST':
        item_type = request.form['type']
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        date_occurred = request.form['date_occurred']
        
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = secure_filename(file.filename)
                filename = f"{timestamp}_{safe_filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_path = f"uploads/{filename}"
        
        item = Item(
            user_id=current_user.id,
            type=item_type,
            title=title,
            description=description,
            location=location,
            date_occurred=date_occurred,
            image_path=image_path
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'id': item.id})
    
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    location_filter = request.args.get('location', '')
    
    query = Item.query
    if search:
        query = query.filter(Item.title.contains(search) | Item.description.contains(search))
    if type_filter:
        query = query.filter(Item.type == type_filter)
    if location_filter:
        query = query.filter(Item.location.contains(location_filter))
    
    items = query.order_by(Item.created_at.desc()).all()
    return jsonify([{
        'id': i.id,
        'title': i.title,
        'description': i.description,
        'location': i.location,
        'type': i.type,
        'date': i.date_occurred,
        'owner_name': i.owner.username,
        'owner_id': i.user_id,
        'image_path': i.image_path,
        'created_at': i.created_at.isoformat()
    } for i in items])

@app.route('/api/items/<int:item_id>')
@login_required
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify({
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'location': item.location,
        'type': item.type,
        'date': item.date_occurred,
        'owner_name': item.owner.username,
        'owner_id': item.user_id,
        'image_path': item.image_path,
        'created_at': item.created_at.isoformat()
    })

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id and current_user.role != 'admin':
        return jsonify({'error': 'Permission denied'}), 403
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/items/<int:item_id>/report', methods=['POST'])
@login_required
def report_item(item_id):
    item = Item.query.get_or_404(item_id)
    item.is_reported = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/messages', methods=['GET', 'POST'])
@login_required
def messages():
    if request.method == 'POST':
        data = request.json
        message = Message(
            sender_id=current_user.id,
            receiver_id=data['receiver_id'],
            item_id=data['item_id'],
            content=data['content'],
            is_read=False
        )
        db.session.add(message)
        db.session.commit()
        return jsonify({'success': True})
    
    other_user = request.args.get('other_user')
    item_id = request.args.get('item_id')
    
    messages_to_update = Message.query.filter(
        Message.sender_id == other_user,
        Message.receiver_id == current_user.id,
        Message.item_id == item_id,
        Message.is_read == False
    ).all()
    
    for msg in messages_to_update:
        msg.is_read = True
    db.session.commit()
    
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == other_user)) |
        ((Message.sender_id == other_user) & (Message.receiver_id == current_user.id))
    ).filter(Message.item_id == item_id).order_by(Message.created_at).all()
    
    return jsonify([{
        'id': m.id,
        'sender_id': m.sender_id,
        'receiver_id': m.receiver_id,
        'content': m.content,
        'sender_name': m.sender.username,
        'is_read': m.is_read,
        'created_at': m.created_at.isoformat()
    } for m in messages])

# ==================== RUN THE APP ====================
if __name__ == '__main__':
    # For local development only
    app.run(debug=True, port=5001)

# For production (Render uses gunicorn, not this block)
# The 'app' object is what Render looks for
