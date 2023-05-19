# cf-ddns  
Uses requests library to get local "Public IPv4/6" address from ifconfig.co, then updates a spesified domain name record via CloudFlare API.  
Retrieves zone/record ID automatically from existing record for subdomain.  
Designed to run on an individual node/instance with its own unique IP address (No NAT).  

## usage  
python3 main.py sub.domain.tld domain.tld RECORDTYPE apiTOKEN12345678  
Example:  
python3 main.py www.example.com example.com AAAA 123456789ABCDEF  

### Addendum  
I wrote this overnight on a monster-fueled coding quest and I had no previous experience with cloudflare's API before then.  
I figure there's nothing wrong by basically searching by the fqdn&type considering they are intinsically unique records by content.  
It's MIT license for a reason  
