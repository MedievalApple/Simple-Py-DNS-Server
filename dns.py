import socket, glob, json

port = 53
ip = '10.0.0.1'

queryadress = ""
queryalert = False

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((ip, port))

print("The DNS Has Started On: " + ip + ":" + str(port))
print(" ")

def load_zones():

    jsonzone = {}
    zonefiles = glob.glob('zones/*.zone')
    
    #Prints Found Zone Files
    print("Found These Zone Files: ")
    print(zonefiles)
    print(" ")

    for zone in zonefiles:
        with open(zone) as zonedata:
            data = json.load(zonedata)
            zonename = data["$origin"]
            jsonzone[zonename] = data
    return jsonzone

zonedata = load_zones()

def getflags(flags):

    byte1 = bytes(flags[:1])
    byte2 = bytes(flags[1:2])

    rflags = ''

    QR = '1'

    OPCODE = ''
    for bit in range(1,5):
        OPCODE += str(ord(byte1)&(1<<bit))
    
    AA = '1'

    TC = '0'

    RD = '0'

    RA = '0'

    Z = '000'

    RCODE = '0000'

    return int(QR+OPCODE+AA+TC+RD, 2).to_bytes(1, byteorder='big')+int(RA+Z+RCODE).to_bytes(1, byteorder='big')

def getquestiondomain(data):

    state = 0
    expectedlength = 0
    domainstring = ''
    domainparts = []
    x = 0
    y = 0

    for byte in data:
        if state == 1:
            if byte != 0:
                domainstring += chr(byte)
            x += 1
            if x == expectedlength:
                domainparts.append(domainstring)
                domainstring = ''
                state = 0
                x = 0
            if byte == 0:
                domainparts.append(domainstring)
                break
        else:
            state = 1
            expectedlength = byte

        y += 1

    questiontype = data[y:y+2]

    return(domainparts, questiontype)

def getzone(domain):
    global zonedata
    global queryalert
    zone_name = '.'.join(domain)
    if queryalert == False:
        print(queryadress[0] + ":" + str(queryadress[1]) + " Queried: " + zone_name[:-1])
        queryalert = True
    try:
        return zonedata[zone_name]
    except:
        print("Could Not Find A Record For: " + zone_name[:-1])
        return ""
    
def checkforrec(data):
    domain, questiontype = getquestiondomain(data)
    
    zone = getzone(domain)

    if zone == "":
        return False
    else:
        return True

def getrecs(data):
    domain, questiontype = getquestiondomain(data)
    qt = ''
    if questiontype == b'\x00\x01':
        qt = 'a'

    zone = getzone(domain)

    return (zone[qt], qt, domain)

def buildquestion(domainname, rectype):
    qbytes = b''

    for part in domainname:
        length = len(part)
        qbytes += bytes([length])

        for char in part:
            qbytes += ord(char).to_bytes(1, byteorder='big')

    if rectype == 'a':
        qbytes += (1).to_bytes(2, byteorder='big')

    qbytes += (1).to_bytes(2, byteorder='big')
    return qbytes
        
def rectobytes(domainname, rectype, recttl, recval):

    rbytes = b'\xc0\x0c'

    if rectype == 'a':
        rbytes = rbytes + bytes([0]) + bytes([1])

    rbytes = rbytes + bytes([0]) + bytes([1])

    rbytes += int(recttl).to_bytes(4, byteorder='big')

    if rectype == 'a':
        rbytes = rbytes + bytes([0]) + bytes([4])

        for part in recval.split('.'):
            rbytes += bytes([int(part)])
    return rbytes


def buildresponse(data):

    # Check If Record Exists
    if checkforrec(data[12:]) == True:

        # Transaction ID
        TransactionID = data[:2]
        
        # Get the flags
        Flags = getflags(data[2:4])

        #Question Count
        QDCOUNT = b'\x00\x01'

        # Answer Count
        ANCOUNT = len(getrecs(data[12:])[0]).to_bytes(2, byteorder='big')
        
        # Nameserver Count
        NSCOUNT = (0).to_bytes(2, byteorder='big')

        # Additional Count
        ARCOUNT = (0).to_bytes(2, byteorder='big')

        dnsheader = TransactionID+Flags+QDCOUNT+ANCOUNT+NSCOUNT+ARCOUNT

        dnsbody = b''

        # Get answer for query
        records, rectype, domainname = getrecs(data[12:])

        dnsquestion = buildquestion(domainname, rectype)

        for record in records:
            dnsbody += rectobytes(domainname, rectype, record["ttl"], record["value"])

        return dnsheader + dnsquestion + dnsbody
    
    else:
        return ""

while 1:
    data, addr = sock.recvfrom(512)
    queryadress = addr
    r = buildresponse(data)
    queryadress = ""
    queryalert = False
    print(" ")
    if r != "":
        sock.sendto(r, addr)