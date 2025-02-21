import logging
from pysnmp.hlapi import *
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity.rfc3413 import cmdrsp, cmdgen, context
from pysnmp.proto.api import v2c
from pysnmp import error

# Configure logging
logging.basicConfig(
    filename="snmp_proxy.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Initialize SNMP Engine
snmpEngine = engine.SnmpEngine()
snmpContext = context.SnmpContext(snmpEngine)  # Create SNMP Context

# SNMPv3 Credentials
USERNAME = "proxyUser"
AUTH_KEY = "authPassword123"
PRIV_KEY = "privPassword123"
AUTH_PROTO = config.usmHMACSHAAuthProtocol
PRIV_PROTO = config.usmAesCfb128Protocol

# Target SNMP Agent (Remote Device)
TARGET_DEVICE = ("192.168.1.100", 161)

# Static OID Mappings (Handled Locally)
LOCAL_OIDS = {
    "1.3.6.1.4.1.6302.2.1.2.28.6.0": "SNMP Proxy Device",
    "1.3.6.1.2.1.1.3.0": "123456",  # Example uptime
}

# Setup Transport (Listening on UDP 161)
config.addTransport(
    snmpEngine,
    udp.domainName + (1,),
    udp.UdpTransport().openServerMode(("0.0.0.0", 161)),
)

# Configure SNMPv3 User
config.addV3User(
    snmpEngine,
    USERNAME,
    AUTH_PROTO,
    AUTH_KEY,
    PRIV_PROTO,
    PRIV_KEY,
)

# Add Default SNMP Context
config.addContext(snmpEngine, "")

# Configure Target SNMP Device (Proxied Requests)
config.addTargetParams(snmpEngine, "remote-agent-auth", USERNAME, "authPriv", 3)
config.addTargetAddr(
    snmpEngine,
    "remote-agent",
    udp.domainName + (2,),
    TARGET_DEVICE,
    "remote-agent-auth",
    retryCount=0,
)


class SNMPProxyResponder(cmdrsp.CommandResponderBase):
    """
    Custom SNMP Responder that either answers locally or forwards requests.
    """

    cmdGenMap = {
        v2c.GetRequestPDU.tagSet: cmdgen.GetCommandGenerator(),
        v2c.SetRequestPDU.tagSet: cmdgen.SetCommandGenerator(),
        v2c.GetNextRequestPDU.tagSet: cmdgen.NextCommandGeneratorSingleRun(),
        v2c.GetBulkRequestPDU.tagSet: cmdgen.BulkCommandGeneratorSingleRun(),
    }
    pduTypes = cmdGenMap.keys()  # This app will handle these PDUs

    def handleMgmtOperation(self, snmpEngine, stateReference, contextName, PDU, acInfo):
        """
        Handles incoming SNMP requests: answers locally or proxies them.
        """
        transportDomain, transportAddress = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)
        source_ip = transportAddress[0]

        # Extract OID from PDU
        varBinds = v2c.apiPDU.getVarBinds(PDU)
        responseVarBinds = []

        print(f"📩 Incoming SNMP request from {source_ip}: {varBinds}")
        logging.info(f"📩 Incoming SNMP request from {source_ip}: {varBinds}")

        # Check if OID is locally handled
        for oid, value in varBinds:
            oid_str = str(oid)

            if oid_str in LOCAL_OIDS:
                response = LOCAL_OIDS[oid_str]
                responseVarBinds.append((oid, v2c.OctetString(response)))
                print(f"✅ Local Response: {oid_str} -> {response}")
                logging.info(f"✅ Local Response: {oid_str} -> {response}")
            else:
                print(f"🔄 OID {oid_str} not found locally, proxying request...")
                logging.info(f"🔄 OID {oid_str} not found locally, proxying request...")

                # Forward to remote SNMP device
                self.cmdGenMap[PDU.tagSet].sendPdu(
                    snmpEngine,
                    "remote-agent",
                    None,  # contextEngineId
                    contextName,
                    PDU,
                    self.handleResponsePdu,
                    (stateReference, PDU),
                )
                return  # Wait for response from remote agent

        # If all OIDs are local, return response immediately
        self.sendResponse(snmpEngine, stateReference, PDU, responseVarBinds)

    def handleResponsePdu(self, snmpEngine, sendRequestHandle, errorIndication, PDU, cbCtx):
        """
        Handles the response from the proxied SNMP request.
        """
        stateReference, reqPDU = cbCtx

        if errorIndication:
            print(f"❌ Proxy request failed: {errorIndication}")
            logging.error(f"❌ Proxy request failed: {errorIndication}")
            PDU = v2c.apiPDU.getResponse(reqPDU)
            PDU.setErrorStatus(PDU, 5)  # Set an error status in response

        self.sendResponse(snmpEngine, stateReference, PDU, v2c.apiPDU.getVarBinds(PDU))

    def sendResponse(self, snmpEngine, stateReference, reqPDU, varBinds):
        """
        Sends SNMP response back to the original requester.
        Ensures the PDU type is changed to RESPONSE-PDU.
        """
        print(f"🚀 Sending SNMP response: {varBinds}")
        logging.info(f"🚀 Sending SNMP response: {varBinds}")

        # Convert GET-PDU to RESPONSE-PDU
        respPDU = v2c.apiPDU.getResponse(reqPDU)
        v2c.apiPDU.setVarBinds(respPDU, varBinds)

        self.sendPdu(snmpEngine, stateReference, respPDU)
        self.releaseStateInformation(stateReference)


# Start the SNMP Proxy
SNMPProxyResponder(snmpEngine, snmpContext)

print("✅ SNMP Proxy started on UDP 161, listening for SNMPv3 requests.")
logging.info("✅ SNMP Proxy started on UDP 161, listening for SNMPv3 requests.")

snmpEngine.transportDispatcher.jobStarted(1)  # Allow asyncore to run

try:
    snmpEngine.transportDispatcher.runDispatcher()
except KeyboardInterrupt:
    print("❌ SNMP Proxy shutting down.")
    logging.info("❌ SNMP Proxy shutting down.")
    snmpEngine.transportDispatcher.closeDispatcher()
