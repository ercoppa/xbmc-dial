import threading
import socket
import fcntl
import struct
import array

running = True

def DIAL_reply(url, method):
    
    if url == '/apps/YouTube':
        
        if method == 'GET':
            reply = """HTTP/1.1 200 OK\r\nContent-Type: application/xml\r\n\r\n<?xml version="1.0" encoding="UTF-8"?>\r\n<service xmlns="urn:dial-multiscreen-org:schemas:dial">\r\n  <name>YouTube</name>\r\n  <options allowStop="true"/>\r\n  <state>running</state>\r\n  <link rel="run" href="run"/>\r\n</service>\r\n"""
        
        elif method == 'POST':
            reply = """HTTP/1.1 201 Created\r\nContent-Type: text/plain\r\nLocation: http://192.168.0.2:56789/apps/YouTube/run\r\n"""
    
    else:
        print url
        print method
        reply = ""
    
    #print reply
    return reply

def DIAL_worker(sock):
    sock.settimeout(5)
    try:
        data = sock.recv(4096)
    except socket.timeout:
        return
    
    if 'GET' in data: method = 'GET'
    elif 'POST' in data: method = 'POST'
    else: method = 'DELETE'
    
    try:
        if method != 'DELETE':
            data = data[data.index(method + ' ') + 4:]
            url = data[:data.index(' ')]
        elif method == 'DELETE':
            url = ""
        sock.send(DIAL_reply(url, method))
    except ValueError:
        print 'ERRORE:' + data
    
    sock.close()

def DIAL_server():
    
    global running
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('192.168.0.2', 56789))
    s.listen(1)
    s.settimeout(1)
    
    while running:
        try:
            conn, addr = s.accept()
            print 'DIAL Connection address:', addr
            worker = threading.Thread(target=DIAL_worker, args = (conn,))
            worker.start()
        except socket.timeout:
            pass
            
    s.close()

def SSSD_worker(sock):
    sock.settimeout(5)    
    data = sock.recv(4096)
    #if not data: return
    #print "received data:", data
    sock.send(SSSD_reply())
    sock.close()

"""<?xml version=\"1.0\"?>
<root
  xmlns=\urn:schemas-upnp-org:device-1-0\
  xmlns:r=\urn:restful-tv-org:schemas:upnp-dd\>
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:tvdevice:1</deviceType>
    <friendlyName>XBNC</friendlyName>
    <manufacturer> </manufacturer>
    <modelName>NOT A VALID MODEL NAME</modelName>
    <UDN>uuid:deadbeef-dead-beef-dead-beefdeadbeef</UDN>
  </device>
</root>"""
def SSSD_reply():
    reply = 'HTTP/1.1 200 OK\r\nContent-Type: application/xml\r\nApplication-URL: http://192.168.0.2:56789/apps/\r\n\r\n'

    reply += """<?xml version="1.0"?><root  xmlns="urn:schemas-upnp-org:device-1-0"  xmlns:r="urn:restful-tv-org:schemas:upnp-dd">  <specVersion>    <major>1</major>    <minor>0</minor>  </specVersion>  <device>    <deviceType>urn:schemas-upnp-org:device:tvdevice:1</deviceType>    <friendlyName>XBMC</friendlyName>    <manufacturer> </manufacturer>    <modelName>NOT A VALID MODEL NAME</modelName>    <UDN>uuid:deadbeef-dead-beef-dead-beefdeadbeef</UDN>  </device></root>\r\n\r\n"""

    #print reply
    return reply

def SSSD_server():
    
    global running
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('192.168.0.2', 56790))
    s.listen(1)
    s.settimeout(1)
    
    while running:
        try:
            conn, addr = s.accept()
            print 'SSSD: Connection address:', addr
            worker = threading.Thread(target=SSSD_worker, args = (conn,))
            worker.start()
        except socket.timeout:
            pass
            
    s.close()
    
def get_local_addr():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com", 80))
    addr = s.getsockname()[0]
    s.close()
    return addr

def SSSD_multicast_reply():

    ssdp_reply  = "HTTP/1.1 200 OK\r\n"
    ssdp_reply += "LOCATION: http://%s:%d/dd.xml\r\n" % (get_local_addr(), 56790)
    ssdp_reply += "CACHE-CONTROL: max-age=1800\r\n"
    ssdp_reply += "EXT:\r\n"
    ssdp_reply += "BOOTID.UPNP.ORG: 1\r\n"
    ssdp_reply += "SERVER: Linux/2.6 UPnP/1.0 quick_ssdp/1.0\r\n"
    ssdp_reply += "ST: urn:dial-multiscreen-org:service:dial:1\r\n"
    ssdp_reply += "USN: uuid:%s::" % ('deadbeef-dead-beef-dead-beefdeadbeef',)
    ssdp_reply += "urn:dial-multiscreen-org:service:dial:1\r\n\r\n"
    
    return ssdp_reply

def SSSD_multicast_server():

    global running
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 1900))
    mreq = struct.pack("=4sl", socket.inet_aton("239.255.255.250"), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    reply = SSSD_multicast_reply()
    sock.settimeout(1)
    
    while running:
        
        try:
            data, sender_addr = sock.recvfrom(4096)
            if data.index('ST: urn:dial-multiscreen-org:service:dial:1'):
                saddr = sender_addr[0]
                sport = sender_addr[1]
                #print 'Sending SSDP reply to ' + str(saddr) + ':' + str(sport)
                sock.sendto(reply, (saddr, sport))
        except socket.timeout:
            pass  
        except ValueError:
            pass
            
    sock.close()
        
if __name__ == '__main__':

    dial = threading.Thread(target=DIAL_server, args = ())
    dial.start()

    sssd_mcast = threading.Thread(target=SSSD_multicast_server, args = ())
    sssd_mcast.start()
    
    sssd = threading.Thread(target=SSSD_server, args = ())
    sssd.start()
    
    try: 
        while True: pass
    except: 
        running = False            
