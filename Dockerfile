# Alondra1 landing page: static build of both variants (dev, prod), served by unprivileged nginx on :8080.
#   docker build -t alondra1-landing:local .
#   docker run --rm -e ALONDRA1_ENVIRONMENT=dev -p 127.0.0.1:8080:8080 alondra1-landing:local   # http://127.0.0.1:8080
# One image for every environment: prod runs the exact digest that passed in dev; ALONDRA1_ENVIRONMENT picks the variant.

FROM python:3.13-alpine@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e AS build
WORKDIR /src
COPY build.py ./
COPY config ./config
COPY src ./src
COPY public ./public
COPY tests ./tests
# The image is only produced when the content rules pass.
RUN python -I -m unittest discover -s tests -t . && python -I build.py --out /dist

FROM nginxinc/nginx-unprivileged:stable-alpine@sha256:f5116ed4606f3eb015dd4a8e28cb9b351476dc0ad4bc6e9f93b19cec130cdf03
# Templates are rendered into conf.d at start (envsubst replaces only ALONDRA1_ENVIRONMENT; nginx variables stay).
ENV NGINX_ENVSUBST_FILTER=^ALONDRA1_
COPY nginx/templates/ /etc/nginx/templates/
COPY nginx/snippets/ /etc/nginx/snippets/
COPY --chmod=0755 nginx/05-alondra1-environment.sh /docker-entrypoint.d/05-alondra1-environment.sh
COPY --from=build /dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3   CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
