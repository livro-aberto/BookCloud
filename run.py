from application import app

app.config.from_object(__name__)
app.run(debug=True)
