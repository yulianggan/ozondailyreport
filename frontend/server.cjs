// 简化型静态服务器，端口 3051（CommonJS 以兼容 package.json type: module）
const express = require('express')
const path = require('path')
const compression = require('compression')

const app = express()
app.use(compression())
const pub = path.join(__dirname, 'public')
app.use(express.static(pub))

app.get('*', (req, res) => {
  res.sendFile(path.join(pub, 'index.html'))
})

const PORT = process.env.PORT ? Number(process.env.PORT) : 3051
app.listen(PORT, () => {
  console.log(`[frontend] static server at http://localhost:${PORT}`)
})

