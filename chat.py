from aiohttp import web
import socketio
import pymongo
import aiohttp_cors
from bson import json_util, ObjectId
import json
from Using_toxic_detection import get_pred_string
from docxtpl import DocxTemplate, InlineImage
import requests
import datetime
import base64

# import Using_toxic_detection from 'Using_toxic_detection.py'
routes = web.RouteTableDef()

# print(get_pred_string("Fuck you, bitch"))

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

conn = pymongo.MongoClient("localhost", 27017)
db = conn['homechat']
# coll = db.users.find_one({"login": "qwe"})
# a = db.users.save({"x": 10})
# print(a)
# if coll:
#     print("Found")
# else: 
#     print("bads")

# print coll.find({"login": "qwe"})
# for men in coll.find():
#     print(men)

@sio.on("writing")
async def writing(sid, message):
    check = True
    check_toxic = get_pred_string(message['value'])
    for i in check_toxic[0]:
        print(i)
        if i > 0.8:
            check = False
    if check != True:
        message['bad'] = True
    await sio.emit("writing", message)

@sio.on('message')
async def print_message(sid, message):
    check = True
    check_toxic = get_pred_string(message['text'])
    for i in check_toxic[0]:
        print(i)
        if i > 0.8:
            check = False
    if check != True:
        tmp = db.users.find_one({"nick": message['name']})
        print(tmp['opacity'])
        if tmp['opacity'] > 0:
            message['opacity'] = 0.4
            db.users.update_one({"nick": message['name']}, {"$set": {"opacity": 0}})
        else:
         message['opacity'] = 0  
    else:
        message['opacity'] = 1
    print(message)
    await sio.emit('message', message)
    db[message['chat']].insert_one(message)

async def index(request):
    res = {"q": "qqq", "a": "aaa"}
    return web.json_response(res)
    # return web.Response(text={"hello": "noup"})

async def reg(request):
    data = await request.json()
    data['nick'] = data['first_name'] + " " + data['sur_name'][0] + ". - №" + data['flat']
    data['opacity'] = 1
    print(data)
    user = db.users.find_one({
        "home": data['home'],
        "flat": data['flat'],
        "status": data['status']
    })
    is_reg = False
    if(user):
        is_reg = True
    else:
        db.users.insert_one(data)
        # db.users.insert_one({
        #     "first_name": request.rel_url.query['first_name'],
        #     "password": request.rel_url.query['password'],
        #     "sur_name": request.rel_url.query['sur_name'],
        #     "home": request.rel_url.query['home'],
        #     "flat": int(float(request.rel_url.query['flat'])),
        #     "status": request.rel_url.query['status'],
            # "nick": request.rel_url.query['first_name'] + " " + request.rel_url.query['sur_name'][0] + ". - №" + request.rel_url.query['flat'],
        #     "opacity": 1
        # })
    return web.json_response({"type": is_reg})

async def login(request):
    user = db.users.find_one({
        "home": request.rel_url.query['home'],
        "flat": request.rel_url.query['flat'],
        "password": request.rel_url.query['password'],
    })
    print(user['nick'])
    logined = False
    print(user['home'])
    if(user):
        logined = True
        return web.json_response({"type": logined, "nick": user['nick'], "chat": user['home']})
    else:
        return web.json_response({"type": logined})

async def getMessages(req):
    return web.json_response(json.loads(json_util.dumps(list(db[req.rel_url.query['chat']].find()))))

async def addAd(req):
    data = await req.json()
    print(data)
    db.ads.insert_one(data)
    return web.json_response({"type": "ok"})

async def getAds(req):
    return web.json_response(json.loads(json_util.dumps(list(db.ads.find()))))

async def likeAd(req):
    tmp = db.ads.find_one({"_id": ObjectId(req.rel_url.query['id'])})
    if tmp.marks.index(req.rel_url.query['nick']):
        return web.json_response({"type": "bad"})
    else:
        db.ads.update_one({
            "_id": ObjectId(req.rel_url.query['id'])
        }, { "$inc": { "likes": +1}})
        return web.json_response({"type": "ok"})

    
async def dislikeAd(req):
    tmp = db.ads.find_one({"_id": ObjectId(req.rel_url.query['id'])})
    if tmp.marks.index(req.rel_url.query['nick']):
        return web.json_response({"type": "bad"})
    else:
        db.ads.update_one({
            "_id": ObjectId(req.rel_url.query['id'])
        }, { "$inc": { "dislikes": +1}})
        return web.json_response({"type": "ok"})

    
async def repost(req):
    ad = db.ads.find_one({"_id": ObjectId(req.rel_url.query['id'])})
    ad['nick'] = req.rel_url.query['nick']
    await sio.emit('message', ad)
    db[req.rel_url.query['chat']].insert_one(ad)
    return web.json_response({"type": "ok"})

async def sendEmail(req):
    user = db.users.find_one({"nick": req.rel_url.query['nick']})
    doc = DocxTemplate("word.docx")
    today = datetime.datetime.today()
    # imgdata = user['sign']
    # imgdata = base64.b64decode(imgdata)
    # img = io.StringIO(user['sign'])
    image_data = user['sign'].split("data:image/jpeg;base64,")
    with open("image.png", "wb") as fh:
        fh.write(base64.b64decode(image_data[1]))
    image = InlineImage(doc, "image.png")
    context = { 'name' :  user['first_name']+" "+user['sur_name'], "flat": user['flat'], "date": today.strftime("%m.%d.%Y"), "sign": image }
    doc.render(context)
    doc.save("generated_doc.docx")

    headers = {
        'X-RapidAPI-Host': 'upload.p.rapidapi.com',
        'X-RapidAPI-Key': '9608457de2msh39bd68eedabbaa1p1ab241jsn577c4aa2aac8',
    }

    files = {
        'UPLOADCARE_STORE': (None, '1'),
        'file': ('generated_doc.docx', open('generated_doc.docx', 'rb')),
        'UPLOADCARE_PUB_KEY': (None, 'demopublickey'),
    }

    response = requests.post('https://upload.p.rapidapi.com/base/', headers=headers, files=files)

    data = json.loads(response.content)

    print(data['file'])

    url = "https://fapimail.p.rapidapi.com/email/send"

    payload = "{\"recipient\":\"aplinxy9plin@gmail.com\",\"sender\":\"aplinxy9plin@gmail.com\",\"subject\":\"Problem with my home\",\"message\":\"https://ucarecdn.com/"+data['file']+"/\"}"
    headers = {
        'content-type': "application/json",
        'x-rapidapi-host': "fapimail.p.rapidapi.com",
        'x-rapidapi-key': "9608457de2msh39bd68eedabbaa1p1ab241jsn577c4aa2aac8"
        }

    response = requests.request("POST", url, data=payload, headers=headers)

    print(response.text)
    return web.json_response({"type": "ok", "url": "https://ucarecdn.com/"+data['file']+"/"})

async def markStat(req):
    db.stats.insert_one({
        "message": req.rel_url.query['message'],
        "type": req.rel_url.query['type']
    })
    return web.json_response({"type": "ok"})

async def test(req):
    a = await req.json()
    print(a['test'])
    # post = await request.post()
    # email = post.get('test')   #  because it MultiDict 
    # logging.warning(post)       #  see post details
    # logging.warning(email)      #  shows value "some@email.com" 

    # json = await request.text() #
    # logging.warning(json)       #  shows json if it was ajax post request
    return web.json_response({"type": "logined"})

# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
})
cors.add(app.router.add_get('/', index))
cors.add(app.router.add_post('/reg', reg))
cors.add(app.router.add_get('/login', login))
cors.add(app.router.add_get('/getMessages', getMessages))
cors.add(app.router.add_get('/getAds', getAds))
cors.add(app.router.add_get('/likeAd', likeAd))
cors.add(app.router.add_get('/dislikeAd', dislikeAd))
cors.add(app.router.add_get('/repost', repost))
cors.add(app.router.add_get('/sendEmail', sendEmail))
cors.add(app.router.add_get('/markStat', markStat))
cors.add(app.router.add_post('/test', test))
cors.add(app.router.add_post('/addAd', addAd))
# Configure CORS on all routes.
# for route in list(app.router.routes()):
#     cors.add(route)

# We kick off our server
if __name__ == '__main__':
    web.run_app(app)