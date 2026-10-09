// Audit-only static build preview and same-origin proxy to isolated backend.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const dist = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../frontend/dist');
const isApi = url => /^\/(auth|users|rooms|messages|uploads|health)(\/|\?|$)/.test(url);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.ico': 'image/x-icon', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8' };
const server = http.createServer((req, res) => {
  if (isApi(req.url)) {
    const upstream = http.request({host:'127.0.0.1',port:8019,path:req.url,method:req.method,headers:req.headers}, reply => {
      res.writeHead(reply.statusCode, reply.headers); reply.pipe(res);
    });
    upstream.on('error', () => {res.writeHead(502); res.end('Isolated audit backend unavailable');});
    req.pipe(upstream); return;
  }
  const requested = path.resolve(dist, '.' + decodeURIComponent(req.url.split('?')[0]));
  const file = requested.startsWith(dist + path.sep) && fs.existsSync(requested) && fs.statSync(requested).isFile() ? requested : path.join(dist,'index.html');
  res.writeHead(200, {'Content-Type': types[path.extname(file)] || 'application/octet-stream'});
  fs.createReadStream(file).pipe(res);
});
server.on('upgrade', (req, socket, head) => {
  const upstream = http.request({host:'127.0.0.1',port:8019,path:req.url,method:req.method,headers:req.headers});
  upstream.on('upgrade', (reply, peer, peerHead) => {
    socket.write(`HTTP/1.1 ${reply.statusCode} ${reply.statusMessage}\r\n` + reply.rawHeaders.reduce((s,v,i,a)=>i%2?s:s+v+': '+a[i+1]+'\r\n','')+'\r\n');
    if(head.length)peer.write(head); if(peerHead.length)socket.write(peerHead);
    socket.pipe(peer); peer.pipe(socket);
    socket.on('error',()=>peer.destroy()); peer.on('error',()=>socket.destroy());
  });
  upstream.on('response', reply => {socket.end(`HTTP/1.1 ${reply.statusCode} Rejected\r\n\r\n`);});
  upstream.on('error',()=>socket.destroy()); upstream.end();
});
server.listen(4189,'127.0.0.1',()=>console.log('Isolated audit preview: http://127.0.0.1:4189'));
