from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ LINE Bot Server is Running on Render!"

if __name__ == '__main__':
    app.run()
