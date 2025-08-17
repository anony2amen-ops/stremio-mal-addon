from bottle import Bottle,```sponse
import json

# Create```ttle app
app = Bottle()

@app.route('/')
def home():
    response.headers['Access-Control-Allow-Origin'] = '*'
    return "<h1>🍶 Bottle Test - IT```RKS!</h1><p><a href='/manifest```on'>Test Manifest</a>```>"

@app.route('/manifest.json')
def manifest():
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.content```pe = 'application/json'```  return json.dumps({"id":"```t","name":"Bottle Test","version":"```.0","resources":["catalog"],"types":["movie"],"catal```":[{"type":"movie","id":"test","name":"Test"}]})

# Export```r Vercel
application = app
