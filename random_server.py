from flask import Flask
from markupsafe import escape
from flask import request
import random


app = Flask(__name__)
merkit = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
          "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
          "0", "1", "2", "3", "4", "5", "6", "7", "8", "9" ]



@app.route('/random/<int:post_id>')
def random_number(post_id):
    pituus = post_id
    salasana = ""
    for i in range(pituus):
        salasana += random.choice(merkit)
    return f"{escape(salasana)}"


@app.route('/make/<string:thing>')
def make_thing(thing):
    muokattu = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
          "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
          "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "_", "=", "+" ]
    
    for i in range(len(thing)):
        if thing[i] == "a":
            viimeinen_alkio = muokattu.pop()
            muokattu.insert(0, viimeinen_alkio)
        if thing[i] == "b":
            eka_alkio = muokattu.pop(1)
            muokattu.append(eka_alkio)
        if thing[i] == "c":
            eka_alkio = muokattu.pop(2)
            muokattu.append(eka_alkio)
        if thing[i] == "d":
            viimeinen_alkio = muokattu.pop(3)
            muokattu.insert(0, viimeinen_alkio)
        
    
    return f"You made a {escape(thing)}!"






if __name__ == "__main__":
    # Aja palvelin kuunnellen kaikkia IP-osoitteita portissa 50
    app.run(host='0.0.0.0', port=6969)




'''
@app.route('/')
def index():
    return 'Index Page'

@app.route('/hello')
def hello():
    return "<a>Hello, World!</a>"

@app.route("/htm")
def htm():
    name = request.args.get("name", "Flask")
    return f"Hell, {escape(name)}!"


@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return f'User {escape(username)}'

@app.route('/post/<int:post_id>')
def show_post(post_id):
    # show the post with the given id, the id is an integer
    return f'Post {post_id}'

@app.route('/path/<path:subpath>')
def show_subpath(subpath):
    # show the subpath after /path/
    return f'Subpath {escape(subpath)}'
'''
