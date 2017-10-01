import requests
import grequests
import os
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

meraki_api_token = os.getenv("MERAKI_API_TOKEN")
meraki_org = os.getenv("MERAKI_ORG")
header = {"X-Cisco-Meraki-API-Key": meraki_api_token}


def get_meraki_networks():
    # Get a list of all networks associated with the specified organization
    url = "https://dashboard.meraki.com/api/v0/organizations/" + meraki_org + "/networks"
    netlist = requests.get(url, headers=header)
    netjson = json.loads(netlist.content.decode("utf-8"))
    return netjson


def collect_url_list(jsondata, baseurl, attr1, attr2):
    # Iterates the jsondata list/dictionary and pulls out attributes to generate a list of URLs
    # jsondata  :   list of dictionaries or dictionary of lists
    # baseurl   :   base url to use. place a $ to show where to substitute
    # attr1     :   when using a list of dictionaries, this is the key that will be retrieved from each dict in the list
    #               when using a dictionary of lists, this is the key where all of the lists will be found
    # attr2     :   (optional) pass "" to disable
    #               when using a dictionary of lists, this is the key that will be retrieved from each dict in each list
    urllist = []
    for jsonitem in jsondata:
        if attr2 == "":
            if attr1 in jsonitem:
                urllist.append(baseurl.replace("$", jsonitem[attr1]))
        else:
            if attr1 in jsondata[jsonitem]:
                for jsonitem2 in jsondata[jsonitem][attr1]:
                    urllist.append(baseurl.replace("$", jsonitem2[attr2]))

    return urllist


def do_multi_get(url_list, comp_list, comp_id1, comp_id2, comp_url_idx, comp_key, content_key):
    # Issues multiple GET requests to a list of URLs. Also will join dictionaries together based on returned content.
    # url_list     :   list of URLs to issue GET requests to
    # comp_list    :   (optional) pass [] to disable
    #                  used to join the results of the GET operations to an existing dictionary
    # comp_id1     :   when using a list of dictionaries, this is the key to retrieve from each dict in the list
    #                  when using a dictionary of lists, this is the key where all of the lists will be found
    # comp_id2     :   (optional) pass "" to disable
    #                  when using a dictionary of lists, this is key that will be retrieved from each dict in each list
    # comp_url_idx :   (optional) pass -1 to disable
    #                  when merging dictionaries, they can be merged either on a URL comparision or a matching key. Use
    #                  this to specify that they be merged based on this specific index in the URL. So to match
    #                  'b' in http://a.com/b, you would specify 3 here, as that is the 3rd // section in the URL
    # comp_key     :   (optional) pass "" to disable
    #                  when merging dictionaries, they can be merged either on a URL comparision or a matching key. Use
    #                  this to specify that they be merged based on this key found in the content coming back from the
    #                  GET requests
    # content_key  :   (optional when not merging, required when merging) pass "" to disable
    #                  this is the base key added to the merged dictionary for the merged data
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.2, status_forcelist=[403, 500, 502, 503, 504], raise_on_redirect=True,
                    raise_on_status=True)
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.mount('https://', HTTPAdapter(max_retries=retries))

    rs = (grequests.get(u, headers=header, session=s) for u in url_list)

    content_dict = {}
    for itemlist in grequests.imap(rs, stream=False):
        inlist = json.loads(itemlist.content.decode("utf-8"))
        if len(inlist) > 0:
            # Use the URL index if it was specified, otherwise use the comparision key
            if comp_url_idx >= 0:
                urllist = itemlist.url.split("/")
                matchval = urllist[comp_url_idx]
            else:
                matchval = inlist[0][comp_key]

            if len(comp_list) > 0:
                # comp_list was passed, iterate and merge dictionaries
                for net in comp_list:
                    if comp_id2 == "":
                        # this is a list of dictionaries. if this matches the search, add it to the content dict
                        if matchval == net[comp_id1]:
                            kid1 = net["id"]

                            if kid1 not in content_dict:
                                content_dict[kid1] = {}
                            content_dict[kid1]["info"] = net
                            content_dict[kid1][content_key] = inlist
                            break
                    else:
                        # this is a dictionary of lists. if the match is present in this dictionary, continue parsing
                        if matchval in json.dumps(comp_list[net][comp_id1]):
                            kid1 = comp_list[net]["info"]["id"]

                            for net2 in comp_list[net][comp_id1]:
                                kid2 = net2["serial"]

                                if comp_id2 in net2:
                                    if matchval == net2[comp_id2]:
                                        if kid1 not in content_dict:
                                            content_dict[kid1] = {}
                                        if comp_id1 not in content_dict[kid1]:
                                            content_dict[kid1][comp_id1] = {}
                                        if kid2 not in content_dict[kid1][comp_id1]:
                                            content_dict[kid1][comp_id1][kid2] = {}

                                        content_dict[kid1]["info"] = comp_list[net]
                                        content_dict[kid1][comp_id1][kid2]["info"] = net2
                                        content_dict[kid1][comp_id1][kid2][content_key] = inlist
                                        break
            else:
                if matchval not in content_dict:
                    content_dict[matchval] = {}
                if content_key != "":
                    if content_key not in content_dict[matchval]:
                        content_dict[matchval][content_key] = {}
                    content_dict[matchval][content_key] = inlist
                else:
                    content_dict[matchval] = inlist

    return content_dict


def decode_model(strmodel):
    # Decodes the Meraki model number into it's general type.
    outmodel = ""
    if "MX" in strmodel:
        outmodel = "Security Appliance"
    if "MS" in strmodel:
        outmodel = "Switch"
    if "MR" in strmodel:
        outmodel = "Wireless"
    if "MV" in strmodel:
        outmodel = "Camera"
    if "MC" in strmodel:
        outmodel = "Phone"

    if outmodel == "":
        outmodel = strmodel[0:2]

    return outmodel


def do_sort_smclients(in_smlist):
    # Rearranges the SM Dictionary to group clients by MAC address rather than a single list
    out_smlist = {}

    for net in in_smlist:
        if "devices" in in_smlist[net]:
            for cli in in_smlist[net]["devices"]:
                if net not in out_smlist:
                    out_smlist[net] = {"devices": {}}
                out_smlist[net]["devices"][cli["wifiMac"]] = cli

    return out_smlist


def do_split_networks(in_netlist):
    # Splits out combined Meraki networks into individual device networks.
    devdict = {}

    for net in in_netlist:
        base_name = in_netlist[net]["info"]["name"]
        for dev in in_netlist[net]["devices"]:
            thisdevtype = decode_model(dev["model"])
            newname = base_name + " - " + thisdevtype

            if newname in devdict:
                devdict[newname].append(dev)
            else:
                devdict[newname] = [dev]

    return devdict


def get_meraki_health(incoming_msg, rettype):
    # Get a list of all networks associated with the specified organization
    netjson = get_meraki_networks()
    # Parse list of networks to extract/create URLs needed to get list of devices
    urlnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$/devices", "id", "")
    # Get a list of all devices associated with the networks associated to the organization
    netlist = do_multi_get(urlnet, netjson, "id", "", -1, "networkId", "devices")
    # Split network lists up by device type
    newnetlist = do_split_networks(netlist)

    totaldev = 0
    retmsg = "<h3>Meraki Details:</h3>"
    retmsg += "<a href='https://dashboard.meraki.com/'>Meraki Dashboard</a><br><ul>"
    for net in sorted(newnetlist):
        totaldev += len(newnetlist[net])
        retmsg += "<li>Network '" + net + "' has " + str(len(newnetlist[net])) + " device(s).</li>"
    retmsg += "</ul><b>There are a total of " + str(totaldev) + " device(s).</b>"

    print(retmsg)
    return retmsg


def get_meraki_clients(incoming_msg, rettype):
    cmdlist = incoming_msg.text.split(" ")
    client_id = cmdlist[len(cmdlist)-1]
    # Get a list of all networks associated with the specified organization
    netjson = get_meraki_networks()
    # Parse list of networks to extract/create URLs needed to get list of devices
    urlnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$/devices", "id", "")
    smnet = collect_url_list(netjson, "https://dashboard.meraki.com/api/v0/networks/$/sm/devices/", "id", "")
    # Get a list of all devices associated with the networks associated to the organization
    netlist = do_multi_get(urlnet, netjson, "id", "", -1, "networkId", "devices")
    smlist = do_multi_get(smnet, [], "id", "", 6, "", "")
    newsmlist = do_sort_smclients(smlist)
    # Parse list of devices to extract/create URLs needed to get list of clients
    urldev = collect_url_list(netlist, "https://dashboard.meraki.com/api/v0/devices/$/clients?timespan=86400", "devices", "serial")
    # Get a list of all clients associated with the devices associated to the networks associated to the organization
    netlist = do_multi_get(urldev, netlist, "devices", "serial", 6, "", "clients")

    if rettype == "json":
        return {"client": netlist, "sm": newsmlist}
    else:
        retmsg = "###Associated Clients:\n"
        for net in sorted(netlist):
            for dev in netlist[net]["devices"]:
                for cli in netlist[net]["devices"][dev]["clients"]:
                    if not isinstance(cli, str):
                        if cli["description"] == client_id and "switchport" in cli:
                            retmsg += "_Computer Name:_ " + cli["dhcpHostname"] + "<br>"

                            if net in newsmlist:
                                if "devices" in newsmlist[net]:
                                    if cli["mac"] in newsmlist[net]["devices"]:
                                        smbase = newsmlist[net]["devices"][cli["mac"]]
                                        retmsg += "_Model:_ " + smbase["systemModel"] + "<br>"
                                        retmsg += "_OS:_ " + smbase["osName"] + "<br>"

                            retmsg += "_IP:_ " + cli["ip"] + "<br>"
                            retmsg += "_MAC:_ " + cli["mac"] + "<br>"
                            retmsg += "_VLAN:_ " + str(cli["vlan"]) + "<br>"
                            devbase = netlist[net]["devices"][dev]["info"]
                            retmsg += "_Connected To:_ " + devbase["name"] + " (" + devbase["model"] + "), Port " + str(cli["switchport"]) + "<br>"

        return retmsg


def get_meraki_health_html(incoming_msg):
    return get_meraki_health(incoming_msg, "html")


def get_meraki_clients_html(incoming_msg):
    return get_meraki_clients(incoming_msg, "html")
