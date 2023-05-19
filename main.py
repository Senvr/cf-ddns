import requests
import socket, json, sys
import requests.packages.urllib3.util.connection as urllib3_cn
 
 
auth_headers=None

def get_ip_addr(ipv:int=4):
    assert ipv == 4 or ipv == 6
    old_gai_family = urllib3_cn.allowed_gai_family
    if ipv == 6:        
        print("Monkeypatching urllib3")
        def allowed_gai_family():
            family = socket.AF_INET6 
            return family 
        urllib3_cn.allowed_gai_family = allowed_gai_family
    ip_addr=requests.get(f'https://ifconfig.co/ip').text.strip()
    urllib3_cn.allowed_gai_family=old_gai_family
    return ip_addr

def zoneid_from_name(zone_domain_name:str):
    global auth_headers
    zone_data_results=requests.get(f'https://api.cloudflare.com/client/v4/zones?name={zone_domain_name}', headers=auth_headers).json()['result']
    assert len(zone_data_results) == 1
    return str(zone_data_results[0]['id']).strip()

def recordids_by_attributes(zone_id:str, fqdn:str, record_type:str):
    global auth_headers
    r=requests.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={fqdn}&type={record_type}', headers=auth_headers)
    recordids_json = r.json()
    return recordids_json['result']
         
def update_record_by_id(zone_id:str, dns_record_id:str, dns_record_address:str, fqdn:str, dns_record_type:str, comment:str="cf-ddns", ttl:int=1):
            global auth_headers
            payload={
                "content": dns_record_address,
                "name": fqdn,
                "type": dns_record_type,
                "comment": comment,
                "ttl": int(ttl)
                }                    
            r=requests.put(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{dns_record_id}", data=json.dumps(payload), headers=auth_headers)
            if not r.ok: 
                print(zone_id, dns_record_id, fqdn)           
                raise RuntimeError(r.text)        
            return True

if __name__ == "__main__":                        
    if not len(sys.argv)  == 5:
        raise ValueError(f"Invalid arguments\nExpecting 6, got {len(sys.argv)}\nFormat: fqdn, name, type, token")
    _, fqdn, zone_domain_name, record_type, cf_api_token = sys.argv                
    
    auth_headers={                
        'Authorization': f"Bearer {cf_api_token}",
        "Content-Type": "application/json"
    }    
    
    zone_domain_name_id=zoneid_from_name(zone_domain_name)
    print(f"Zone ID of {zone_domain_name} is {zone_domain_name_id}")    
    
    dns_record_json=recordids_by_attributes(zone_domain_name_id, fqdn, record_type)[0]    
    dns_record_address=dns_record_json['content']
    print(f"[{record_type}] - {fqdn} > {dns_record_address}")
    dns_record_id=dns_record_json['id']    
        
    ip_type = 4
    if record_type == "AAAA":
        ip_type=6
    self_ip=get_ip_addr(ip_type)
    print(f"Machine IP is {self_ip}, IPv{ip_type}")
    
    if not dns_record_address == self_ip:
        update_record_by_id(zone_domain_name_id, dns_record_id, self_ip, fqdn, record_type)
        print(f"UPDATED [{record_type}]@{fqdn} > {dns_record_address}")