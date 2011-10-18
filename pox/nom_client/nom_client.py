#!/usr/bin/env python
# Nom nom nom nom

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent.revent import *

import sys
import threading
import signal
import time

import Pyro4
import Pyro4.util

sys.excepthook=Pyro4.util.excepthook

log = core.getLogger()

class NomClient:
    """
    Keeps a copy of the Nom in its cache. Arbitrary controller applications
    can be implemented on top of NomClient through inheritance. Mutating calls to 
    self.nom transparently write-through to the NomServer

    Visually,  NomClient's connect to the NomServer through
    the following interfaces:

    ==========================                            ==========================
    |    NomClient           |                            |    NomServer           |
    |                        |   any mutating operation   |                        |
    |                        |  -------------------->     |server.put(nom)         |
    |                        |                            |                        |
    |          client.       |   cache invalidation, or   |                        |
    |            update_nom()|   network event            |                        |
    |                        |   <-------------------     |                        |
    ==========================                            ==========================
    """
    def __init__(self):
        nom_client = self
        class DaemonThread(threading.Thread):
            def __init__(self):
                threading.Thread.__init__(self)
                self.registered = False

            """daemon.requestLoop() does not return, so we spawn a new thread"""
            def run(self):
                daemon = Pyro4.Daemon()
                nom_client.uri = daemon.register(nom_client)
                self.registered = True
                daemon.requestLoop()
                
        self.daemon_thread = DaemonThread()
        self.daemon_thread.start()

        self.server = Pyro4.Proxy("PYRONAME:nom_server.nom_server")
        # wait to be registered with the Pyro daemon
        while not self.daemon_thread.registered:
            pass
        self.server.register_client(self.uri)
        self.nom = self.server.get()

    def update_nom(self, nom):
        """
        According to Scott's philosophy of SDN, a control application is a
        function: F(view) => configuration

        This method is the entry point for the POX platform to update the
        view. 

        The POX platform may invoke it in two situations:
          i.  NomServer will invalidate this client's cache in the
              case where another client modifies its copy of the NOM

          ii. Either POX or this client (should) register this method as a
              handler for network events.
        """
        log.info("Updating nom from %s to %s " % (self.nom, nom))
        self.nom = nom
        return True

def main():
    import time
    import random

    def sigint_handler(signum, frame):
        import os
        os._exit(signum)

    signal.signal(signal.SIGINT, sigint_handler)

    nom_client = NomClient()
    time.sleep(2)

    while True:
        # test read operation
        nom_client.nom.items()
        # test write operation 
        nom_client.nom[random.randint(0,100)] = random.randint(0,100)
        time.sleep(random.randint(0,4))

if __name__ == "__main__":
    main()
