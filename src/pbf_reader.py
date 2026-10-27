"""Read nodes, ways and attributes from OpenStreetMap PBF files."""
import struct,zlib
from pathlib import Path

def varint(b, i):
    n=0;shift=0
    while True:
        a=b[i]; i+=1; n |= (a&127)<<shift
        if a<128:return n,i
        shift+=7

def s64(n):return n-(1<<64) if n>=1<<63 else n
def zig(n):return (n>>1)^-(n&1)

def fields(buf):
    i=0
    while i<len(buf):
        key,i=varint(buf,i); f=key>>3;wire=key&7
        if wire==0: v,i=varint(buf,i)
        elif wire==1:v=buf[i:i+8];i+=8
        elif wire==2:
            size,i=varint(buf,i);v=buf[i:i+size];i+=size
        elif wire==5:v=buf[i:i+4];i+=4
        else: raise ValueError('unknown protobuf wire type '+str(wire))
        yield f,v

def packed(buf, signed=False):
    i=0
    while i<len(buf):
        n,i=varint(buf,i)
        yield zig(n) if signed else n

def delta(vals):
    v=0
    for d in vals:v+=d;yield v

def blocks(pbf):
    with open(pbf,'rb') as f:
        while raw:=f.read(4):
            n=struct.unpack('>I',raw)[0];hdr=f.read(n)
            t='';size=None
            for k,v in fields(hdr):
                if k==1:t=v.decode()
                elif k==3:size=v
            data=f.read(size)
            if t!='OSMData':continue
            blobs=dict(fields(data))
            if 1 in blobs: body=blobs[1]
            elif 3 in blobs:body=zlib.decompress(blobs[3])
            else:raise ValueError('unsupported PBF blob compression')
            yield body

def read_osm(pbf):
    """Yield ('node', id,lon,lat) and ('way', id,list_of_node_ids,tags)."""
    for blob in blocks(pbf):
        groups=[];gran=100;lat_off=0;lon_off=0;st=[]
        for k,v in fields(blob):
            if k==1:
                st=[x.decode('utf-8','replace') for j,x in fields(v) if j==1]
            elif k==2:groups.append(v)
            elif k==17:gran=v
            elif k==19:lat_off=s64(v)
            elif k==20:lon_off=s64(v)
        for group in groups:
            for field,record in fields(group):
                if field==2: # DenseNodes
                    p=dict(fields(record))
                    ids=list(delta(packed(p.get(1,b''),True)))
                    lats=list(delta(packed(p.get(8,b''),True)))
                    lons=list(delta(packed(p.get(9,b''),True)))
                    for nid,lat,lon in zip(ids,lats,lons):
                        yield ('node',nid, (lon_off+gran*lon)*1e-9,(lat_off+gran*lat)*1e-9)
                elif field==1: # nondense Node
                    p=dict(fields(record))
                    yield ('node',p[1],(lon_off+gran*zig(p[9]))*1e-9,(lat_off+gran*zig(p[8]))*1e-9)
                elif field==3: # Way
                    props={}; keys=[];values=[];refs=[]
                    for k,v in fields(record):
                        if k==1: props['id']=v
                        elif k==2:keys=list(packed(v))
                        elif k==3:values=list(packed(v))
                        elif k==8:refs=list(delta(packed(v,True)))
                    tags={st[k]:st[v] for k,v in zip(keys,values)}
                    yield ('way',props['id'],refs,tags)
