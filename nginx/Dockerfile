# Pixelle-Video Nginx Reverse Proxy
FROM nginx:alpine

# Install certbot for SSL certificate auto-renewal (optional)
RUN apk add --no-cache certbot certbot-nginx

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy production nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create SSL directory
RUN mkdir -p /etc/nginx/ssl /var/www/certbot

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]