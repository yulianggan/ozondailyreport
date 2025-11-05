FROM node:20-alpine

ENV NODE_ENV=production
WORKDIR /app

# 拷贝静态资源和零依赖的服务器脚本（不需要 npm install）
COPY public /app/public
COPY server-standalone.cjs /app/server.cjs

EXPOSE 3051

CMD ["node", "server.cjs"]
