FROM nginx:alpine

# Copy site into Nginx's default static folder
COPY ./public-html /usr/share/nginx/html

# Optional: overwrite default Nginx config
# COPY nginx.conf /etc/nginx/nginx.conf

