(function(root){
  "use strict";
  const table=(()=>{const value=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;value[n]=c>>>0;}return value;})();
  const crc32=bytes=>{let c=0xffffffff;for(const b of bytes)c=table[(c^b)&255]^(c>>>8);return (c^0xffffffff)>>>0;};
  const put16=(value,offset,number)=>new DataView(value.buffer).setUint16(offset,number,true);
  const put32=(value,offset,number)=>new DataView(value.buffer).setUint32(offset,number>>>0,true);

  function zipStore(files){
    const enc=new TextEncoder(),locals=[],centrals=[];let offset=0;
    files.forEach(file=>{
      const name=enc.encode(file.name),data=file.data,crc=crc32(data);
      const local=new Uint8Array(30+name.length+data.length);
      put32(local,0,0x04034b50);put16(local,4,20);put16(local,6,0x0800);put16(local,8,0);
      put32(local,14,crc);put32(local,18,data.length);put32(local,22,data.length);put16(local,26,name.length);
      local.set(name,30);local.set(data,30+name.length);locals.push(local);
      const central=new Uint8Array(46+name.length);
      put32(central,0,0x02014b50);put16(central,4,20);put16(central,6,20);put16(central,8,0x0800);put16(central,10,0);
      put32(central,16,crc);put32(central,20,data.length);put32(central,24,data.length);put16(central,28,name.length);put32(central,42,offset);
      central.set(name,46);centrals.push(central);offset+=local.length;
    });
    const centralSize=centrals.reduce((sum,value)=>sum+value.length,0),end=new Uint8Array(22);
    put32(end,0,0x06054b50);put16(end,8,files.length);put16(end,10,files.length);put32(end,12,centralSize);put32(end,16,offset);
    return new Blob([...locals,...centrals,end],{type:"application/zip"});
  }

  root.ModooZipStore=Object.freeze({crc32,zipStore});
})(globalThis);
