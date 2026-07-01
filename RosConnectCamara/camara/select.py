import requests
from requests.auth import HTTPDigestAuth

ip = "192.168.51.251"
user = "admin"
pwd = "Gsydj666"

url = f"http://{ip}/ISAPI/Event/triggers/notifications/AudioAlarm/customAudioInfo?format=json"

r = requests.get(
    url,
    auth=HTTPDigestAuth(user, pwd)
)

print(r.status_code)
print(r.text)