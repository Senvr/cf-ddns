import requests, time
import socket, json, sys
import requests.packages.urllib3.util.connection as urllib3_cn
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

auth_headers = None


def get_ip_addr(ipv: int = 4):
    assert ipv == 4 or ipv == 6

    old_gai_family = urllib3_cn.allowed_gai_family
    if ipv == 6:
        print("Monkeypatching urllib3 for IPV6 only connection (please double check)")
        def allowed_gai_family():
            family = socket.AF_INET6
            return family

        urllib3_cn.allowed_gai_family = allowed_gai_family

    try:
        ip_addr = requests.get(f"https://ifconfig.co/ip",timeout=300).text
    except requests.exceptions.ConnectionError:
        session=requests.Session()
        retry=Retry(connect=128,backoff_factor=1.0)
        adapter=HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        ip_addr=session.get("https://ifconfig.co/ip").text
    urllib3_cn.allowed_gai_family = old_gai_family
    return ip_addr.strip()


def zoneid_from_name(zone_domain_name: str):
    global auth_headers
    zone_data_results = requests.get(
        f"https://api.cloudflare.com/client/v4/zones?name={zone_domain_name}",
        headers=auth_headers,
    ).json()["result"]
    assert len(zone_data_results) == 1
    return str(zone_data_results[0]["id"]).strip()


def recordids_by_attributes(zone_id: str, fqdn: str, record_type: str):
    global auth_headers
#   print(zone_id, fqdn, record_type)
    r = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={fqdn}&type={record_type}",
        headers=auth_headers,
    )
    recordids_json = r.json()
    return recordids_json["result"]


def create_dns_record(
    zone_id: str,
    dns_record_address: str,
    fqdn: str,
    dns_record_type: str,
    comment: str = f"cf-ddns created {time.time()}",
    proxied:bool=True,
    ttl: int = 1,
):
    global auth_headers
    payload={
        "content": dns_record_address,
        "name": fqdn,
        "proxied": proxied,
        "type": dns_record_type,
        "comment": comment,
        "ttl": int(ttl),
    }
    r = requests.post(        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
        data=json.dumps(payload),
        headers=auth_headers,
    )
    if not r.ok:
        raise RuntimeError(r.text)
    return True

def update_record_by_id(
    zone_id: str,
    dns_record_id: str,
    dns_record_address: str,
    fqdn: str,
    dns_record_type: str,
    comment: str = "cf-ddns updated {time.time()}",
    ttl: int = 1,

):
    global auth_headers
    payload = {
        "content": dns_record_address,
        "name": fqdn,
        "type": dns_record_type,
        "comment": comment,
        "ttl": int(ttl),
    }
    r = requests.put(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{dns_record_id}",
        data=json.dumps(payload),
        headers=auth_headers,
    )
    if not r.ok:
        print(zone_id, dns_record_id, fqdn)
        raise RuntimeError(r.text)
    return True


if __name__ == "__main__":
    if not len(sys.argv) == 5:
        raise ValueError(
            f"Invalid arguments\nExpecting 4, got {len(sys.argv)-1}\nFormat: fqdn name type token"
        )
    _, fqdn, zone_domain_name, record_type, cf_api_token = sys.argv

    auth_headers = {
        "Authorization": f"Bearer {cf_api_token}",
        "Content-Type": "application/json",
    }

    ip_type = 4
    if record_type == "AAAA":
        ip_type = 6
    self_ip = get_ip_addr(ip_type)
    print(f"Machine IP is {self_ip}, IPv{ip_type}")
    zone_domain_name_id = zoneid_from_name(zone_domain_name)
    dns_record_json = recordids_by_attributes(zone_domain_name_id, fqdn, record_type)
    print(f"Zone ID of {zone_domain_name} is {zone_domain_name_id}")
    if len(dns_record_json) > 0:
        print("Record exists, checking if update is needed")
        dns_record_address = dns_record_json[0]["content"]
        print(f"[{record_type}] - {fqdn} > {dns_record_address}")
        dns_record_id = dns_record_json[0]["id"]

        if not dns_record_address == self_ip:
            update_record_by_id(
                zone_domain_name_id, dns_record_id, self_ip, fqdn, record_type
            )
            print(f"UPDATED [{record_type}]@{fqdn} > {self_ip}")
        else:
            print("Did not update existing record for this host")
    else:
        create_dns_record(zone_domain_name_id, self_ip, fqdn, record_type)
        print(f"CREATED [{record_type}]@{fqdn} > {self_ip}")
