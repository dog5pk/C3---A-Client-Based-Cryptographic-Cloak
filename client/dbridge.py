#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, secrets, socket, sqlite3, struct, subprocess, sys, time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

DEFAULT_CHAIN: List[Tuple[str,int]]=[("127.0.0.1",9000),("127.0.0.1",9001),("127.0.0.1",9002)]
FINAL_BIN="final_obfuscated_output.bin"; RECEIVED_BIN="received_output.bin"; RELAY_PREFIX="relay_output_"
TCP_TIMEOUT=2.0; VERSION_TAG=b"DB1"; FLAG_PADDED=0x01

def read_json(p:Path)->dict:
    if not p.exists(): raise FileNotFoundError(str(p))
    return json.loads(p.read_text())

def write_bytes(p:Path,b:bytes)->None: p.write_bytes(b)

def sha256_bytes(b:bytes)->str:
    h=hashes.Hash(hashes.SHA256()); h.update(b); return h.finalize().hex()

def parse_chain_override(s:Optional[str])->Optional[List[Tuple[str,int]]]:
    if not s: return None
    out=[]; 
    for part in s.split(","):
        part=part.strip(); 
        if not part or ":" not in part: raise ValueError(f"bad --chain entry: {part!r}")
        host,sport=part.rsplit(":",1); out.append((host,int(sport)))
    if not out: raise ValueError("--chain parsed to empty set"); 
    return out

def load_chain(override:Optional[str], cfg_path:Path|None)->List[Tuple[str,int]]:
    o=parse_chain_override(override)
    if o: return o
    if cfg_path and cfg_path.exists():
        cfg=read_json(cfg_path); lst=cfg.get("tcp_chain",cfg); out=[]
        for i in lst: out.append((i["host"],int(i["port"])))
        if not out: raise ValueError("Empty TCP chain in config")
        return out
    return DEFAULT_CHAIN

def load_root_secret(p:Path|None)->bytes:
    if p is None: raise FileNotFoundError("secrets.json required")
    hx=read_json(p).get("root_secret"); 
    if not hx: raise ValueError("secrets.json missing 'root_secret'")
    key=bytes.fromhex(hx); 
    if len(key)<32: raise ValueError("root_secret must be >=32 bytes")
    return key[:32]

def hkdf_derive(root:bytes,host:str,port:int)->bytes:
    return HKDF(algorithm=hashes.SHA256(),length=32,salt=b"dbridge-salt",info=f"dbridge-hop:{host}:{port}".encode()).derive(root)

def pad_to_multiple(data:bytes,m:int)->tuple[bytes,int]:
    if m<=0: return data,0
    rem=len(data)%m; add=(m-rem)%m; 
    if add==0: add=m
    return data+secrets.token_bytes(add),add

def build_plaintext(payload:bytes,pad_multiple:int)->tuple[bytes,bytes]:
    msg_id=secrets.token_bytes(8)
    orig_len=struct.pack(">I",len(payload))
    data,_=pad_to_multiple(payload,pad_multiple) if pad_multiple else (payload,0)
    flags=FLAG_PADDED if pad_multiple else 0
    return VERSION_TAG+struct.pack("B",flags)+msg_id+orig_len+data,msg_id

def parse_plaintext(plain:bytes)->tuple[bytes,bytes]:
    if len(plain)<16: raise ValueError("plaintext too short")
    if plain[:3]!=VERSION_TAG: raise ValueError("bad version tag")
    msg_id=plain[4:12]; orig_len=struct.unpack(">I",plain[12:16])[0]; data=plain[16:]
    if orig_len>len(data): raise ValueError("invalid original length")
    return data[:orig_len],msg_id

class NonceLogger:
    def __init__(self,path:Optional[Path])->None:
        self.path=path
        if path and not path.exists(): path.write_text("ts,dir,hop,host,port,msg_id,nonce\n")
    def log(self,*,direction:str,hop_idx:int,host:str,port:int,nonce:bytes,msg_id:Optional[bytes])->None:
        if not self.path: return
        ts=int(time.time()); mid=msg_id.hex() if msg_id else ""
        with self.path.open("a") as f: f.write(f"{ts},{direction},{hop_idx},{host},{port},{mid},{nonce.hex()}\n")

def aead_encrypt_layer(data:bytes,key:bytes,aad:bytes)->tuple[bytes,bytes]:
    a=ChaCha20Poly1305(key); n=secrets.token_bytes(12); ct=a.encrypt(n,data,aad); return n+ct,n

def aead_decrypt_layer(blob:bytes,key:bytes,aad:bytes)->tuple[bytes,bytes]:
    if len(blob)<28: raise ValueError("layer too short")
    n,ct=blob[:12],blob[12:]; a=ChaCha20Poly1305(key); pt=a.decrypt(n,ct,aad); return pt,n

def obfuscate_layers(data:bytes,chain:Sequence[Tuple[str,int]],root:bytes,logger:Optional[NonceLogger],msg_id:Optional[bytes])->bytes:
    out=data
    for idx,(h,p) in enumerate(chain,1):
        key=hkdf_derive(root,h,p); aad=f"{h}:{p}".encode()
        out,nonce=aead_encrypt_layer(out,key,aad)
        if logger: logger.log(direction="enc",hop_idx=idx,host=h,port=p,nonce=nonce,msg_id=msg_id)
    return out

def deobfuscate_layers(data:bytes,chain:Sequence[Tuple[str,int]],root:bytes,logger:Optional[NonceLogger])->bytes:
    out=data
    for r_idx,(h,p) in enumerate(reversed(chain),1):
        key=hkdf_derive(root,h,p); aad=f"{h}:{p}".encode()
        out,nonce=aead_decrypt_layer(out,key,aad)
        if logger:
            hop_idx=len(chain)-r_idx+1
            logger.log(direction="dec",hop_idx=hop_idx,host=h,port=p,nonce=nonce,msg_id=None)
    return out

def _recv_exact(s:socket.socket,n:int)->bytes:
    buf=bytearray()
    while len(buf)<n:
        chunk=s.recv(n-len(buf))
        if not chunk: raise ConnectionError("socket closed")
        buf.extend(chunk)
    return bytes(buf)

def _tcp_roundtrip(s:socket.socket,chunk:bytes)->bytes:
    s.sendall(struct.pack(">I",len(chunk))); s.sendall(chunk)
    n=struct.unpack(">I",_recv_exact(s,4))[0]; return _recv_exact(s,n)

def attempt_tcp_hop(data:bytes,host:str,port:int,mtu:int)->bytes:
    try:
        with socket.create_connection((host,port),timeout=TCP_TIMEOUT) as s:
            s.settimeout(TCP_TIMEOUT)
            if mtu and mtu>0:
                out=bytearray()
                for off in range(0,len(data),mtu): out.extend(_tcp_roundtrip(s,data[off:off+mtu]))
                return bytes(out)
            return _tcp_roundtrip(s,data)
    except Exception:
        return data

def run_online_chain(data:bytes,*,tcp:bool,mtu:int,receive_mode:bool,chain:Sequence[Tuple[str,int]],write_intermediate:bool=True)->bytes:
    segments=[data]; idxs=range(len(chain)) if not receive_mode else reversed(range(len(chain)))
    for idx in idxs:
        h,p=chain[idx]; cur=segments[-1]
        hopped=attempt_tcp_hop(cur,h,p,mtu) if tcp else cur
        segments.append(hopped)
        if not receive_mode and write_intermediate: write_bytes(Path(f"{RELAY_PREFIX}{idx+1}.bin"),hopped)
    return segments[-1]

def replay_db_open(path:Path)->sqlite3.Connection:
    c=sqlite3.connect(str(path))
    c.execute("CREATE TABLE IF NOT EXISTS messages(msg_id BLOB PRIMARY KEY, seen_at INTEGER NOT NULL) WITHOUT ROWID;")
    return c

def replay_check_and_store(conn:sqlite3.Connection,msg_id:bytes,allow:bool)->bool:
    row=conn.execute("SELECT 1 FROM messages WHERE msg_id=?", (msg_id,)).fetchone()
    if row and not allow: return False
    if not row: conn.execute("INSERT INTO messages(msg_id,seen_at) VALUES(?,?)",(msg_id,int(time.time()))); conn.commit()
    return True

def spawn_relays_if_requested(spawn:bool,relay_bin:Path,chain:Sequence[Tuple[str,int]])->List[subprocess.Popen]:
    if not spawn: return []
    if not relay_bin.exists(): raise FileNotFoundError(f"relay binary not found: {relay_bin}")
    procs=[]
    for _h,p in chain:
        try:
            subprocess.run(["bash","-lc",f"pid=$(sudo lsof -t -i TCP:{p} -sTCP:LISTEN 2>/dev/null || true); [ -n \"$pid\" ] && sudo kill -9 \"$pid\" || true"],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except Exception: pass
        procs.append(subprocess.Popen([str(relay_bin),"--port",str(p)],cwd=str(relay_bin.parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
    time.sleep(0.4); return procs

def stop_relays(ps:List[subprocess.Popen])->None:
    for p in ps:
        try: p.terminate()
        except Exception: pass
    for p in ps:
        try: p.wait(timeout=1.0)
        except Exception:
            try: p.kill()
            except Exception: pass

def cmd_send(msg:str,*,tcp:bool,mtu:int,chain_opt:str|None,config:Path|None,secrets_path:Path|None,pad:int,nonce_log:Optional[Path])->int:
    chain=load_chain(chain_opt,config); root=load_root_secret(secrets_path or Path("secrets.json")); logger=NonceLogger(nonce_log)
    plain,msg_id=build_plaintext(msg.encode(),pad); layered=obfuscate_layers(plain,chain,root,logger,msg_id)
    write_bytes(Path(FINAL_BIN),layered); print(layered.hex()); print(f"[write] {FINAL_BIN} {len(layered)} bytes sha256={sha256_bytes(layered)}")
    _=run_online_chain(layered,tcp=tcp,mtu=mtu,receive_mode=False,chain=chain); return 0

def cmd_sendfile(path:Path,*,tcp:bool,mtu:int,chain_opt:str|None,config:Path|None,secrets_path:Path|None,pad:int,nonce_log:Optional[Path])->int:
    chain=load_chain(chain_opt,config); root=load_root_secret(secrets_path or Path("secrets.json")); logger=NonceLogger(nonce_log)
    data=Path(path).read_bytes(); plain,msg_id=build_plaintext(data,pad); layered=obfuscate_layers(plain,chain,root,logger,msg_id)
    write_bytes(Path(FINAL_BIN),layered); print(f"[write] {FINAL_BIN} {len(layered)} bytes sha256={sha256_bytes(layered)}")
    _=run_online_chain(layered,tcp=tcp,mtu=mtu,receive_mode=False,chain=chain); return 0

def cmd_forward(path:Path,*,tcp:bool,mtu:int,chain_opt:str|None,config:Path|None)->int:
    chain=load_chain(chain_opt,config); data=Path(path).read_bytes()
    last=run_online_chain(data,tcp=tcp,mtu=mtu,receive_mode=False,chain=chain,write_intermediate=True)
    outp=Path(f"{RELAY_PREFIX}{len(chain)}.bin"); 
    if not outp.exists(): write_bytes(outp,last)
    print(f"[write] {outp.name} {len(last)} bytes sha256={sha256_bytes(last)}"); return 0

def cmd_receive(path:Path,*,tcp:bool,mtu:int,chain_opt:str|None,config:Path|None,secrets_path:Path|None,pad:int,replay_db:Path|None,allow_replay:bool,nonce_log:Optional[Path])->int:
    chain=load_chain(chain_opt,config); root=load_root_secret(secrets_path or Path("secrets.json")); logger=NonceLogger(nonce_log)
    incoming=Path(path).read_bytes()
    traversed=run_online_chain(incoming,tcp=tcp,mtu=mtu,receive_mode=True,chain=chain,write_intermediate=False)
    try: plain=deobfuscate_layers(traversed,chain,root,logger)
    except Exception as e: print(f"[error] decryption failed: {e}",file=sys.stderr); return 1
    try: payload,msg_id=parse_plaintext(plain)
    except Exception as e: print(f"[error] plaintext parse failed: {e}",file=sys.stderr); return 1
    if replay_db:
        conn=replay_db_open(replay_db); ok=replay_check_and_store(conn,msg_id,allow_replay); conn.close()
        if not ok: print("[error] replay detected (use --allow-replay to override)",file=sys.stderr); return 1
    write_bytes(Path(RECEIVED_BIN),payload); print(f"[write] {RECEIVED_BIN} {len(payload)} bytes sha256={sha256_bytes(payload)}"); return 0

def build_parser()->argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog="dbridge.py",description="D-Bridge hardened client")
    p.add_argument("--tcp",action="store_true"); p.add_argument("--mtu",type=int,default=0)
    p.add_argument("--chain",type=str,default=None); p.add_argument("--config",type=Path,default=Path("entropy_tcp.json"))
    p.add_argument("--secrets",type=Path,default=Path("secrets.json")); p.add_argument("--pad",type=int,default=512)
    p.add_argument("--replay-db",type=Path,default=None); p.add_argument("--allow-replay",action="store_true")
    p.add_argument("--spawn-relays",action="store_true")
    p.add_argument("--relay-bin",type=Path,default=(Path(__file__).resolve().parent.parent/"relays"/"relay"))
    p.add_argument("--nonce-log",type=Path,default=None)
    sub=p.add_subparsers(dest="cmd",required=True)
    sp=sub.add_parser("send"); sp.add_argument("message",type=str)
    spf=sub.add_parser("sendfile"); spf.add_argument("path",type=Path)
    spfw=sub.add_parser("forward"); spfw.add_argument("path",type=Path)
    spr=sub.add_parser("receive"); spr.add_argument("path",type=Path)
    return p

def main(argv:Sequence[str]|None=None)->int:
    a=build_parser().parse_args(argv); chain=load_chain(a.chain,a.config); procs=[]
    try:
        procs=spawn_relays_if_requested(a.spawn_relays,a.relay_bin,chain)
        if a.cmd=="send": return cmd_send(a.message,tcp=a.tcp,mtu=a.mtu,chain_opt=a.chain,config=a.config,secrets_path=a.secrets,pad=a.pad,nonce_log=a.nonce_log)
        if a.cmd=="sendfile": return cmd_sendfile(a.path,tcp=a.tcp,mtu=a.mtu,chain_opt=a.chain,config=a.config,secrets_path=a.secrets,pad=a.pad,nonce_log=a.nonce_log)
        if a.cmd=="forward": return cmd_forward(a.path,tcp=a.tcp,mtu=a.mtu,chain_opt=a.chain,config=a.config)
        if a.cmd=="receive": return cmd_receive(a.path,tcp=a.tcp,mtu=a.mtu,chain_opt=a.chain,config=a.config,secrets_path=a.secrets,pad=a.pad,replay_db=a.replay_db,allow_replay=a.allow_replay,nonce_log=a.nonce_log)
        print("Unknown command",file=sys.stderr); return 2
    finally:
        if procs: stop_relays(procs)

if __name__=="__main__": sys.exit(main())
