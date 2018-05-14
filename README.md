This is a slack bot, so you will need a slack bot API key.  This also needs to be available at a location with https.

First:
```
docker pull micahscopes/bubbles
```

Then, to expose this application at port 9876 on your host, you could do:
```
docker run --name bubbles -e "BUBBLES_BOT_TOKEN='xoxb-123456789999-ABC123ABC123ABC123ABC123'" -p 9876:8080 micahscopes/bubbles
```
