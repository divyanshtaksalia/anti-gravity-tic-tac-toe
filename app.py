import json
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# JSON file se data read karne ka function
def load_game_data():
    try:
        with open('data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"games_played": 0, "scores": {"player": 0, "computer": 0}}

# JSON file mein data save karne ka function
def save_game_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)
import random

def get_best_move(board, level):
    empty_cells = [i for i, cell in enumerate(board) if cell == ""]
    
    # 1. EASY LEVEL: Bilkul random move
    if level == "easy":
        return random.choice(empty_cells) if empty_cells else None

    # 2. MEDIUM LEVEL: Kabhi sahi move, kabhi random
    if level == "medium":
        if random.random() > 0.5:
            return minimax(board, "O")['index'] # "O" computer hai
        else:
            return random.choice(empty_cells)

    # 3. HARD LEVEL: Humesha best move (Minimax Algorithm)
    if level == "hard":
        move = minimax(board, "O")
        return move['index']

def minimax(new_board, player):
    # Khali jagah dhundna
    avail_spots = [i for i, cell in enumerate(new_board) if cell == ""]

    # Jeetne ya haarne ki conditions
    if check_win(new_board, "X"): return {'score': -10}
    elif check_win(new_board, "O"): return {'score': 10}
    elif len(avail_spots) == 0: return {'score': 0}

    moves = []
    for i in avail_spots:
        move = {}
        move['index'] = i
        new_board[i] = player

        if player == "O":
            result = minimax(new_board, "X")
            move['score'] = result['score']
        else:
            result = minimax(new_board, "O")
            move['score'] = result['score']

        new_board[i] = ""
        moves.append(move)

    # Best move choose karna
    if player == "O":
        best_score = -10000
        for m in moves:
            if m['score'] > best_score:
                best_score = m['score']
                best_move = m
    else:
        best_score = 10000
        for m in moves:
            if m['score'] < best_score:
                best_score = m['score']
                best_move = m
    return best_move

def check_win(b, p):
    # Winning combinations (rows, cols, diagonals)
    return ((b[0]==p and b[1]==p and b[2]==p) or
            (b[3]==p and b[4]==p and b[5]==p) or
            (b[6]==p and b[7]==p and b[8]==p) or
            (b[0]==p and b[3]==p and b[6]==p) or
            (b[1]==p and b[4]==p and b[7]==p) or
            (b[2]==p and b[5]==p and b[8]==p) or
            (b[0]==p and b[4]==p and b[8]==p) or
            (b[2]==p and b[4]==p and b[6]==p))

@app.route('/')
def index():
    return render_template('index.html') # Ye aapki HTML file load karega

@app.route('/get_move', methods=['POST'])
def ai_move():
    data = request.json
    board = data.get('board') # Ex: ["X", "", "O", ...]
    level = data.get('level') # "easy", "medium", "hard"
    
    move_index = get_best_move(board, level)
    return jsonify({"move": move_index})

# Jab koi player online connect hoga
@socketio.on('connect')
def handle_connect():
    print('Ek player connect ho gaya!')

from flask_socketio import join_room, leave_room

# Online game storage (Temporary memory mein)
online_rooms = {}

@socketio.on('create_room')
def on_create(data):
    room = data['room']
    join_room(room)
    online_rooms[room] = {"board": [""] * 9, "players": [request.sid], "turn": "X"}
    emit('room_created', {'room': room})

@socketio.on('join_room')
def on_join(data):
    room = data['room']
    # Check karein ki room exist karta hai
    if room in online_rooms:
        if len(online_rooms[room]["players"]) < 2:
            join_room(room)
            online_rooms[room]["players"].append(request.sid)
            
            # 1. Sirf join karne wale ko symbol bhejein
            emit('game_start', {'symbol': 'O'}, room=request.sid)
            
            # 2. Poore room (creator + joiner) ko batayein ki game shuru ho gaya hai
            emit('player_joined', {'msg': 'Friend joined!'}, room=room)
        else:
            emit('error', {'msg': 'Room full hai!'})
    else:
        emit('error', {'msg': 'Room exist nahi karta!'})
@app.route('/save_score', methods=['POST'])
def save_score():
    data = request.json
    winner = data.get('winner')
    game_data = load_game_data()
    
    game_data['games_played'] += 1
    if winner == 'X':
        game_data['scores']['player'] += 1
    else:
        game_data['scores']['computer'] += 1
        
    save_game_data(game_data)
    return jsonify({"status": "success"})

@socketio.on('make_online_move')
def on_move(data):
    room = data['room']
    index = data['index']
    symbol = data['symbol']
    
    # Board update aur dusre player ko move bhejna
    online_rooms[room]["board"][index] = symbol
    emit('move_made', {'index': index, 'symbol': symbol}, room=room, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True)