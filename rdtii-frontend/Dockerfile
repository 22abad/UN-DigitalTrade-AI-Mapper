FROM nginx:1.27-alpine

# 直接复制本地构建好的 dist 到 nginx 目录，跳过容器内构建
COPY ./dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
