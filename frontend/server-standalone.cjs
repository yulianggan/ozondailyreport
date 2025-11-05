// 零依赖静态服务器，用于 Docker 容器
const http = require('http')
const fs = require('fs')
const path = require('path')

const root = path.join(__dirname, 'public')
const port = Number(process.env.PORT || 3051)

const mime = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
}

function send(res, status, headers, body) {
  res.writeHead(status, headers); res.end(body)
}

function notFound(res) { send(res, 404, { 'content-type': 'text/plain; charset=utf-8' }, 'Not Found') }

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0])
  let filePath = path.join(root, urlPath)

  fs.stat(filePath, (err, stat) => {
    if (!err && stat.isDirectory()) filePath = path.join(filePath, 'index.html')
    fs.readFile(filePath, (e, data) => {
      if (e) {
        // 单页应用回退到 index.html
        fs.readFile(path.join(root, 'index.html'), (e2, data2) => {
          if (e2) return notFound(res)
          send(res, 200, { 'content-type': 'text/html; charset=utf-8' }, data2)
        })
        return
      }
      const ext = path.extname(filePath)
      const type = mime[ext] || 'application/octet-stream'
      send(res, 200, { 'content-type': type }, data)
    })
  })
})

server.listen(port, () => {
  console.log(`[frontend] static server running at http://0.0.0.0:${port}`)
})

