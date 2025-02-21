
from pysnmp.hlapi import *

def snmp_get(oid, hostname, user, auth_key, priv_key):
    iterator = getCmd(
        SnmpEngine(),
        UsmUserData(user, auth_key, priv_key, authProtocol=usmHMACSHAAuthProtocol, privProtocol=usmAesCfb128Protocol),
        UdpTransportTarget((hostname, 161)),
        ContextData(),
        ObjectType(ObjectIdentity(oid))
    )

    errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

    if errorIndication:
        print(errorIndication)
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(), errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            print(' = '.join([x.prettyPrint() for x in varBind]))

if __name__ == "__main__":
    snmp_get('1.3.6.1.4.1.6302.2.1.2.28.6.0', 'localhost', 'proxyUser', 'authPassword123', 'privPassword123')
