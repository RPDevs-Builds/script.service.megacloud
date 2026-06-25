# -*- coding: utf-8 -*-
import base64
import math
import re
import json
import urllib.request
import urllib.parse
from resources.lib.logger import get_logger

log = get_logger()

class MegacloudDecryptor:
    def __init__(self):
        self.char_array = [chr(32 + i) for i in range(95)]

    def keygen2(self, megacloud_key: str, client_key: str) -> str:
        temp_key = megacloud_key + client_key
        hash_val = 0
        keygen_hash_mult_val = 31
        for char in temp_key:
            hash_val = ord(char) + hash_val * keygen_hash_mult_val + (hash_val << 7) - hash_val
        
        hash_val = -hash_val if hash_val < 0 else hash_val
        l_hash = hash_val % 0x7FFFFFFFFFFFFFFF
        
        temp_key = "".join(chr(ord(c) ^ 247) for c in temp_key)
        
        pivot = (l_hash % len(temp_key)) + 5
        temp_key = temp_key[pivot:] + temp_key[:pivot]
        
        leaf_str = client_key[::-1]
        return_key = ""
        max_len = max(len(temp_key), len(leaf_str))
        for i in range(max_len):
            c1 = temp_key[i] if i < len(temp_key) else ""
            c2 = leaf_str[i] if i < len(leaf_str) else ""
            return_key += c1 + c2
            
        return_key = return_key[:(96 + l_hash % 33)]
        return_key = "".join(chr((ord(c) % 95) + 32) for c in return_key)
        return return_key

    def columnar_cipher2(self, src: str, ikey: str) -> str:
        column_count = len(ikey)
        row_count = math.ceil(len(src) / column_count)
        
        grid = [[" " for _ in range(column_count)] for _ in range(row_count)]
        key_map = [{"char": char, "idx": index} for index, char in enumerate(ikey)]
        sorted_map = sorted(key_map, key=lambda x: ord(x["char"]))
        
        src_index = 0
        for item in sorted_map:
            idx = item["idx"]
            for r in range(row_count):
                if src_index < len(src):
                    grid[r][idx] = src[src_index]
                    src_index += 1
                    
        res = []
        for r in range(row_count):
            for c in range(column_count):
                res.append(grid[r][c])
        return "".join(res)

    def seed_shuffle2(self, char_array, ikey: str):
        hash_val = 0
        for char in ikey:
            hash_val = (hash_val * 31 + ord(char)) & 0xFFFFFFFF
            
        shuffle_num = hash_val
        
        def pseudo_rand(arg):
            nonlocal shuffle_num
            shuffle_num = (shuffle_num * 1103515245 + 12345) & 0x7FFFFFFF
            return shuffle_num % arg

        ret_list = list(char_array)
        for i in range(len(ret_list) - 1, 0, -1):
            swap_index = pseudo_rand(i + 1)
            ret_list[i], ret_list[swap_index] = ret_list[swap_index], ret_list[i]
        return ret_list

    def decrypt(self, encrypted_src: str, nonce: str, secret: str) -> str:
        layers = 3
        gen_key = self.keygen2(secret, nonce)
        dec_src = base64.b64decode(encrypted_src).decode('latin1')
        
        for iteration in range(layers, 0, -1):
            layer_key = gen_key + str(iteration)
            
            hash_val = 0
            for char in layer_key:
                hash_val = (hash_val * 31 + ord(char)) & 0xFFFFFFFF
                
            seed = hash_val
            
            def seed_rand(arg):
                nonlocal seed
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                return seed % arg
                
            shifted_chars = []
            for char in dec_src:
                try:
                    c_idx = self.char_array.index(char)
                    rand_num = seed_rand(95)
                    new_idx = (c_idx - rand_num + 95) % 95
                    shifted_chars.append(self.char_array[new_idx])
                except ValueError:
                    shifted_chars.append(char)
            dec_src = "".join(shifted_chars)
            
            dec_src = self.columnar_cipher2(dec_src, layer_key)
            
            sub_values = self.seed_shuffle2(self.char_array, layer_key)
            char_map = {char: self.char_array[idx] for idx, char in enumerate(sub_values)}
            
            dec_src = "".join(char_map.get(char, char) for char in dec_src)
            
        data_len = int(dec_src[:4])
        return dec_src[4:4 + data_len]

def fetch_via_flaresolverr(url, referer, fs_url, fs_timeout):
    import urllib.request
    import json
    
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": fs_timeout * 1000,
        "headers": {
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req_body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(fs_url, data=req_body, headers=headers, method="POST")
    
    with urllib.request.urlopen(req, timeout=fs_timeout + 10) as f:
        resp = json.loads(f.read().decode('utf-8'))
        
    if resp.get("status") != "ok":
        raise Exception("FlareSolverr error: " + str(resp.get("message")))
        
    return resp.get("solution", {})

def extract_megacloud_sources(embed_url: str, referer: str = "https://hianime.to/", keys_url: str = None, fs_enable: bool = False, fs_url: str = "http://localhost:8191/v1", fs_timeout: int = 30):
    if not keys_url:
        keys_url = "https://raw.githubusercontent.com/RPDevs-Builds/script.service.megacloud/master/keys/keys.json"
        
    user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
    
    parsed_url = urllib.parse.urlparse(embed_url)
    domain = parsed_url.netloc
    parts = parsed_url.path.split('/')
    xrax = parts[-1]
    path = "/".join(parts[:-1])
    get_sources_base = f"https://{domain}{path}/getSources?id="
    
    cookies = []
    ua = user_agent
    
    if fs_enable:
        try:
            solution = fetch_via_flaresolverr(embed_url, referer, fs_url, fs_timeout)
            html = solution.get("response", "")
            cookies = solution.get("cookies", [])
            ua = solution.get("userAgent", user_agent)
        except Exception as e:
            log.error(f"FlareSolverr fetch failed for {embed_url}: {str(e)}")
            raise Exception("FlareSolverr fetch failed: " + str(e))
    else:
        req = urllib.request.Request(embed_url, headers={
            "User-Agent": user_agent,
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest"
        })
        with urllib.request.urlopen(req, timeout=10) as f:
            html = f.read().decode('utf-8')
            
    match1 = re.search(r'\b[a-zA-Z0-9]{48}\b', html)
    nonce = None
    if match1:
        nonce = match1.group(0)
    else:
        match2 = re.search(r'\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b.*?\b([a-zA-Z0-9]{16})\b', html)
        if match2:
            nonce = "".join(match2.groups())
            
    if not nonce:
        log.error("Could not find nonce in embed page")
        raise Exception("Could not find nonce in embed page")
        
    get_sources_url = f"{get_sources_base}{xrax}&_k={nonce}"
    
    response_json = None
    
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    headers = {
        "User-Agent": ua,
        "Referer": referer,
        "X-Requested-With": "XMLHttpRequest"
    }
    if cookie_str:
        headers["Cookie"] = cookie_str
        
    req_sources = urllib.request.Request(get_sources_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req_sources, timeout=10) as f:
            response_json = json.loads(f.read().decode('utf-8'))
    except Exception as e:
        if fs_enable:
            solution_sources = fetch_via_flaresolverr(get_sources_url, referer, fs_url, fs_timeout)
            raw_resp = solution_sources.get("response", "")
            if "<pre" in raw_resp or "<body" in raw_resp or "<html" in raw_resp:
                json_match = re.search(r'({.*})', raw_resp, re.DOTALL)
                if json_match:
                    raw_resp = json_match.group(1)
            response_json = json.loads(raw_resp)
        else:
            raise e
            
    if not response_json:
        raise Exception("Failed to retrieve sources response")
        
    if response_json.get("encrypted"):
        req_keys = urllib.request.Request(keys_url, headers={
            "User-Agent": ua
        })
        with urllib.request.urlopen(req_keys, timeout=10) as fk:
            keys = json.loads(fk.read().decode('utf-8'))
            
        key = keys.get("vidstr")
        if not key:
            raise Exception("Key 'vidstr' not found in keys JSON")
            
        decryptor = MegacloudDecryptor()
        decrypted = decryptor.decrypt(response_json["sources"], nonce, key)
        try:
            response_json["sources"] = json.loads(decrypted)
        except Exception as e:
            raise Exception(f"JSON load failed on decrypted sources: {str(e)}")
            
    return response_json

