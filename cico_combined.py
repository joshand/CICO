import json
import difflib
import cico_meraki
import cico_spark_call
import cico_umbrella
import cico_a4e
import cico_common


def get_health(incoming_msg):
    retval = ""
    if cico_common.meraki_support():
        retval += cico_meraki.get_meraki_health(incoming_msg, "html")
    if cico_common.spark_call_support():
        if retval != "":
            retval += "<br><br>"
        retval += cico_spark_call.get_spark_call_health(incoming_msg, "html")
    if cico_common.umbrella_support():
        if retval != "":
            retval += "<br><br>"
        retval += cico_umbrella.get_umbrella_health(incoming_msg, "html")
    if cico_common.a4e_support():
        if retval != "":
            retval += ""
        retval += cico_a4e.get_a4e_health(incoming_msg, "html")

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
    uclients = cico_umbrella.get_umbrella_clients(incoming_msg, "json")
    aclients = cico_a4e.get_a4e_clients(incoming_msg, "json")
    netlist = mclients["client"]
    newsmlist = mclients["sm"]

    retmsg = "<h3>Associated Clients:</h3>"
    retsc = "<h3>Collaboration:</h3>"
    retsc += "<b>Phones:</b><br>"
    foundphone = 0
    for net in sorted(netlist):
        for dev in netlist[net]["devices"]:
            for cli in netlist[net]["devices"][dev]["clients"]:
                if not isinstance(cli, str):
                    if cli["description"] == client_id and "switchport" in cli and cli["switchport"] is not None:
                        devbase = netlist[net]["devices"][dev]["info"]
                        showdev = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=86400", 0)
                        showport = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=86400", 1)
                        showcli = cico_meraki.meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])
                        retmsg += "<i>Computer Name:</i> " + showcli + "<br>"

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
                        retmsg += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"

                        # if cli["dhcpHostname"] in aclients["clients"]:
                        if any(cli["dhcpHostname"] in s for s in aclients["clients"]):
                            retmsg += "<h3>AMP for Endpoints Stats:</h3><ul>"
                            for acli in aclients["clients"]:
                                if "." in acli:
                                    ahostname = acli.split(".")[0]
                                else:
                                    ahostname = acli

                                # retmsg += ahostname + "<br>"
                                # retmsg += acli + "<br>"
                                # retmsg += cli["dhcpHostname"] + "<br>"

                                if ahostname == cli["dhcpHostname"]:
                                    retmsg += "<li><b>" + str(aclients["clients"][acli]["threat_detected_count"]) + " threat(s) detected. (" + str(aclients["clients"][acli]["threat_detected_excluded_count"]) + " in excluded locations.)</b></li>"
                                    retmsg += "<li><b>" + str(aclients["clients"][acli]["threat_quarantined_count"]) + " threat(s) quarantined.</b></li>"
                                    if aclients["clients"][acli]["threat_quarantine_failed_count"] > 0:
                                        erricon = chr(0x2757) + chr(0xFE0F)
                                    else:
                                        erricon = ""
                                    retmsg += "<li><b>" + str(aclients["clients"][acli]["threat_quarantine_failed_count"]) + " threat(s) quarantine failed." + erricon + "</b></li>"
                                # else:
                                #     # print("'" + acli + "';'" + client_id + "'")
                                #     retmsg += acli + "::" + cli["dhcpHostname"] + "<br>"
                                #     for i, s in enumerate(difflib.ndiff(acli, cli["dhcpHostname"])):
                                #         if s[0] == ' ':
                                #             continue
                                #         elif s[0] == '-':
                                #             retmsg += 'Delete "{}" from position {}'.format(s[-1], i) + "<br>"
                                #         elif s[0] == '+':
                                #             retmsg += 'Add "{}" to position {}'.format(s[-1], i) + "<br>"
                                retmsg += "</ul>Processed " + str(aclients["aggregate"]["processed_events"]) + " of " + str(aclients["aggregate"]["total_events"]) + " threat event(s)."
                        else:
                            retmsg += "<h3>AMP for Endpoints Stats:</h3><ul>"
                            retmsg += "<li>No stats available for this user.</li></ul>"

                    elif "phones" in sclients and cli["mac"] in sclients["phones"] and "switchport" in cli and cli["switchport"] is not None:
                        foundphone = 1
                        devbase = netlist[net]["devices"][dev]["info"]
                        showdev = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], devbase["name"], "?timespan=86400", 0)
                        showport = cico_meraki.meraki_create_dashboard_link("devices", devbase["mac"], str(cli["switchport"]), "/ports/" + str(cli["switchport"]) + "?timespan=86400", 1)
                        showcli = cico_meraki.meraki_dashboard_client_mod(showdev, cli["id"], cli["dhcpHostname"])

                        scbase = sclients["phones"][cli["mac"]]
                        retsc += scbase["description"] + " (<i>" + scbase["registrationStatus"] + "</i>)<br>"
                        retsc += "<i>Device Name:</i> " + showcli + "<br>"
                        retsc += "<i>IP:</i> " + cli["ip"] + "<br>"
                        retsc += "<i>MAC:</i> " + cli["mac"] + "<br>"
                        retsc += "<i>VLAN:</i> " + str(cli["vlan"]) + "<br>"
                        retsc += "<i>Connected To:</i> " + showdev + " (" + devbase["model"] + "), Port " + showport + "<br>"

    if foundphone == 0:
        if "phones" in sclients:
            for d in sclients["phones"]:
                dev = sclients["phones"][d]
                retsc += dev["description"] + " [<em>" + dev["registrationStatus"] + "</em>]<br>"
                retsc += "<i>IP:</i> " + dev.get("ipAddress", "N/A") + "<br>"
                retsc += "<i>MAC:</i> " + dev["mac"] + "<br>"

    retscn = ""
    if "numbers" in sclients:
        for n in sclients["numbers"]:
            num = sclients["numbers"][n]
            retscn = "<b>Numbers:</b><br>"
            if "external" in num:
                retscn += num["external"] + " (x" + num["internal"] + ")\n"
            else:
                retscn += "Extension " + num["internal"] + "<br>"

    retu = "<h3>Umbrella Client Stats (Last 24 hours):</h3><ul>"
    if "Aggregate" in uclients:
        retu += "<li>Total Requests: " + str(uclients["Aggregate"]["Total"]) + "</li>"
        for x in uclients["Aggregate"]:
            if x != "Total":
                retu += "<li>" + x + ": " + str(uclients["Aggregate"][x]) + " (" + str(round(uclients["Aggregate"][x] / uclients["Aggregate"]["Total"] * 100, 2)) + "%)</li>"
        retu += "</ul></b>"

        if len(uclients["Blocked"]) > 0:
            retu += "<h4>Last 5 Blocked Requests:</h4><ul>"

            for x in uclients["Blocked"]:
                retu += "<li>" + x["Timestamp"] + " " + x["Domain"] + " " + x["Categories"] + "</li>"

            retu += "</ul>"
    else:
        retu += "<li>No stats available for this user.</li></ul>"

    return retmsg + "<hr>" + retu + "<hr>" + retsc + "<br>" + retscn
