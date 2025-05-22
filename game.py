from flask import Flask, request, render_template_string, redirect, url_for, session
import random
import threading
import webbrowser

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for sessions

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Rock Paper Scissors</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; }
        button.choice-btn { font-size: 18px; margin: 5px; padding: 10px 20px; cursor: pointer; }
        #result { margin-top: 20px; font-size: 20px; font-weight: bold; }
        #scoreboard { margin-top: 20px; }
        #scoreboard div { margin-bottom: 5px; }
        #timer { font-size: 18px; color: red; margin-top: 10px; }
        .animation {
            font-size: 40px;
            height: 50px;
            margin-top: 10px;
            animation-name: shake;
            animation-duration: 0.5s;
            animation-iteration-count: 3;
        }
        @keyframes shake {
            0% { transform: translate(1px, 1px) rotate(0deg); }
            25% { transform: translate(-1px, -2px) rotate(-1deg); }
            50% { transform: translate(-3px, 0px) rotate(1deg); }
            75% { transform: translate(3px, 2px) rotate(0deg); }
            100% { transform: translate(1px, -1px) rotate(1deg); }
        }
    </style>
</head>
<body>

    <h2>Rock Paper Scissors</h2>

    {% if multiplayer and player_turn == 1 %}
        <p><strong>Player 1's Turn:</strong> Choose your move!</p>
    {% elif multiplayer and player_turn == 2 %}
        <p><strong>Player 2's Turn:</strong> Choose your move!</p>
    {% endif %}

    <div id="timer"></div>

    <form method="POST" id="choiceForm">
        <button type="submit" name="choice" value="Rock" class="choice-btn">✊ Rock</button>
        <button type="submit" name="choice" value="Paper" class="choice-btn">✋ Paper</button>
        <button type="submit" name="choice" value="Scissors" class="choice-btn">✌️ Scissors</button>
    </form>

    {% if result %}
        <div id="result" class="animation">{{ result }}</div>
        <p>Your Choice: {{ user_choice }}</p>
        <p>Computer Choice: {{ computer_choice }}</p>
    {% endif %}

    {% if multiplayer and both_choices %}
        <div id="result" class="animation">{{ multiplayer_result }}</div>
        <p>Player 1 Choice: {{ player1_choice }}</p>
        <p>Player 2 Choice: {{ player2_choice }}</p>
    {% endif %}

    <div id="scoreboard">
        <h3>Scoreboard</h3>
        <div>Player Wins: {{ score['wins'] }}</div>
        <div>Computer Wins: {{ score['losses'] }}</div>
        <div>Ties: {{ score['ties'] }}</div>
        {% if multiplayer %}
            <div>Player 1 Wins: {{ mp_score['player1_wins'] }}</div>
            <div>Player 2 Wins: {{ mp_score['player2_wins'] }}</div>
            <div>Draws: {{ mp_score['draws'] }}</div>
        {% endif %}
    </div>

    <form method="POST" action="{{ url_for('reset') }}">
        <button type="submit">Reset Game</button>
    </form>

    <form method="POST" action="{{ url_for('toggle_multiplayer') }}">
        {% if multiplayer %}
            <button type="submit">Switch to Single Player</button>
        {% else %}
            <button type="submit">Switch to Multiplayer</button>
        {% endif %}
    </form>

    <audio id="clickSound" src="https://www.soundjay.com/buttons/sounds/button-16.mp3"></audio>
    <audio id="winSound" src="https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3"></audio>
    <audio id="loseSound" src="https://www.soundjay.com/misc/sounds/fail-buzzer-01.mp3"></audio>
    <audio id="tieSound" src="https://www.soundjay.com/misc/sounds/bell-ringing-04.mp3"></audio>

    <script>
        // Timer countdown
        let timeLeft = 10;  // seconds
        let timerElem = document.getElementById('timer');
        let interval = null;

        function updateTimer() {
            if(timeLeft <= 0) {
                clearInterval(interval);
                timerElem.innerText = "Time's up! You missed your turn.";
                // Auto submit form with no choice to skip turn
                document.getElementById('choiceForm').submit();
            } else {
                timerElem.innerText = "Time remaining: " + timeLeft + " seconds";
                timeLeft -= 1;
            }
        }

        interval = setInterval(updateTimer, 1000);

        // Play sound effects on button click
        document.querySelectorAll('button.choice-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('clickSound').play();
            });
        });

        // Play sound on result display
        {% if result %}
            {% if 'win' in result.lower() %}
                document.getElementById('winSound').play();
            {% elif 'lose' in result.lower() %}
                document.getElementById('loseSound').play();
            {% elif 'tie' in result.lower() %}
                document.getElementById('tieSound').play();
            {% endif %}
        {% elif multiplayer and both_choices %}
            {% if 'win' in multiplayer_result.lower() %}
                document.getElementById('winSound').play();
            {% elif 'draw' in multiplayer_result.lower() %}
                document.getElementById('tieSound').play();
            {% endif %}
        {% endif %}
    </script>

</body>
</html>
'''

def decide_winner(user, computer):
    if user == computer:
        return "It's a tie!"
    elif (user == 'Rock' and computer == 'Scissors') or \
         (user == 'Paper' and computer == 'Rock') or \
         (user == 'Scissors' and computer == 'Paper'):
        return "You win!"
    else:
        return "Computer wins!"

def decide_winner_multiplayer(p1, p2):
    if p1 == p2:
        return "It's a draw!"
    elif (p1 == 'Rock' and p2 == 'Scissors') or \
         (p1 == 'Paper' and p2 == 'Rock') or \
         (p1 == 'Scissors' and p2 == 'Paper'):
        return "Player 1 wins!"
    else:
        return "Player 2 wins!"

@app.route('/', methods=['GET', 'POST'])
def index():
    multiplayer = session.get('multiplayer', False)
    score = session.get('score', {'wins':0,'losses':0,'ties':0})
    mp_score = session.get('mp_score', {'player1_wins':0,'player2_wins':0,'draws':0})

    result = None
    user_choice = None
    computer_choice = None
    multiplayer_result = None
    player1_choice = None
    player2_choice = None
    both_choices = False
    player_turn = session.get('player_turn', 1)

    if request.method == 'POST':
        choice = request.form.get('choice')

        if multiplayer:
            if player_turn == 1:
                # Save player 1 choice and switch turn
                session['player1_choice'] = choice
                session['player_turn'] = 2
                return redirect(url_for('index'))

            elif player_turn == 2:
                # Get player 2 choice and decide winner
                player1_choice = session.get('player1_choice')
                player2_choice = choice
                multiplayer_result = decide_winner_multiplayer(player1_choice, player2_choice)

                # Update multiplayer scores
                if "Player 1 wins" in multiplayer_result:
                    mp_score['player1_wins'] += 1
                elif "Player 2 wins" in multiplayer_result:
                    mp_score['player2_wins'] += 1
                else:
                    mp_score['draws'] += 1

                session['mp_score'] = mp_score
                both_choices = True
                session['player_turn'] = 1  # Reset turn for next round
                session.pop('player1_choice', None)

        else:
            # Single player mode: play against computer
            user_choice = choice
            computer_choice = random.choice(['Rock', 'Paper', 'Scissors'])
            result = decide_winner(user_choice, computer_choice)

            # Update scores
            if "win" in result.lower():
                score['wins'] += 1
            elif "computer wins" in result.lower():
                score['losses'] += 1
            else:
                score['ties'] += 1

            session['score'] = score

    # For multiplayer show choices from session if available
    if multiplayer:
        player_turn = session.get('player_turn', 1)
        player1_choice = session.get('player1_choice')
        mp_score = session.get('mp_score', {'player1_wins':0,'player2_wins':0,'draws':0})

    return render_template_string(HTML,
                                  result=result,
                                  user_choice=user_choice,
                                  computer_choice=computer_choice,
                                  score=score,
                                  multiplayer=multiplayer,
                                  player_turn=player_turn,
                                  multiplayer_result=multiplayer_result,
                                  player1_choice=player1_choice,
                                  player2_choice=player2_choice,
                                  both_choices=both_choices,
                                  mp_score=mp_score)

@app.route('/reset', methods=['POST'])
def reset():
    session.pop('score', None)
    session.pop('mp_score', None)
    session.pop('player_turn', None)
    session.pop('player1_choice', None)
    return redirect(url_for('index'))

@app.route('/toggle_multiplayer', methods=['POST'])
def toggle_multiplayer():
    current = session.get('multiplayer', False)
    session['multiplayer'] = not current
    # Reset everything when toggling modes
    session.pop('score', None)
    session.pop('mp_score', None)
    session.pop('player_turn', None)
    session.pop('player1_choice', None)
    return redirect(url_for('index'))

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1.0, open_browser).start()
    app.run(debug=True)
