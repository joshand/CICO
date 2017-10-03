import cico_meraki
import cico_spark_call
import cico_common
import json


def get_health(incoming_msg):
    retval = ""
    if cico_common.meraki_support():
        retval += cico_meraki.get_meraki_health(incoming_msg, "html")
    if cico_common.spark_call_support():
        if retval != "":
            retval += "<br><br>"
        retval += cico_spark_call.get_spark_call_health(incoming_msg, "html")

    return retval


def get_clients(incoming_msg):
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]

    if not cico_common.meraki_support():
        cico_spark_call.get_spark_call_clients_html(incoming_msg)
    if not cico_common.spark_call_support():
        cico_meraki.get_meraki_clients_html(incoming_msg)

    sclients = cico_spark_call.get_spark_call_clients(incoming_msg, "json")
    mclients = cico_meraki.get_meraki_clients(incoming_msg, "json")
    netlist = mclients["client"]
    newsmlist = mclients["sm"]

    retmsg = "<h3>Associated Clients:</h3>"
    retsc = "<h3>Collaboration:</h3>"
    retsc += "<b>Phones:</b><br>"
    for net in sorted(netlist):
        for dev in netlist[net]["devices"]:
            for cli in netlist[net]["devices"][dev]["clients"]:
                if not isinstance(cli, str):
                    if cli["description"] == client_id and "switchport" in cli:
                        retmsg += "<i>Computer Name:</i> <a href='https://dashboard.meraki.com/manage/usage/list#c=" + cli["id"] + "'>" + cli["dhcpHostname"] + "</a><br>"

                        if net in newsmlist:
                            if "devices" in newsmlist[net]:
                                if cli["mac"] in newsmlist[net]["devices"]:
                                    smbase = newsmlist[net]["devices"][cli["mac"]]
                                    retmsg += "<i>Model:</i> " + smbase["systemModel"] + "<br>"
                                    retmsg += "<i>OS:</i> " + smbase["osName"] + "<br>"

                        retmsg += "<i>IP:</i> " + cli["ip"] + "<br>"
                        retmsg += "<i>MAC:</i> " + cli["mac"] + "<br>"
                        retmsg += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                        devbase = netlist[net]["devices"][dev]["info"]
                        retmsg += "<i>Connected To:</i> <a href='https://dashboard.meraki.com/manage/nodes/show/" + devbase["mac"] + "'>" + devbase["name"] + "</a> (" + devbase["model"] + "), Port " + str(cli["switchport"]) + "<br>"
                    elif cli["mac"] in sclients["phones"] and "switchport" in cli:
                        scbase = sclients["phones"][cli["mac"]]
                        retsc += scbase["description"] + " (<i>" + scbase["registrationStatus"] + "</i>)<br>"
                        retsc += "<i>Device Name:</i> <a href='https://dashboard.meraki.com/manage/usage/list#c=" + cli["id"] + "'>" + cli["dhcpHostname"] + "</a><br>"
                        retsc += "<i>IP:</i> " + cli["ip"] + "<br>"
                        retsc += "<i>MAC:</i> " + cli["mac"] + "<br>"
                        retsc += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                        devbase = netlist[net]["devices"][dev]["info"]
                        retsc += "<i>Connected To:</i> <a href='https://dashboard.meraki.com/manage/nodes/show/" + devbase["mac"] + "'>" + devbase["name"] + "</a> (" + devbase["model"] + "), Port " + str(cli["switchport"]) + "<br>"

    for n in sclients["numbers"]:
        num = sclients["numbers"][n]
        retscn = "<b>Numbers:</b><br>"
        if "external" in num:
            retscn += num["external"] + " (x" + num["internal"] + ")\n"
        else:
            retscn += "Extension " + num["internal"] + "<br>"

    return retmsg + "<hr>" + retsc + "<br>" + retscn
