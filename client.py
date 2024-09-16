import argparse
import socket
import ssl
import json

def load_word_list():
    with open('words.txt', 'r') as file:
        words = [line.strip() for line in file]
    return words

wordList = load_word_list()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', type=int, default=None)
    parser.add_argument('-s', action='store_true')
    parser.add_argument('hostname', type=str)
    parser.add_argument('username', type=str)
    return parser.parse_args()

def create_socket(hostname, port, use_tls):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if use_tls:
        context = ssl.create_default_context()
        wrapped_socket = context.wrap_socket(sock, server_hostname=hostname)
        wrapped_socket.connect((hostname, port))
        return wrapped_socket
    else:
        sock.connect((hostname, port))
        return sock

def send_message(sock, message):
    sock.sendall((message + '\n').encode('utf-8'))

def receive_message(sock):
    response = b''
    while not response.endswith(b'\n'):
        response += sock.recv(4096)
    return json.loads(response.decode('utf-8').strip())

def get_marks(guess, correctWord):
    marks = [0] * 5
    guessCount = {}
    correctCount = {}

    # mark matches
    for i, (gChar, cChar) in enumerate(zip(guess, correctWord)):
        if gChar == cChar:
            marks[i] = 2
        else:
            guessCount[gChar] = guessCount.get(gChar, 0) + 1
            correctCount[cChar] = correctCount.get(cChar, 0) + 1

    # mark wrong guesses
    for i, (gChar, cChar) in enumerate(zip(guess, correctWord)):
        if marks[i] == 0:
            if gChar in correctCount and correctCount[gChar] > 0:
                marks[i] = 1
                correctCount[gChar] -= 1

    return marks

def filter_word_list(guesses, wordList):
    # checks for words with same marks
    for guess in guesses:
        word, marks = guess["word"], guess["marks"]
        newWordList = []

        for candidate in wordList:
            valid = True
            candidateMarks = get_marks(word, candidate)

            if candidateMarks != marks:
                valid = False

            if valid:
                newWordList.append(candidate)

        wordList = newWordList

        if not wordList:
            break

    return wordList

def play_game(sock, username):
    # hello mesage
    helloMessage = json.dumps({"type": "hello", "northeastern_username": username})
    send_message(sock, helloMessage)

    # start message
    response = receive_message(sock)
    gameId = response['id']

    remainingWordList = wordList.copy()
    guesses = []

    while True:
        if not remainingWordList:
            break

        # make guess
        guessWord = remainingWordList[0]
        guessMsg = json.dumps({"type": "guess", "id": gameId, "word": guessWord})
        send_message(sock, guessMsg)

        response = receive_message(sock)

        if response['type'] == 'bye':
            print(response['flag'])
            break
         # update guesses and try again
        elif response['type'] == 'retry':
            guessesFromServer = response["guesses"]
            guessMarks = next((g["marks"] for g in guessesFromServer 
            if g["word"] == guessWord), None)
            if guessMarks:
                if not any(g["word"] == guessWord for g in guesses):
                    guesses.append({"word": guessWord, "marks": guessMarks})

            remainingWordList = filter_word_list(guesses, remainingWordList)
        else:
            break

def main():
    args = parse_args()
    port = args.p or (27994 if args.s else 27993)

    sock = create_socket(args.hostname, port, args.s)

    play_game(sock, args.username)


main()